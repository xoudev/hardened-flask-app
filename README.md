# lab-python

API Flask de lab DevSecOps : identifiants PostgreSQL dynamiques via HashiCorp Vault,
image Chainguard durcie, pipeline CI (gitleaks, hadolint, Trivy, Ruff, pytest, Semgrep, OWASP ZAP).

## Structure

```
app/                    Code de l'API (package Python)
  __init__.py           create_app() : assemble l'application
  __main__.py           Point d'entrée : python -m app
  config.py             Lecture des variables d'environnement
  security.py           En-têtes HTTP de sécurité + masquage bannière Werkzeug
  routes.py             Endpoints (/ et /health)
  services/
    vault.py            Identifiants DB éphémères depuis Vault
    database.py         Requêtes PostgreSQL
tests/                  Tests pytest (conftest.py fournit le client de test)
docker/
  seccomp-flask.json    Profil seccomp du conteneur app
  vault/vault.json      Config Vault (mode serveur, non utilisée en mode dev)
db/backup.sql           Dump PostgreSQL de référence
scripts/reset_lab.sh    Monte et initialise toute la stack
secrets/                Secrets locaux (ignorés par git, générés par reset_lab.sh)
reports/                Rapports de bench/scans (ignorés par git)
.zap/rules.tsv          Règles du scan DAST ZAP
```

## Compétences acquises

**Développement Python / Flask**
- Structurer une API en package : factory `create_app()`, blueprints, séparation routes / services / config
- Configuration par variables d'environnement (principe 12-factor)
- Endpoint de santé `/health` indépendant des dépendances externes (liveness probe)

**Tests et qualité de code**
- Tests unitaires avec pytest : fixtures (`conftest.py`), client de test Flask
- Isolation des dépendances externes avec `unittest.mock` (`patch`, `MagicMock`, context managers)
- Lint avec Ruff, configuration centralisée dans `pyproject.toml`

**Sécurité applicative (AppSec)**
- En-têtes HTTP de sécurité : CSP, X-Frame-Options, X-Content-Type-Options, COOP/CORP, Permissions-Policy, Cache-Control
- Masquage de l'empreinte logicielle (bannière Werkzeug)
- Gestion des secrets hors du code : secrets Docker montés dans `/run/secrets`, fichiers ignorés par git

**Conteneurisation et durcissement Docker**
- Dockerfile multi-stage (builder / runtime) pour une image minimale
- Image de base Chainguard « zero-CVE », épinglée par digest `sha256`
- Exécution en utilisateur non-root (`USER 65532`)
- `.dockerignore` en liste blanche pour limiter le contexte de build
- Durcissement à l'exécution : système de fichiers en lecture seule, `tmpfs` `noexec`, `cap_drop: ALL`,
  `no-new-privileges`, profil seccomp personnalisé, limites CPU / mémoire / PIDs

**Orchestration avec Docker Compose**
- Stack multi-services (app, PostgreSQL, Vault)
- Segmentation réseau avec réseaux `internal` (DB et Vault non exposés à l'extérieur)
- Healthchecks et `depends_on` conditionnels, ports liés à `127.0.0.1` uniquement

**CI/CD DevSecOps (GitHub Actions)**
- Pipeline en plusieurs jobs enchaînés (`needs`)
- Actions tierces épinglées par SHA de commit (sécurité de la supply chain)
- Détection de secrets : gitleaks
- Lint du Dockerfile : hadolint
- SAST : Semgrep
- SCA : Trivy sur les dépendances (filesystem) et sur l'image construite
- DAST : scan OWASP ZAP baseline contre le conteneur en cours d'exécution
- Gestion documentée du risque résiduel (`.trivyignore`, `.zap/rules.tsv`)

**Scripting**
- Script Bash robuste (`set -euo pipefail`), attente active de services, idempotence SQL (`WHERE NOT EXISTS`)

## Compétences en cours d'acquisition

**HashiCorp Vault**
- Moteur de secrets *Database* : configurer la connexion PostgreSQL et le rôle `app-readwrite`
  pour générer de vrais identifiants dynamiques (aujourd'hui le script utilise encore le moteur KV)
- Sortir du mode dev : stockage persistant, TLS, unseal, politiques (policies) à moindre privilège
- Remplacer le root token par une méthode d'authentification applicative (AppRole, Kubernetes auth)

**Bases de données**
- Schéma cohérent entre le script d'init et l'application (table `users` vs `app_users`)
- Scripts d'initialisation / migrations versionnés (`docker-entrypoint-initdb.d`, Alembic)
- Gestion du cycle de vie des connexions (pool, rotation des identifiants éphémères)

**Sécurité applicative**
- Gestion d'erreurs sans fuite d'information (message générique côté client, détail dans les logs)
- Journalisation structurée et traçabilité des accès
- Suppression du doublon d'en-tête `Server`

**Mise en production**
- Serveur WSGI de production (Gunicorn) à la place du serveur de dev Flask
- Épinglage de toutes les images (Vault, PostgreSQL) et de toutes les dépendances (`requirements` verrouillés)
- Signature d'image et SBOM (cosign, Syft), publication dans un registre

**Orchestration Kubernetes**
- Déploiement avec probes (`/health`), `securityContext`, NetworkPolicies et injection de secrets Vault

## Commandes

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest                  # tests
ruff check .            # lint
python -m app           # lancer l'API en local

./scripts/reset_lab.sh  # stack complète (app + Postgres + Vault)
```
