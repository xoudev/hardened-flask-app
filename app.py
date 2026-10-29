import os
import hvac
import psycopg2
from flask import Flask, jsonify

app = Flask(__name__)

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://vault:8200")
VAULT_TOKEN_PATH = "/run/secrets/vault_token"

def get_vault_client():
    if not os.path.exists(VAULT_TOKEN_PATH):
        raise RuntimeError(f"Fichier secret introuvable : {VAULT_TOKEN_PATH}")
    with open(VAULT_TOKEN_PATH, "r") as f:
        token = f.read().strip()
    client = hvac.Client(url=VAULT_ADDR, token=token)
    if not client.is_authenticated():
        raise RuntimeError("Échec de l'authentification auprès de Vault.")
    return client

def get_dynamic_db_creds():
    client = get_vault_client()
    # Appel de l'API Vault pour générer un nouvel utilisateur PostgreSQL temporaire
    response = client.secrets.database.generate_credentials(name="flask-role")
    
    lease_id = response.get("lease_id")
    lease_duration = response.get("lease_duration")
    creds = response["data"]
    
    print(f"[INFO] Nouveaux identifiants générés (lease: {lease_id}, durée: {lease_duration}s)")
    return creds["username"], creds["password"]

@app.route("/")
def list_users():
    try:
        # Récupération à la volée des identifiants éphémères
        db_user, db_pass = get_dynamic_db_creds()

        # Connexion à PostgreSQL avec les droits temporaires
        conn = psycopg2.connect(
            host="db",
            port=5432,
            dbname="appdb",
            user=db_user,
            password=db_pass,
            connect_timeout=3
        )
        cur = conn.cursor()
        cur.execute("SELECT id, username, secret_note FROM users;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        users = [{"id": r[0], "username": r[1], "secret_note": r[2]} for r in rows]
        return jsonify({
            "status": "success",
            "connected_as": db_user,
            "data": users
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    app.run(host=host, port=port)