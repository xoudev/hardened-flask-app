#!/usr/bin/env bash
set -euo pipefail

echo "=== [1/5] Vérification des secrets locaux ==="
if [ ! -f db_password.txt ]; then
  echo -n "supersecretpassword" > db_password.txt
  chmod 600 db_password.txt
  echo "Fichier db_password.txt généré."
fi

if [ ! -f vault_token.txt ]; then
  echo -n "myroottoken" > vault_token.txt
  chmod 644 vault_token.txt
  echo "Fichier vault_token.txt généré."
fi

echo "=== [2/5] Démarrage des conteneurs ==="
docker compose up -d

echo "=== [3/5] Configuration de HashiCorp Vault ==="
until docker exec -e VAULT_ADDR="http://127.0.0.1:8200" lab-vault vault status > /dev/null 2>&1; do
  echo "En attente de Vault..."
  sleep 1
done

docker exec -e VAULT_ADDR="http://127.0.0.1:8200" -e VAULT_TOKEN="myroottoken" lab-vault \
  vault kv put secret/app/database \
  username="appuser" \
  password="supersecretpassword" \
  dbname="appdb" > /dev/null
echo "Identifiants injectés dans Vault."

echo "=== [4/5] Initialisation du schéma PostgreSQL ==="
until docker exec lab-python-db-1 pg_isready -U appuser -d appdb > /dev/null 2>&1; do
  echo "En attente de PostgreSQL..."
  sleep 1
done

docker exec -i lab-python-db-1 psql -U appuser -d appdb > /dev/null << 'SQL'
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    secret_note TEXT
);

INSERT INTO users (username, secret_note)
SELECT 'Alice', 'Note confidentielle 1'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'Alice');

INSERT INTO users (username, secret_note)
SELECT 'Bob', 'Note confidentielle 2'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'Bob');
SQL
echo "Table users initialisée."

echo "=== [5/5] Attente active et test de l'API Flask ==="
# Redémarrage pour recharger les secrets si nécessaire
docker compose restart app > /dev/null

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
