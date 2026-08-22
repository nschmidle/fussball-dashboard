# Session-Kontext

## Projekt
- **Fußball-Dashboard**: FastAPI (Python 3.12) + Vue 3 (Vite 6.4.3)
- App-Version: 0.5.1 (`APP_VERSION` in server.py, angezeigt im Dashboard via `/api/version`)
- Datenquelle: OpenLigaDB API
- DB: SQLite (`bundesliga.db`), als Directory-Mount (`./data:/app/data`), Pfad via `DATABASE_PATH` env-Variable konfigurierbar (Default: `/app/bundesliga.db`)

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
- Dockerfile: Multi-Stage (Node 24-alpine → Python 3.12-slim)
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
| Classic PAT | `ghp_*` | write:packages + read:packages | Docker push (lokal + CI) |

- Fine-grained Token: in `pass` (GPG-verschlüsselt, Eintrag `fussball-dashboard/git`)
- Classic PAT: in `pass` (GPG-verschlüsselt, Eintrag `fussball-dashboard/docker`)
- Classic PAT: als GitHub Secret `CR_PAT` hinterlegt (für Docker push in CI)
- Credential-Helper: Custom Bash-Scripts in `~/.local/bin/`
  - `git-credential-pass` – liest Token aus `pass` für Git
  - `docker-credential-pass` – liest Token aus `pass` für Docker (nur ghcr.io)
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
- Unterstützt beide Docker-Formate: `host=ghcr.io` (Key=Value) und `ghcr.io` (plain hostname)
- Unterstützt: `get`, `store`, `erase`, `list`
- `~/.docker/config.json` nutzt `"credHelpers": {"ghcr.io": "pass"}` (nur ghcr.io, Docker Hub läuft anonymous)

## Letzte Session (2026-07-18)
- Token-Setup auf `pass` (GPG) umgestellt
- Custom Credential-Helper Scripts erstellt
- Globaler `gh auth` Helper entfernt
- `golang-docker-credential-helpers` deinstalliert
- Git push + Docker push getestet
- Workflow `.github/workflows/docker.yml` erstellt (automatischer Docker-Build bei Push zu main)
- CI: `GITHUB_TOKEN` → `CR_PAT` für ghcr.io-Push (GitHub Actions)
- CI: Actions auf Node 24-kompatible Versionen updaten (checkout@v7, setup-qemu@v4, setup-buildx@v4, login@v4, build-push@v7)
- `docker-credential-pass` gefixt: Host-Check unterstützt `host=ghcr.io` UND plain `ghcr.io`
- `~/.docker/config.json`: `credsStore` → `credHelpers` (Docker Hub läuft anonymous)
- Docker: Node 20-alpine → Node 24-alpine
- Security: vite 6.4.2 → 6.4.3 (0 vulnerabilities)
- Erster erfolgreicher CI-Build (#10)

## Letzte Session (2026-07-19)
- DB-Pfad-Fix: `VOLUME` aus Dockerfile entfernt
- `database.py`: absoluter Pfad + `DATABASE_PATH` env-Variable
- `docker-compose.yml`: File-Mount → Directory-Mount (`./data:/app/data`)
- Bootstrap lokal gebündelt statt CDN (Reverse-Proxy kompatibel)

## Letzte Session (2026-08-21)
- Ziel: OpenLigaDB-Aufrufe auf Minimum reduzieren
- `scraper.py`: Upsert-Logik – vorhandene Matches werden aktualisiert (`score1`/`score2`/`finished`/`date`) statt übersprungen, Goals per `goal_id` dedupliziert; `run()` → wiederverwendbare `scrape_all()`
- `server.py`: täglicher Scheduler im lifespan – Scrape um **08:00 UTC** (`SCRAPE_HOUR` env, Default 8, Container bleibt UTC)
- `server.py`: `/api/live` mit Memory-Cache (`LIVE_CACHE_TTL` env, Default 300s) + `asyncio.Lock` gegen Request-Stampede
- **UTC-Umstellung**: `matches.date` wird ab jetzt als ISO-UTC mit `+00:00` gespeichert; Ingest konvertiert naive OpenLigaDB-Zeiten (Berlin) via `_to_utc()`; Auto-Migration in `init_db()` konvertiert Bestandsdaten einmalig (idempotent, Suffix-Erkennung verhindert Doppelkonvertierung); Frontend bleibt unverändert (`new Date()` mit Offset zeigt weiter Lokalzeit)
- **Live-Fenster-Scheduler** (`live_window_loop`): liest nächsten Kickoff aus eigener DB, schläft in max-1h-Chunks dorthin, pollt ab Anstoß alle `LIVE_POLL_INTERVAL` s (Default 120) via `scrape_all()`, stoppt wenn kein Spiel mehr läuft (Anstoß ≤ jetzt < Anstoß+3h); Restart mitten im Fenster → sofortiger Poll
- Gemeinsamer `asyncio.Lock` (`scrape_all_locked`) um alle Scrape-Aufrufe (Daily ↔ Live-Fenster)
- Request-Bilanz: ohne Frontend/Spiel nur Start-Scrape + 1×/Tag; während Spielen 30 Req/h im Fenster
- Dockerfile CMD, `bundesliga_watcher.py` (nur manuell) und Frontend unverändert

## Letzte Session (2026-08-21, Teil 2)
- Version/Build-Info: `APP_VERSION = "0.5.1"` in server.py + neuer Endpoint `/api/version` (liefert version + build_date)
- `Dockerfile`: `ARG/ENV BUILD_DATE`; CI (`docker.yml`) setzt `BUILD_DATE=$(date -u ...)` als build-arg
- Dashboard zeigt unten `v0.5.1 · Build: <Datum> UTC` (Fallback `dev` ohne Docker); Version angehoben 2.0.0 → **0.5.1**
- Verifiziert mit lokalem Docker-Build + Container-Test

## Letzte Session (2026-08-21, Teil 3)
- Navbar: Burger-Menü mobil (Bootstrap `navbar-expand-lg`, Toggle via Vue-`ref` statt Bootstrap-JS – Bundle bleibt ohne bootstrap.bundle.js), Auto-Close bei Routenwechsel
- Versionszeile unter dem Branding in der Navbar (≈0.72rem, `text-white-50`), Footer-Zeile aus Dashboard.vue entfernt
- Verifiziert mit lokalem Docker-Build + Container-Test

## Letzte Session (2026-08-21, Teil 4)
- Navbar-/Versionsiteration getestet (Burger-Panel als Overlay, Version rechts unter dem Band, Desktop-Links rechtsbündig) – vom Nutzer bewusst **verworfen** (`git restore`, nie committet)
- SW-Fix (v2, network-first für Navigationen) war Teil der Verworfenen und wird **bewusst nicht** nachgebaut → cache-first-Problem (doppelte Reloads nötig) bleibt bestehen

## Letzte Session (2026-08-22)
- Navbar neu (Commits `fe29b41`, `0e89796`, `09ad912`):
  - **Burger-Menü bei allen Breitgrößen** (`navbar-expand-lg` entfernt), Panel `.nav-panel` als schwebendes Overlay rechts unter dem Band (`position:absolute; top:calc(100%+6px); z-index:1030`), enthält Dashboard/Spiele/Tabelle/Statistiken
  - **⚡ Live** steht links neben dem Burger (außerhalb des Panels!), eigene Farben: normal `rgba(255,255,255,.8)`, Hover `#fff`
  - **Burger-Icon dezent ohne Rahmen**: Bootstrap-Toggler-Klassen entfernt → custom `.burger`-Button – 3 feine Linien (22×2px, gap 5px, `rgba(255,255,255,.8)`, Hover `#fff`), kein Rahmen/Glow in keinem Zustand; Morph zu ✕ bei offenem Panel (`.open`: translateY ±7px + rotate 45°, Mittellinie faded); dezenter Outline nur bei `:focus-visible` (Tastatur)
  - Outside-Close via Document-Click-Listener (`onDocClick`, Klicks auf `.nav-right`/`.nav-panel` ausgenommen), Auto-Close bei Routenwechsel, Active-Highlight `isActive()` (exakter Pfadvergleich)
- **Header-Dreiteiler**: Branding links (`.nav-left`-Spalte), Versionsblock zweizeilig (`Version:` / `Build:`) – ≥768px absolut mittig im Band (`translate(-50%,-50%)`, `pointer-events:none`), <768px unter dem Branding; Live+Burger rechts
- Datenbestand aktualisiert: einmaliger Scrape **Saison 2026/27** (1024 Matches: bl1/bl2 306, bl3 380, dfb 32; UCL/UEL liefert OpenLigaDB noch nichts), UTC-Migration konvertierte 1261 Alt-Dates; Archiv 2025/26 bleibt erhalten
- Clean-Rebuild verifiziert: `npm ci && npm run build`, `docker build --no-cache`, Container-Smoke-Test (:8081, `/api/version`+`/api/leagues`+Index OK)
- Navbar-TODOs beides erledigt und aus AGENTS.md entfernt; nur `bl3`-TODO bleibt

## TODOs
- [ ] `bl3` zu `LIVE_LEAGUES` in server.py hinzufügen (falls Live-Support gewünscht)
