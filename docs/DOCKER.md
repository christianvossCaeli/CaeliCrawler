# Docker Container Dokumentation

Dieses Dokument beschreibt alle Docker-Container des CaeliCrawler-Projekts und ihre jeweiligen Aufgaben.

## Übersicht

| Container | Image/Build | Port | Beschreibung |
|-----------|-------------|------|--------------|
| postgres | postgres:17-alpine | 5432 | Datenbank |
| redis | redis:7-alpine | 6379 | Message Broker & Cache |
| backend | ./backend | 8000 | FastAPI REST-API |
| celery-worker | ./backend | - | Allgemeiner Worker |
| celery-worker-crawl | ./backend | - | Crawling Worker |
| celery-worker-ai | ./backend | - | KI-Analyse Worker |
| celery-beat | ./backend | - | Task Scheduler |
| frontend | ./frontend | 5173 (dev) / 80 (prod) | Vue.js Web-UI |

---

## Container im Detail

### postgres

**Image:** `postgres:17-alpine`
**Container-Name:** `caelichrawler-postgres`
**Port:** 5432

**Aufgabe:**
PostgreSQL-Datenbank für die persistente Speicherung aller Anwendungsdaten:
- OParl-Entitäten (Organisationen, Personen, Meetings, Dokumente, etc.)
- Crawl-Jobs und deren Status
- Benutzereinstellungen und Konfigurationen
- Dokumenten-Metadaten und Volltextindex

**Volumes:**
- `postgres_data:/var/lib/postgresql/data` - Persistente Datenspeicherung

---

### redis

**Image:** `redis:7-alpine`
**Container-Name:** `caelichrawler-redis`
**Port:** 6379

**Aufgabe:**
Redis dient als:
- **Celery Message Broker** (DB 1): Verteilt Aufgaben an die Worker
- **Celery Result Backend** (DB 2): Speichert Task-Ergebnisse
- **Application Cache** (DB 0): Caching für häufig abgefragte Daten

**Konfiguration:**
- Append-Only-File (AOF) aktiviert für Datenpersistenz

**Volumes:**
- `redis_data:/data` - Persistente Redis-Daten

---

### backend

**Build:** `./backend/Dockerfile`
**Container-Name:** `caelichrawler-backend`
**Port:** 8000

**Aufgabe:**
FastAPI-Backend, das die REST-API bereitstellt:
- API-Endpunkte für alle CRUD-Operationen
- WebSocket-Verbindungen für Echtzeit-Updates
- Authentifizierung und Autorisierung
- Schnittstelle zu PySis (externes System)
- Dokumenten-Upload und -Verwaltung
- Smart Query AI-Assistenten-Endpunkte

**Entwicklungsmodus:**
- Hot-Reload aktiviert (`--reload`)
- Source-Code gemountet für Live-Änderungen

**Produktionsmodus:**
- 4 Worker-Prozesse für bessere Performance
- Kein Hot-Reload

**Volumes:**
- `./backend:/app` - Source-Code (nur Dev)
- `document_storage:/app/storage/documents` - Dokumentenspeicher

---

### celery-worker

**Build:** `./backend/Dockerfile`
**Container-Name:** `caelichrawler-worker`

**Aufgabe:**
Allgemeiner Celery-Worker für:
- **default Queue**: Standard-Hintergrundaufgaben
- **processing Queue**: Dokumentenverarbeitung, PDF-Parsing, Textextraktion

**Konfiguration:**
- Concurrency: 4 (4 parallele Tasks)
- Queues: `default`, `processing`

---

### celery-worker-crawl

**Build:** `./backend/Dockerfile`
**Container-Name:** `caelichrawler-worker-crawl`

**Aufgabe:**
Dedizierter Worker für Crawling-Aufgaben:
- Abrufen von OParl-Endpunkten
- Synchronisation mit externen Ratsinformationssystemen
- Download von Dokumenten und Anhängen

**Konfiguration:**
- Concurrency: 8 (höhere Parallelität für I/O-intensive Aufgaben)
- Queue: `crawl`

---

### celery-worker-ai

**Build:** `./backend/Dockerfile`
**Container-Name:** `caelichrawler-worker-ai`

**Aufgabe:**
Dedizierter Worker für KI-Aufgaben:
- Dokumentenanalyse mit Azure OpenAI
- Embedding-Generierung für Vektorsuche
- Zusammenfassungen und Inhaltsextraktion
- Smart Query Verarbeitung

**Konfiguration:**
- Concurrency: 2 (limitiert wegen API-Rate-Limits)
- Queue: `ai`

---

### celery-beat

**Build:** `./backend/Dockerfile`
**Container-Name:** `caelichrawler-beat`

**Aufgabe:**
Celery Beat Scheduler für zeitgesteuerte Aufgaben:
- Periodische Crawl-Jobs starten
- Regelmäßige Datenaktualisierungen
- Cleanup-Tasks (alte Logs, temporäre Dateien)
- Geplante Synchronisationen

---

### frontend

**Build:** `./frontend/Dockerfile`
**Container-Name:** `caelichrawler-frontend`
**Port:** 5173 (Development) / 80 (Production)

**Aufgabe:**
Vue.js Single-Page-Application:
- Benutzeroberfläche für alle Funktionen
- Dashboard und Visualisierungen
- Dokumenten-Viewer
- Such- und Filteroberfläche
- Echtzeit-Updates via WebSocket
- Smart Query Chat-Interface

**Entwicklungsmodus:**
- Vite Dev-Server mit Hot Module Replacement (HMR)
- Source-Code gemountet

**Produktionsmodus:**
- Statische Build-Dateien
- Nginx als Webserver

**Volumes (nur Dev):**
- `./frontend:/app` - Source-Code
- `/app/node_modules` - Isolierte Node-Module

---

## Volumes

| Volume | Verwendung |
|--------|------------|
| `postgres_data` | PostgreSQL Datenbankdateien |
| `redis_data` | Redis Persistenz (AOF) |
| `document_storage` | Hochgeladene und gecrawlte Dokumente |

---

## Netzwerk

Alle Container befinden sich im selben Docker-Netzwerk und können sich über ihre Service-Namen erreichen:
- Backend → Postgres: `postgres:5432`
- Backend → Redis: `redis:6379`
- Frontend → Backend: `backend:8000`
- Workers → Postgres/Redis: analog

---

## Starten der Umgebung

**Entwicklung:**
```bash
docker-compose up -d
```

**Produktion:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Health Checks

Folgende Container haben Health Checks konfiguriert:
- **postgres**: `pg_isready` prüft Datenbankverbindung
- **redis**: `redis-cli ping` prüft Redis-Verfügbarkeit

Backend und Worker starten erst, wenn postgres und redis healthy sind.
