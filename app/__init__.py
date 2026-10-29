"""Package de l'API : expose la factory create_app()."""
from flask import Flask

from app.routes import bp
from app.security import apply_security_headers, harden_werkzeug_banner


def create_app(config: dict | None = None) -> Flask:
    """Construit et configure l'application Flask."""
    harden_werkzeug_banner()

    app = Flask(__name__)
    if config:
        app.config.update(config)

    app.after_request(apply_security_headers)
    app.register_blueprint(bp)
    return app
