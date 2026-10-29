import os
import pytest
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    # Définition propre via environnement
    os.environ["FLASK_ENV"] = "testing"
    app.config.update({"TESTING": True})
    with app.test_client() as client:
        yield client

def test_list_users_success(client):
    fake_creds = ("v-token-test-user", "fake-password-123")
    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = [
        (1, "alice", "note-secrete-1"),
        (2, "bob", "note-secrete-2")
    ]
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cursor

    with patch("app.get_dynamic_db_creds", return_value=fake_creds), \
         patch("psycopg2.connect", return_value=fake_conn):
        
        response = client.get('/')
        json_data = response.get_json()

        assert response.status_code == 200
        assert json_data["status"] == "success"
        assert json_data["connected_as"] == "v-token-test-user"
        assert len(json_data["data"]) == 2

def test_list_users_vault_failure_handling(client):
    with patch("app.get_dynamic_db_creds", side_effect=RuntimeError("Vault unreachable")):
        response = client.get('/')
        json_data = response.get_json()

        assert response.status_code == 500
        assert json_data["status"] == "error"

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}