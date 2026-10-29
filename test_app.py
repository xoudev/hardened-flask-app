import pytest
from app import app

@pytest.fixture
def client():
    # Configure Flask en mode test (meilleure remontée des exceptions)
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_or_index_status(client):
    """Vérifie que l'API démarre et répond sur la racine ou le endpoint de santé."""
    response = client.get('/')
    # On accepte 200 (OK) ou 404 si la racine n'est pas définie, mais jamais 500 (crash serveur)
    assert response.status_code != 500