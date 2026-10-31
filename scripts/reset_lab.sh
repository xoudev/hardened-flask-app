#!/usr/bin/env bash
set -euo pipefail

# Toujours exécuter depuis la racine du projet, peu importe d'où le script est lancé
cd "$(dirname "$0")/.."
mkdir -p secrets

DB_CONTAINER="lab-python-db-1"
VAULT_CONTAINER="lab-vault"
VAULT_DB_CONFIG="appdb"
VAULT_DB_ROLE="app-readwrite"

echo "=== [1/5] Vérification des secrets locaux ==="
if [ ! -f secrets/db_password.txt ]; then
  echo -n "supersecretpassword" > secrets/db_password.txt
  chmod 600 secrets/db_password.txt
  echo "Fichier secrets/db_password.txt généré."
fi

if [ ! -f secrets/vault_token.txt ]; then
  echo -n "myroottoken" > secrets/vault_token.txt
  # 644 : le secret est monté tel quel dans le conteneur app, qui tourne en UID 65532
  chmod 644 secrets/vault_token.txt
  echo "Fichier secrets/vault_token.txt généré."
fi

echo "=== [2/5] Construction de l'image et démarrage des conteneurs ==="
# --build : sans lui, Compose réutilise l'image locale existante, même si le code a changé
docker compose up -d --build

echo "=== [3/5] Initialisation du schéma PostgreSQL ==="
until docker exec "$DB_CONTAINER" pg_isready -U appuser -d appdb > /dev/null 2>&1; do
  echo "En attente de PostgreSQL..."
  sleep 1
done

docker exec -i "$DB_CONTAINER" psql -v ON_ERROR_STOP=1 -U appuser -d appdb > /dev/null << 'SQL'
CREATE TABLE IF NOT EXISTS app_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    secret_note TEXT
);

INSERT INTO app_users (username, secret_note) VALUES
    ('Alice', 'Note confidentielle 1'),
    ('Bob',   'Note confidentielle 2')
ON CONFLICT (username) DO NOTHING;
SQL
echo "Table app_users initialisée."

echo "=== [4/5] Configuration du moteur de secrets Database de Vault ==="
until docker exec -e VAULT_ADDR="http://127.0.0.1:8200" "$VAULT_CONTAINER" vault status > /dev/null 2>&1; do
  echo "En attente de Vault..."
  sleep 1
done

vault_cli() {
  docker exec -i \
    -e VAULT_ADDR="http://127.0.0.1:8200" \
    -e VAULT_TOKEN="$(cat secrets/vault_token.txt)" \
    "$VAULT_CONTAINER" vault "$@"
}

# Mode dev = stockage en mémoire : tout est perdu quand le conteneur est recréé
if ! vault_cli secrets list | grep -q '^database/'; then
  vault_cli secrets enable database > /dev/null
fi

# Connexion de Vault à PostgreSQL. Le mot de passe arrive par stdin (password=-)
# pour ne jamais apparaître dans la liste des processus ni dans l'historique.
vault_cli write "database/config/${VAULT_DB_CONFIG}" \
  plugin_name="postgresql-database-plugin" \
  connection_url="postgresql://{{username}}:{{password}}@db:5432/appdb?sslmode=disable" \
  username="appuser" \
  password=- \
  allowed_roles="${VAULT_DB_ROLE}" < secrets/db_password.txt > /dev/null

# Rôle : chaque demande crée un utilisateur PostgreSQL temporaire, en lecture seule
vault_cli write "database/roles/${VAULT_DB_ROLE}" \
  db_name="${VAULT_DB_CONFIG}" \
  creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT ON app_users TO \"{{name}}\";" \
  default_ttl="1h" \
  max_ttl="24h" > /dev/null
echo "Moteur database et rôle ${VAULT_DB_ROLE} configurés."

echo "=== [5/5] Attente active et test de l'API Flask ==="
MAX_RETRIES=15
COUNT=0

echo -n "En attente de Flask sur http://127.0.0.1:5000/ "
until curl -s -f http://127.0.0.1:5000/ > /dev/null 2>&1; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
    echo -e "\n[ERREUR] Timeout : Flask n'a pas répondu avec un code 200 après ${MAX_RETRIES}s."
    echo "Derniers logs de app :"
    docker compose logs app --tail=15
    exit 1
  fi
  echo -n "."
  sleep 1
done

echo -e "\nFlask est prêt !"
echo "Réponse HTTP de l'API :"
curl -s http://127.0.0.1:5000/
echo -e "\n\nStack 100 % opérationnelle !"
