"""Durcissement HTTP : bannière serveur et en-têtes de sécurité (audit OWASP ZAP)."""
import werkzeug.serving

SERVER_NAME = "api-gateway"

SECURITY_HEADERS = {
    # Masquage de la bannière serveur
    "Server": SERVER_NAME,
    # Protection contre le reniflage MIME
    "X-Content-Type-Options": "nosniff",
    # Anti-clickjacking
    "X-Frame-Options": "DENY",
    # Isolation cross-origin stricte
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    # CSP restrictive pour une API purement JSON
    "Content-Security-Policy": (
        "default-src 'none'; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "frame-ancestors 'none';"
    ),
    # Pas d'accès aux capteurs du client
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    # Pas de cache sur les données
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


def harden_werkzeug_banner() -> None:
    """Empêche Werkzeug d'envoyer "Server: Werkzeug/x.x Python/x.x" au niveau socket."""
    werkzeug.serving.WSGIRequestHandler.server_version = SERVER_NAME
    werkzeug.serving.WSGIRequestHandler.sys_version = ""


def apply_security_headers(response):
    """Ajoute les en-têtes de sécurité sur chaque réponse (200, 404, 500)."""
    response.headers.update(SECURITY_HEADERS)
    return response
