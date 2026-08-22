# AGENTS.md

## Projekt
- **Fußball-Dashboard**: FastAPI (Python 3.12, async SQLAlchemy/SQLite) + Vue 3 (Vite), Datenquelle: OpenLigaDB-API
- Version: `APP_VERSION` in `server.py` (aktuell 0.5.2), ausgeliefert via `/api/version` – bei sichtbaren Änderungen bumpen
- Keine Lint-/Typecheck-/Test-Commands definiert

## Dev-Commands
```bash
pip install --user -r requirements.txt
python3 scraper.py                    # DB füllen/aktualisieren (Upsert, kein Reset)
python3 server.py                     # Backend auf :8080 (uvicorn --reload)
cd frontend && npm install && npm run dev   # :5173, /api wird zu :8080 proxied → Backend muss laufen
cd frontend && npm run build          # → frontend/dist/; Server liefert dist automatisch aus, falls vorhanden
```
Verifizierungsworkflow ohne Tests: `npm run build` + `docker build` + Container-Smoke-Test (`:PORT/api/version`, `/api/leagues`, Index).

## Architektur & Fallstricke
- Ein FastAPI-Prozess macht alles: API + Scheduler (im `lifespan`) + statisches Frontend. Der Mount auf `/` (`server.py`, unten) muss **nach** den API-Routen bleiben.
- **OpenLigaDB-Aufrufe minimieren** ist Designziel:
  - Täglicher Scrape um 08:00 UTC (`SCRAPE_HOUR`, Default 8)
  - Live-Fenster-Loop (`live_window_loop`): pollt nur während laufender Spiele alle `LIVE_POLL_INTERVAL` s (Default 120); Fenster = Anstoß ≤ jetzt < Anstoß+3h
  - Alle Scrape-Aufrufe ausschließlich über `scrape_all_locked()` (gemeinsamer `asyncio.Lock`) – keine zusätzlichen Polling-/Fetch-Logik einbauen
- **UTC-Konvention**: `matches.date` wird als ISO-UTC mit `+00:00` gespeichert; naive OpenLigaDB-Zeiten sind Europe/Berlin und werden via `_to_utc()` konvertiert. Migration in `init_db()` ist idempotent (erkennt anhand tzinfo-Suffix). Frontend rendrt Lokalzeit via `new Date()`.
- `scraper.py`: Upsert-Logik – bestehende Matches werden aktualisiert statt übersprungen, Goals per `goal_id` dedupliziert; `scrape_all()` liefert `(total, total_updated)`.
- **Startseite = Spieltag**: Route `/` rendert `SpieltagView`, Dashboard liegt unter `/dashboard`. Endpoint `/api/spieltag` liefert Spiele des heutigen Kalendertags (Mitternacht Europe/Berlin als UTC-Fenster), je Liga gruppiert in fester Reihenfolge.
- **Scrape-Historie** (`GET /api/scrape-history`): Ringpuffer `deque(maxlen=20)` in `scrape_all_locked(trigger)` – Einträge mit UTC-Zeitstempel, Dauer, total/updated, Trigger `daily`/`live`. Rein RAM-basiert: Nach Neustart leer; der Docker-CMD-Start-Scrape läuft im eigenen Prozess vor uvicorn und taucht nie auf.
- Ligen: `bl1 bl2 bl3 dfb ucl uel` werden gescrapt, aber `LIVE_LEAGUES` (server.py:396) enthält **kein `bl3`** → `/api/live` liefert bl3 nicht.
- Env-Variablen: `DATABASE_PATH` (Default `/app/bundesliga.db`), `SCRAPE_HOUR=8`, `LIVE_CACHE_TTL=300`, `LIVE_POLL_INTERVAL=120`, `BUILD_DATE` (nur CI).

## Frontend-Konventionen
- Bootstrap nur als CSS; **kein bootstrap.bundle.js** – interaktive Widgets (Burger-Menü in App.vue) mit Vue-Refs umsetzen, kein Bootstrap-JS nachrüsten.
- **Spieltag-Polling bewusst minimal**: Auto-Refresh alle 5s *nur* solange ein Spiel läuft (`isLive` = Anstoß ≤ jetzt, nicht beendet) und der Tab sichtbar ist (`document.hidden`); ohne laufende Spiele gar kein Polling (Nutzer-Entscheidung – nicht „verbessern").
- Service Worker (`frontend/public/sw.js`): cache-first für alles außer `/api/`. Bekannte Folge: Nach Deploy sind teils doppelte Reloads nötig. Eine network-first-Fix wurde vom Nutzer **bewusst verworfen** – nicht erneut vorschlagen/implementieren.

## Docker / CI / Deploy
- Multi-Stage-Dockerfile (Node 24-alpine → python 3.12-slim); CMD startet Scraper vor uvicorn (:8080).
- CI `.github/workflows/docker.yml`: Push auf main → baut **nur linux/arm64** und pusht nach `ghcr.io/nschmidle/fussball-dashboard:latest` (privat). Lokal `--platform linux/arm64` verwenden, um CI-Nachzubilden.
- `BUILD_DATE` wird von CI als build-arg gesetzt; ohne Docker zeigt die UI `dev`.
- docker-compose: Directory-Mount (`./data:/app/data`) + `DATABASE_PATH=/app/data/bundesliga.db`; DB liegt auf dem Host.

## Credentials (Maschinen-Setup)
- Git push + Docker push nutzen Tokens aus `pass` (GPG): Einträge `fussball-dashboard/git` (Fine-grained PAT) und `fussball-dashboard/docker` (Classic PAT), gelesen von Custom-Helpern in `~/.local/bin/{git,docker}-credential-pass`.
- CI nutzt GitHub-Secret `CR_PAT` für den ghcr.io-Push.
- Niemals Klartext-Tokens in Repo-/Config-Dateien ablegen.

## TODOs
- [ ] `bl3` zu `LIVE_LEAGUES` in server.py hinzufügen (falls Live-Support gewünscht)
