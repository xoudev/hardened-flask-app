"""Configuration centralisée, lue depuis les variables d'environnement."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VaultSettings:
    addr: str
    token_path: str
    db_role: str


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    name: str
    port: str


def vault_settings() -> VaultSettings:
    return VaultSettings(
        addr=os.getenv("VAULT_ADDR", "http://vault:8200"),
        token_path=os.getenv("VAULT_TOKEN_PATH", "/run/secrets/vault_token"),
        db_role=os.getenv("VAULT_DB_ROLE", "app-readwrite"),
    )


def database_settings() -> DatabaseSettings:
    return DatabaseSettings(
        host=os.getenv("DB_HOST", "db"),
        name=os.getenv("DB_NAME", "appdb"),
        port=os.getenv("DB_PORT", "5432"),
    )


def server_bind() -> tuple[str, int]:
    return (
        os.getenv("FLASK_RUN_HOST", "0.0.0.0"),
        int(os.getenv("FLASK_RUN_PORT", "5000")),
    )
