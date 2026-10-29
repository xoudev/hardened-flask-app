"""Endpoints HTTP de l'API."""
from flask import Blueprint, jsonify

from app.services import database, vault

bp = Blueprint("api", __name__)


@bp.get("/health")
def health():
    """Liveness probe (Kubernetes / cible DAST). Ne touche ni Vault ni la DB."""
    return jsonify({"status": "healthy"}), 200


@bp.get("/")
def list_users():
    """Récupère des identifiants Vault temporaires puis lit les utilisateurs en base."""
    try:
        db_user, db_pass = vault.get_dynamic_db_creds()
        data = database.fetch_users(db_user, db_pass)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success", "connected_as": db_user, "data": data}), 200
