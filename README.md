# ⚽ Fußball Dashboard

Live-Ergebnisse, Tabellen und Statistiken für Bundesliga, Champions League, Europa League und DFB-Pokal.

## Features

- **Dashboard** – Übersicht über alle Ligen, Fortschritt, letzte Spiele
- **Spiele** – Filterbare Liste nach Liga, Spieltag und Team
- **Tabelle** – Liga-Tabelle berechnet aus allen Spielen
- **Statistiken** – Tore pro Spieltag, Ergebnisverteilung, Top-Torjäger (Chart.js)
- **Live** – Echtzeit-Spiele mit Tor-Benachrichtigungen im Browser
- **Push-Benachrichtigungen** – Desktop-Push bei Toren (via Service Worker, benötigt HTTPS)
- **PWA** – Installierbar auf dem Handy-Homescreen

## Datenquellen

Alle Daten kommen von der [OpenLigaDB](https://www.openligadb.de/)-API:

| Liga | Kürzel |
|------|--------|
| 1. Bundesliga | `bl1` |
| 2. Bundesliga | `bl2` |
| 3. Liga | `bl3` |
| DFB-Pokal | `dfb` |
| Champions League | `ucl` |
| Europa League | `uel` |

## Installation

### Voraussetzungen

- Python 3.12+
- Node.js 18+ (für Frontend-Entwicklung)
- Optional: Docker

### Schnellstart

```bash
# Abhängigkeiten installieren
pip install --user fastapi uvicorn sqlalchemy aiosqlite requests pywebpush

# Datenbank füllen
python3 scraper.py

# Server starten
python3 server.py
```

→ `http://localhost:8080`

### Frontend-Entwicklung

```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173 (proxied an :8080)
npm run build      # → Produktions-Build nach frontend/dist/
```

Der Server liefert automatisch den aktuellen Build aus `frontend/dist/` aus.

## API-Endpunkte

| Pfad | Beschreibung |
|------|-------------|
| `GET /api/leagues` | Ligen mit Spielanzahl und Fortschritt |
| `GET /api/matchdays?league=bl1` | Verfügbare Spieltage |
| `GET /api/matches?league=bl1&limit=50` | Gefilterte Spiele |
| `GET /api/standings?league=bl1` | Liga-Tabelle |
| `GET /api/stats?league=bl1` | Statistiken und Top-Torjäger |
| `GET /api/live` | Aktuelle Live-Spiele aller Ligen |
| `GET /api/push/vapid-key` | Öffentlicher VAPID-Key für Push |
| `POST /api/push/subscribe` | Push-Abo registrieren |
| `POST /api/push/test` | Test-Push an alle Abos senden |
| `GET /docs` | Swagger-UI (automatisch) |

## Live-Benachrichtigungen

### Browser-Tab (ohne Setup)
Im Live-Tab "🔔 an" aktivieren – Browser-Notifications bei jedem Tor, solange der Tab offen ist.

### Push (geschlossene App, benötigt HTTPS)
1. Server mit HTTPS bereitstellen
2. Live-Tab → "Push aktivieren"
3. Browser nach Berechtigung fragen
4. Push-Benachrichtigungen auch bei geschlossener App

## Deployment

### Docker

#### Image bauen

Der Build ist als **Multi-Stage-Dockerfile** ausgelegt:
- Stage 1: Frontend-Build mit Node.js
- Stage 2: Python-Runtime, nur das gebaute Frontend wird übernommen

```bash
docker build -t fussball-dashboard .
```

#### Von GitHub Container Registry (ghcr.io)

Das Image liegt auf [ghcr.io](https://ghcr.io) (privat):

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <user> --password-stdin
docker pull ghcr.io/nschmidle/fussball-dashboard:latest
```

#### Starten

```bash
# DB lokal erzeugen (falls nicht vorhanden)
python3 scraper.py

# Starten (DB als Volume, Scraper läuft automatisch beim Start)
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/bundesliga.db:/app/bundesliga.db \
  ghcr.io/nschmidle/fussball-dashboard:latest
```

Die Datenbank liegt auf dem Host und wird bei jedem Container-Start automatisch aktualisiert (der Scraper läuft vor dem Server).

### docker-compose.yml (optional)

```yaml
services:
  app:
    image: ghcr.io/nschmidle/fussball-dashboard:latest
    ports:
      - "8080:8080"
    volumes:
      - ./bundesliga.db:/app/bundesliga.db
```

### Render (kostenlos)

1. Repository auf GitHub pushen
2. Auf [render.com](https://render.com) neuen Web Service erstellen
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn server:app --host 0.0.0.0 --port 10000`
5. Health Check: `/api/leagues`

## Projektstruktur

```
├── Dockerfile              ← Multi-Stage Build
├── requirements.txt        ← Python-Dependencies
├── .dockerignore
├── server.py              ← FastAPI-App + API-Routen
├── database.py            ← SQLAlchemy async Engine
├── models.py              ← DB-Modelle (Match, Goal, PushSubscription)
├── schemas.py             ← Pydantic-Response-Schemata
├── scraper.py             ← Datenimport von OpenLigaDB
├── bundesliga_watcher.py  ← Live-Tor-Alarm (Terminal + Windows Toast)
├── frontend/
│   ├── src/
│   │   ├── App.vue        ← Navigation
│   │   ├── main.js        ← Router
│   │   ├── api.js         ← API-Helper
│   │   └── views/
│   │       ├── Dashboard.vue
│   │       ├── MatchesView.vue
│   │       ├── StandingsView.vue
│   │       ├── StatsView.vue
│   │       └── LiveView.vue
│   ├── public/
│   │   ├── manifest.json  ← PWA-Manifest
│   │   ├── sw.js          ← Service Worker
│   │   └── icon.svg       ← App-Icon
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
└── bundesliga.db          ← SQLite-Datenbank
```

## Daten aktualisieren

```bash
python3 scraper.py
```

Überschreibt keine vorhandenen Einträge (INSERT OR IGNORE). Zum kompletten Neuladen einfach `bundesliga.db` löschen und erneut ausführen.
