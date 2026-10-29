from unittest.mock import MagicMock, patch

from app.security import SECURITY_HEADERS
from app.services import database


def test_list_users_success(client):
    fake_users = [
        {"id": 1, "username": "alice", "secret_note": "note-secrete-1"},
        {"id": 2, "username": "bob", "secret_note": "note-secrete-2"},
    ]
    with patch("app.services.vault.get_dynamic_db_creds", return_value=("v-token-test-user", "pwd")), \
         patch("app.services.database.fetch_users", return_value=fake_users):
        response = client.get("/")

    json_data = response.get_json()
    assert response.status_code == 200
    assert json_data["status"] == "success"
    assert json_data["connected_as"] == "v-token-test-user"
    assert len(json_data["data"]) == 2


def test_list_users_vault_failure_handling(client):
    with patch("app.services.vault.get_dynamic_db_creds", side_effect=RuntimeError("Vault unreachable")):
        response = client.get("/")

    assert response.status_code == 500
    assert response.get_json()["status"] == "error"


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_security_headers_on_every_response(client):
    for path in ("/health", "/route-inexistante"):
        response = client.get(path)
        for name, value in SECURITY_HEADERS.items():
            assert response.headers[name] == value


def test_fetch_users_maps_rows_and_closes_connection():
    fake_cursor = MagicMock()
    fake_cursor.fetchall.return_value = [(1, "alice", "n1"), (2, "bob", "n2")]
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor

    with patch("psycopg2.connect", return_value=fake_conn):
        users = database.fetch_users("user", "pwd")

    assert users == [
        {"id": 1, "username": "alice", "secret_note": "n1"},
        {"id": 2, "username": "bob", "secret_note": "n2"},
    ]
    fake_conn.close.assert_called_once()
