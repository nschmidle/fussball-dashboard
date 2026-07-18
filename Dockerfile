# ---- Stage 1: Frontend bauen (Node.js) ----
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY frontend/ .
RUN npm run build

# ---- Stage 2: Backend (Python) ----
FROM python:3.12-slim
WORKDIR /app

# Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf /root/.cache/pip

# Backend-Code kopieren
COPY *.py ./

# Gebautes Frontend aus Stage 1 kopieren
COPY --from=frontend /build/dist frontend/dist

# Port freigeben
EXPOSE 8080

# DB-Pfad als Volume (muss vom Host eingebunden werden)
VOLUME /app/bundesliga.db

# Start (Scraper läuft bei jedem Start, aktualisiert die DB)
CMD ["sh", "-c", "python3 scraper.py && uvicorn server:app --host 0.0.0.0 --port 8080"]
