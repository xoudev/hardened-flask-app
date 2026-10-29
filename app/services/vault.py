"""Identifiants PostgreSQL dynamiques et éphémères générés par HashiCorp Vault."""
import os

import hvac

from app.config import vault_settings


def get_dynamic_db_creds() -> tuple[str, str]:
    """Lit le token Vault (secret Docker) et demande un couple user/password éphémère."""
    settings = vault_settings()

    if not os.path.exists(settings.token_path):
        raise RuntimeError(f"Fichier de secret Vault introuvable sur {settings.token_path}")

    with open(settings.token_path, encoding="utf-8") as f:
        vault_token = f.read().strip()

    client = hvac.Client(url=settings.addr, token=vault_token)
    if not client.is_authenticated():
        raise RuntimeError("Échec de l'authentification auprès de HashiCorp Vault")

    creds = client.secrets.database.generate_credentials(name=settings.db_role)
    return creds["data"]["username"], creds["data"]["password"]
