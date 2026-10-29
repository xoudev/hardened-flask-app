import pytest
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_list_users_success(client):
    """
    Test unitaire : vérifie que la route / traite et formate correctement 
    les données SQL quand Vault et la base répondent normalement.
    """
    # 1. On simule la réponse de Vault (identifiants temporaires)
    fake_creds = ("v-token-test-user", "fake-password-123")

    # 2. On simule le curseur PostgreSQL et le retour de la requête SELECT
    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = [
        (1, "alice", "note-secrete-1"),
        (2, "bob", "note-secrete-2")
    ]
    
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cursor

    # 3. On injecte les mocks à la place des vraies fonctions réseau
    with patch("app.get_dynamic_db_creds", return_value=fake_creds), \
         patch("psycopg2.connect", return_value=fake_conn):
        
        response = client.get('/')
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data["status"] == "success"
        assert json_data["connected_as"] == "v-token-test-user"
        assert len(json_data["data"]) == 2
        assert json_data["data"][0]["username"] == "alice"

def test_list_users_vault_failure_handling(client):
    """
    Test de résilience : vérifie que l'app gère proprement l'erreur 
    si Vault devient inaccessible (sans crasher le processus).
    """
    with patch("app.get_dynamic_db_creds", side_effect=RuntimeError("Vault unreachable")):
        response = client.get('/')
        json_data = response.get_json()

        assert response.status_code == 500
        assert json_data["status"] == "error"
        assert "Vault unreachable" in json_data["message"]