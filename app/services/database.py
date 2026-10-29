"""Requêtes PostgreSQL."""
import psycopg2

from app.config import database_settings


def fetch_users(user: str, password: str) -> list[dict]:
    """Ouvre une connexion avec les identifiants fournis et retourne les utilisateurs."""
    settings = database_settings()
    conn = psycopg2.connect(
        host=settings.host,
        database=settings.name,
        user=user,
        password=password,
        port=settings.port,
        connect_timeout=3,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, secret_note FROM app_users;")
            rows = cursor.fetchall()
    finally:
        conn.close()

    return [{"id": r[0], "username": r[1], "secret_note": r[2]} for r in rows]
