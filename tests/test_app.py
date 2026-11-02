import http.client
import threading
from unittest.mock import MagicMock, patch

from werkzeug.serving import make_server

from app import create_app
from app.security import SECURITY_HEADERS, SERVER_NAME
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


def test_error_does_not_leak_details(client):
    with patch("app.services.vault.get_dynamic_db_creds", side_effect=RuntimeError("DATABASE_PASSWORD=123")):
        response = client.get("/")
        texte = response.get_data(as_text=True)
    assert "DATABASE_PASSWORD=123" not in texte


def test_error_is_logged_with_details(client, caplog):
    with patch("app.services.vault.get_dynamic_db_creds", side_effect=RuntimeError("DATABASE_PASSWORD=123")):
        client.get("/")

    assert "DATABASE_PASSWORD=123" in caplog.text


def test_server_header_sent_once_and_masked():
    # Le doublon n'apparaît qu'au niveau socket (Werkzeug) : le client de test Flask ne le voit pas.
    server = make_server("127.0.0.1", 0, create_app({"TESTING": True}))
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        connection.request("GET", "/health")
        response = connection.getresponse()
        server_headers = response.headers.get_all("Server")
        connection.close()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert server_headers == [SERVER_NAME]