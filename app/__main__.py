"""Point d'entrée : `python -m app`."""
from app import create_app
from app.config import server_bind

if __name__ == "__main__":
    host, port = server_bind()
    create_app().run(host=host, port=port)
