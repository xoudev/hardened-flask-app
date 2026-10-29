import os
import werkzeug.serving
from flask import Flask, jsonify
import hvac
import psycopg2

# ==============================================================================
# DURCISSEMENT WSGI (Neutralisation de la fuite d'empreinte logicielle)
# ==============================================================================
# Neutralise Werkzeug au niveau le plus bas (socket HTTP) pour empêcher
# la réinjection automatique de "Server: Werkzeug/x.x.x Python/x.x.x"
werkzeug.serving.WSGIRequestHandler.server_version = "api-gateway"
werkzeug.serving.WSGIRequestHandler.sys_version = ""

app = Flask(__name__)

# ==============================================================================
# MIDDLEWARE DE SÉCURITÉ HTTP (Audit DAST OWASP ZAP)
# ==============================================================================
@app.after_request
def apply_security_headers(response):
    """
    Injecte les en-têtes de sécurité sur chaque réponse HTTP (200, 404, 500).
    """
    # 1. Masquage de la bannière serveur
    response.headers["Server"] = "api-gateway"

    # 2. Protection contre le reniflage MIME (MIME-confusion)
    response.headers["X-Content-Type-Options"] = "nosniff"

    # 3. Protection anti-Clickjacking (interdiction stricte d'encapsulation iframe)
    response.headers["X-Frame-Options"] = "DENY"

    # 4. Isolation cross-origin stricte
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

    # 5. Content Security Policy (CSP) restrictive pour API purement JSON
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "frame-ancestors 'none';"
    )

    # 6. Neutralisation de l'accès aux capteurs matériels du client
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

    # 7. Directive anti-cache sur les flux de données
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"

    return response

# ==============================================================================
# LOGIQUE VAULT (Identifiants dynamiques éphémères)
# ==============================================================================
def get_dynamic_db_creds():
    """
    Lit le token Vault monté via secret Docker/K8s et génère un couple
    utilisateur/mot de passe éphémère auprès du moteur de secrets Database de Vault.
    """
    token_path = os.getenv("VAULT_TOKEN_PATH", "/run/secrets/vault_token")
    vault_addr = os.getenv("VAULT_ADDR", "http://vault:8200")
    vault_role = os.getenv("VAULT_DB_ROLE", "app-readwrite")

    if not os.path.exists(token_path):
        raise RuntimeError(f"Fichier de secret Vault introuvable sur {token_path}")

    with open(token_path, "r", encoding="utf-8") as f:
        vault_token = f.read().strip()

    client = hvac.Client(url=vault_addr, token=vault_token)
    if not client.is_authenticated():
        raise RuntimeError("Échec de l'authentification auprès de HashiCorp Vault")

    creds = client.secrets.database.generate_credentials(name=vault_role)
    username = creds["data"]["username"]
    password = creds["data"]["password"]

    return username, password

# ==============================================================================
# ENDPOINTS DE L'API
# ==============================================================================
@app.route("/health", methods=["GET"])
def health():
    """
    Sonde de disponibilité (liveness probe) pour Kubernetes et cible du scan DAST.
    Ne sollicite aucune ressource externe (Vault/DB).
    """
    return jsonify({"status": "healthy"}), 200

@app.route("/", methods=["GET"])
def list_users():
    """
    Point d'entrée principal : récupère des identifiants temporaires Vault,
    ouvre une session PostgreSQL, exécute la requête et formate le JSON.
    """
    try:
        db_user, db_pass = get_dynamic_db_creds()
        db_host = os.getenv("DB_HOST", "db")
        db_name = os.getenv("DB_NAME", "appdb")
        db_port = os.getenv("DB_PORT", "5432")

        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_pass,
            port=db_port,
            connect_timeout=3
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, secret_note FROM app_users;")
        records = cursor.fetchall()

        cursor.close()
        conn.close()

        data = [
            {"id": row[0], "username": row[1], "secret_note": row[2]}
            for row in records
        ]

        return jsonify({
            "status": "success",
            "connected_as": db_user,
            "data": data
        }), 200

    except Exception as e:
        # Message opaque retourné au client pour éviter toute fuite d'informations internes
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ==============================================================================
# EXÉCUTION DU PROCESSUS
# ==============================================================================
if __name__ == "__main__":
    run_host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    run_port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    app.run(host=run_host, port=run_port)