# Session-Kontext

## Projekt
- **Fußball-Dashboard**: FastAPI (Python 3.12) + Vue 3 (Vite 6.3)
- App-Version: 2.0.0
- Datenquelle: OpenLigaDB API
- DB: SQLite (`bundesliga.db`), als Volume gemountet

## Ligen
| Liga | Shortcut | Scraped | Live |
|------|----------|---------|------|
| 1. Bundesliga | bl1 | ✓ | ✓ |
| 2. Bundesliga | bl2 | ✓ | ✓ |
| 3. Liga | bl3 | ✓ | ✗ |
| DFB-Pokal | dfb | ✓ | ✓ |
| Champions League | ucl | ✓ | ✓ |
| Europa League | uel | ✓ | ✓ |

→ `bl3` wird gescrapt, aber in `/api/live` (server.py:252) nicht live abgefragt.

## Docker
- Dockerfile: Multi-Stage (Node 20-alpine → Python 3.12-slim)
- Image: `ghcr.io/nschmidle/fussball-dashboard:latest` (privat)
- docker-compose.yml nutzt ghcr.io-Image
- CMD: `python3 scraper.py && uvicorn server:app --host 0.0.0.0 --port 8080`

## Dev-Commands
- `pip install --user fastapi uvicorn sqlalchemy aiosqlite requests pywebpush`
- `python3 scraper.py` – Daten importieren
- `python3 server.py` – Server starten (Port 8080)
- `cd frontend && npm install && npm run dev` – Frontend dev (Port 5173)
- `cd frontend && npm run build` – Frontend build
- `docker build -t fussball-dashboard .`
- Keine Lint-/Typecheck-Commands definiert

## Token-Setup
| Token | Typ | Scope | Verwendung |
|-------|-----|-------|------------|
| Fine-grained | `github_pat_*` | Contents + Workflows (nur fussball-dashboard) | Git push (lokal) |
| Classic PAT | `ghp_*` | write:packages + read:packages | Docker push (manuell) |
| `GITHUB_TOKEN` | built-in | packages: write | GitHub Actions (automatisch) |

- Fine-grained Token: in `pass` (GPG-verschlüsselt, Eintrag `fussball-dashboard/git`)
- Classic PAT: in `pass` (GPG-verschlüsselt, Eintrag `fussball-dashboard/docker`)
- GitHub Actions: nutzt automatisch `GITHUB_TOKEN`
- Credential-Helper: Custom Bash-Scripts in `~/.local/bin/`
  - `git-credential-pass` – liest Token aus `pass` für Git
  - `docker-credential-pass` – liest Token aus `pass` für Docker
- GPG-Key: `CC598F2A04284084A6B0CFF193DE3FCE215E854F`
- Kein Klartext in Config-Dateien

## Credential-Helper Scripts

Beide Scripts liegen in `~/.local/bin/` und nutzen `pass` als Backend.

### `git-credential-pass`
- Git ruft das Script automatisch bei `git push/pull` auf
- Liest Token aus `pass show fussball-dashboard/git`
- Konfiguriert in `.git/config`: `credential.https://github.com.helper`
- Unterstützt: `get`, `store`, `erase`

### `docker-credential-pass`
- Docker ruft das Script automatisch bei `docker login/push` auf
- Liest Token aus `pass show fussball-dashboard/docker`
- Konfiguriert in `~/.docker/config.json`: `"credsStore": "pass"`
- Unterstützt: `get`, `store`, `erase`, `list`

## Letzte Session (2026-07-18)
- Token-Setup auf `pass` (GPG) umgestellt
- Custom Credential-Helper Scripts erstellt
- Globaler `gh auth` Helper entfernt
- `golang-docker-credential-helpers` deinstalliert
- Git push + Docker push getestet
- Workflow `.github/workflows/docker.yml` erstellt (automatischer Docker-Build bei Push zu main)

## TODOs
- [ ] `bl3` zu `LIVE_LEAGUES` in server.py hinzufügen (falls Live-Support gewünscht)
