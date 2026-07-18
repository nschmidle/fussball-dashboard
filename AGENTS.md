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

## Letzte Session (2026-05-16)
- Docker-Image für `linux/arm64` lokal gebaut (76.7 MB)
- Push zu ghcr.io fehlgeschlagen – Token ohne Schreibrechte
- Buildx-Builder `arm64builder` aktiv, QEMU-Emulation installiert

## TODOs
- [ ] Image pushen mit Token mit Schreibrechten (`docker push ghcr.io/nschmidle/fussball-dashboard:latest`)
- [ ] `bl3` zu `LIVE_LEAGUES` in server.py hinzufügen (falls Live-Support gewünscht)
