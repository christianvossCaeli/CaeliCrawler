# CaeliCrawler - Technische Dokumentation

## Inhaltsverzeichnis

1. [Uebersicht](#1-uebersicht)
2. [Systemarchitektur](#2-systemarchitektur)
3. [Technologie-Stack](#3-technologie-stack)
4. [Docker-Infrastruktur](#4-docker-infrastruktur)
5. [Datenbankarchitektur](#5-datenbankarchitektur)
6. [Deployment-Leitfaden](#6-deployment-leitfaden)
7. [Systemvoraussetzungen](#7-systemvoraussetzungen)
8. [Konfiguration](#8-konfiguration)
9. [Sicherheit](#9-sicherheit)
10. [Monitoring und Wartung](#10-monitoring-und-wartung)
11. [Troubleshooting](#11-troubleshooting)
12. [Smart Query System](#12-smart-query-system)
13. [Vollstaendige Umgebungsvariablen-Referenz](#13-vollständige-umgebungsvariablen-referenz)
14. [Vollstaendige API-Referenz](#14-vollständige-api-referenz)

---

## 1. Uebersicht

### Was ist CaeliCrawler?

CaeliCrawler ist eine Enterprise-Plattform fuer automatisiertes Web-Crawling, Dokumentenanalyse und KI-gestuetzte Datenextraktion. Das System ist spezialisiert auf:

- **Web-Crawling**: Automatisiertes Erfassen von Webseiten, APIs und RSS-Feeds
- **Dokumentenverarbeitung**: Extraktion von Text aus PDF, Word, Excel und HTML
- **KI-Analyse**: Intelligente Datenextraktion mittels Azure OpenAI / Claude
- **Entity-Facet-System**: Flexibles Datenmodell fuer strukturierte Informationen
- **Smart Query**: Natuerlichsprachige Abfragen mit KI-Unterstuetzung

### Anwendungsfaelle

- Monitoring kommunaler Ratsinformationssysteme (OParl-Standard)
- Analyse von Ausschreibungen und Beschluessen
- Tracking von Entscheidern und Organisationen
- Aggregation von Nachrichtenquellen
- Integration externer APIs und Datenquellen

---

## 2. Systemarchitektur

### Architektur-Diagramm

```
                                    +------------------+
                                    |    Frontend      |
                                    |   (Vue.js 3)     |
                                    |   Port: 5173     |
                                    +--------+---------+
                                             |
                                             | HTTP/REST
                                             v
+------------------+              +------------------+              +------------------+
|    PostgreSQL    |<----------->|    Backend       |<------------>|     Redis        |
|    Port: 5432    |   SQL/ORM   |   (FastAPI)      |   Cache/MQ   |   Port: 6379     |
|                  |             |   Port: 8000     |              |                  |
+------------------+              +--------+---------+              +------------------+
                                           |
                                           | Celery Tasks
                                           v
                        +------------------------------------------+
                        |            Celery Workers                |
                        |  +------------+  +------------+          |
                        |  | General    |  | Crawl      |          |
                        |  | (4 proc)   |  | (8 proc)   |          |
                        |  +------------+  +------------+          |
                        |  +------------+  +------------+          |
                        |  | AI         |  | Beat       |          |
                        |  | (2 proc)   |  | (Scheduler)|          |
                        |  +------------+  +------------+          |
                        +------------------------------------------+
                                           |
                                           v
                        +------------------------------------------+
                        |          Externe Dienste                 |
                        |  +------------+  +------------+          |
                        |  | Azure      |  | Claude/    |          |
                        |  | OpenAI     |  | Anthropic  |          |
                        |  +------------+  +------------+          |
                        |  +------------+  +------------+          |
                        |  | PySis      |  | SharePoint |          |
                        |  | API        |  | Online     |          |
                        |  +------------+  +------------+          |
                        +------------------------------------------+
```

### Komponenten-Uebersicht

| Komponente | Technologie | Zweck |
|------------|-------------|-------|
| Frontend | Vue.js 3 + Vuetify | Benutzeroberfläche |
| Backend | FastAPI (Python) | REST-API Server |
| Datenbank | PostgreSQL 17 | Persistente Datenhaltung |
| Cache/Broker | Redis 7 | Caching, Message Queue |
| Task Workers | Celery | Hintergrundverarbeitung |
| Scheduler | Celery Beat | Periodische Tasks |

---

## 3. Technologie-Stack

### 3.1 Backend

#### Programmiersprache: Python 3.12

**Warum Python?**
- Exzellente KI/ML-Bibliotheken (OpenAI, LangChain)
- Starkes Web-Crawling-Oekosystem (Scrapy, Playwright)
- Async/Await fuer hohe Parallelitaet
- Grosse Community und Enterprise-Support

#### Framework: FastAPI 0.115+

**Warum FastAPI?**
- Native Async-Unterstuetzung fuer hohe Performance
- Automatische OpenAPI-Dokumentation
- Pydantic-Integration fuer Datenvalidierung
- Typisierung mit Python Type Hints

#### Datenbank-ORM: SQLAlchemy 2.0+

**Warum SQLAlchemy?**
- Vollstaendige Async-Unterstuetzung
- Flexibles Query-Building
- Alembic fuer Migrationen
- PostgreSQL-Optimierungen (JSONB, Full-Text-Search)

#### Task Queue: Celery 5.6

**Warum Celery?**
- Bewaehrte verteilte Task-Verarbeitung
- Flexible Queue-Konfiguration
- Celery Beat fuer Scheduling
- Redis als schneller Broker

#### Wichtige Python-Pakete

| Paket | Version | Zweck |
|-------|---------|-------|
| `uvicorn` | 0.34+ | ASGI Server |
| `asyncpg` | 0.30+ | PostgreSQL Async Driver |
| `openai` | 1.57+ | OpenAI API Integration |
| `langchain` | 0.3+ | LLM Orchestration |
| `scrapy` | 2.12 | Web Scraping |
| `playwright` | 1.49 | Browser Automation |
| `pymupdf` | 1.25+ | PDF Processing |
| `passlib` | - | Passwort-Hashing |
| `python-jose` | - | JWT Tokens |

### 3.2 Frontend

#### Framework: Vue.js 3.5

**Warum Vue.js?**
- Composition API fuer modularen Code
- Reaktives State Management
- Exzellente TypeScript-Integration
- Grosse Komponenten-Bibliotheken

#### UI-Framework: Vuetify 3.7

**Warum Vuetify?**
- Material Design 3 Komponenten
- Responsive out-of-the-box
- Theming-Support (Dark/Light)
- Accessibility (a11y) integriert

#### Build-Tool: Vite 7.0

**Warum Vite?**
- Schnelle Hot Module Replacement
- Optimierte Production Builds
- Native ES Modules
- Code Splitting

#### Wichtige Frontend-Pakete

| Paket | Version | Zweck |
|-------|---------|-------|
| `pinia` | 3.0 | State Management |
| `vue-router` | 4.5 | SPA Routing |
| `vue-i18n` | 11.0 | Internationalisierung |
| `chart.js` | 4.4 | Diagramme |
| `maplibre-gl` | 5.15 | Kartenvisualisierung |
| `axios` | 1.7 | HTTP Client |
| `zod` | 3.24 | Schema-Validierung |

### 3.3 Datenbank: PostgreSQL 17

**Warum PostgreSQL?**
- JSONB fuer flexible Schemas
- Full-Text-Search mit deutscher Sprachunterstuetzung
- GIN-Indizes fuer schnelle Suche
- Transaktionssicherheit (ACID)
- Async-Driver (asyncpg) verfuegbar

### 3.4 Cache/Message Broker: Redis 7

**Warum Redis?**
- In-Memory-Performance
- Pub/Sub fuer Echtzeit-Updates
- Persistenz (AOF) fuer Zuverlaessigkeit
- Celery-Kompatibilitaet

---

## 4. Docker-Infrastruktur

### 4.1 Container-Uebersicht

| Container | Image | Port | Zweck |
|-----------|-------|------|-------|
| `caelichrawler-postgres` | postgres:17-alpine | 5432 | Hauptdatenbank |
| `caelichrawler-redis` | redis:7-alpine | 6379 | Cache & Message Broker |
| `caelichrawler-backend` | Custom (Python) | 8000 | FastAPI Server |
| `caelichrawler-worker` | Custom (Python) | - | Celery General Worker |
| `caelichrawler-worker-crawl` | Custom (Python) | - | Celery Crawl Worker |
| `caelichrawler-worker-ai` | Custom (Python) | - | Celery AI Worker |
| `caelichrawler-beat` | Custom (Python) | - | Celery Scheduler |
| `caelichrawler-frontend` | Custom (Node/Nginx) | 5173/80 | Vue.js Frontend |

### 4.2 Container-Details

#### PostgreSQL

```yaml
postgres:
  image: postgres:17-alpine
  environment:
    POSTGRES_USER: caelichrawler
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: caelichrawler
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U caelichrawler"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Zweck:** Persistente Datenspeicherung fuer alle Anwendungsdaten.

#### Redis

```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
```

**Zweck:**
- DB 0: Anwendungs-Cache & Token Blacklist
- DB 1: Celery Message Broker
- DB 2: Celery Result Backend

#### Backend (FastAPI)

```yaml
backend:
  build: ./backend
  environment:
    DATABASE_URL: postgresql+asyncpg://...
    REDIS_URL: redis://redis:6379/0
    CELERY_BROKER_URL: redis://redis:6379/1
  depends_on:
    postgres: { condition: service_healthy }
    redis: { condition: service_healthy }
```

**Zweck:** REST-API fuer Frontend und externe Integrationen.

#### Celery Workers

```yaml
# General Worker (Default + Processing Queues)
worker:
  command: celery -A workers.celery_app worker -Q default,processing --concurrency=4

# Crawl Worker (Hohe Parallelitaet)
worker-crawl:
  command: celery -A workers.celery_app worker -Q crawl --concurrency=8

# AI Worker (Limitiert wegen API Rate Limits)
worker-ai:
  command: celery -A workers.celery_app worker -Q ai --concurrency=2
```

**Zweck:**
- **General**: Dokumentenverarbeitung, Exports, Benachrichtigungen
- **Crawl**: Web-Crawling mit hoher Parallelitaet
- **AI**: KI-Analysen mit Rate-Limit-Beruecksichtigung

#### Celery Beat

```yaml
beat:
  command: celery -A workers.celery_app beat --loglevel=info
```

**Zweck:** Zeitgesteuerte Tasks (Scheduled Crawls, Cleanup, etc.)

#### Frontend

```yaml
frontend:
  build:
    context: ./frontend
    target: development  # oder production
  environment:
    VITE_API_BASE_URL: http://backend:8000
```

**Zweck:** Vue.js Single-Page-Application.

### 4.3 Volumes

| Volume | Mount-Punkt | Zweck |
|--------|-------------|-------|
| `postgres_data` | /var/lib/postgresql/data | Datenbank-Persistenz |
| `redis_data` | /data | Redis AOF-Persistenz |
| `document_storage` | /app/storage/documents | Gecrawlte Dokumente |

### 4.4 Netzwerk

Alle Container befinden sich im Standard Docker Bridge Network:
- Interne Kommunikation ueber Container-Namen (DNS)
- Beispiel: `postgres:5432`, `redis:6379`, `backend:8000`

---

## 5. Datenbankarchitektur

### 5.1 Haupttabellen

#### Core System

| Tabelle | Zweck |
|---------|-------|
| `entities` | Generische Entitaeten (Gemeinden, Personen, Organisationen) |
| `entity_types` | Entity-Typ-Definitionen (Blueprints) |
| `facet_types` | Facet-Typ-Definitionen (Pain Points, Kontakte, Events) |
| `facet_values` | Konkrete Facet-Instanzen mit Werten |
| `entity_relations` | Beziehungen zwischen Entitaeten |

#### Crawling

| Tabelle | Zweck |
|---------|-------|
| `data_sources` | Crawl-Ziele (Websites, APIs, RSS) |
| `documents` | Gecrawlte Dokumente und Seiten |
| `crawl_jobs` | Crawl-Operationen und Status |
| `categories` | Dokumentenkategorien |

#### Benutzer

| Tabelle | Zweck |
|---------|-------|
| `users` | Benutzerkonten |
| `user_sessions` | Session-Tracking |
| `audit_logs` | Vollstaendiger Audit-Trail |
| `notifications` | Benachrichtigungen |

### 5.2 Entity-Relationship-Diagramm (vereinfacht)

```
+---------------+       +---------------+       +---------------+
|  entity_types |       |   entities    |       | facet_values  |
|---------------|       |---------------|       |---------------|
| id            |<------| entity_type_id|       | entity_id     |----+
| slug          |       | id            |<------| facet_type_id |    |
| name          |       | name          |       | value (JSONB) |    |
| schema (JSON) |       | attributes    |       | confidence    |    |
+---------------+       +---------------+       +---------------+    |
                                                                     |
+---------------+       +---------------+                            |
| facet_types   |       | entity_relations|                          |
|---------------|       |-----------------|                          |
| id            |<------| relation_type_id|                          |
| slug          |       | source_entity_id|<-------------------------+
| value_schema  |       | target_entity_id|
+---------------+       +-----------------+
```

### 5.3 Full-Text-Search

PostgreSQL TSVECTOR mit deutscher Sprachunterstuetzung:

```sql
-- Dokument-Suche
documents.search_vector TSVECTOR (GIN Index)

-- Facet-Suche
facet_values.search_vector TSVECTOR (GIN Index)
```

---

## 6. Deployment-Leitfaden

### 6.1 Voraussetzungen

- Docker >= 24.0
- Docker Compose >= 2.20
- Git
- Mindestens 8 GB RAM
- Mindestens 50 GB freier Speicherplatz

### 6.2 Development Deployment

```bash
# 1. Repository klonen
git clone <repository-url>
cd CaeliCrawler

# 2. Umgebungsvariablen konfigurieren
cp .env.example .env
# .env bearbeiten und API-Keys eintragen

# 3. Container starten
docker-compose up -d

# 4. Datenbank-Migrationen ausfuehren
docker-compose exec backend alembic upgrade head

# 5. Zugriff
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### 6.3 Production Deployment

```bash
# 1. Production Compose verwenden
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 2. Unterschiede zu Development:
# - Uvicorn mit 4 Workers (statt Hot Reload)
# - Frontend via Nginx (Port 80)
# - DEBUG=false
# - Log-Level: warning
# - Restart-Policy: always
```

### 6.4 Production docker-compose.prod.yml

```yaml
version: '3.8'

services:
  backend:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      APP_ENV: production
      DEBUG: "false"
    volumes:
      - document_storage:/app/storage/documents
      # KEIN Source-Mount in Production!
    restart: always

  frontend:
    build:
      target: production
    ports:
      - "80:80"
    restart: always

  worker:
    command: celery -A workers.celery_app worker -Q default,processing,crawl,ai --concurrency=8 --loglevel=warning
    restart: always
```

### 6.5 Reverse Proxy (Nginx)

Fuer Production wird ein Reverse Proxy empfohlen:

```nginx
# /etc/nginx/sites-available/caelichrawler

upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:80;
}

server {
    listen 443 ssl http2;
    server_name caelichrawler.example.com;

    ssl_certificate /etc/letsencrypt/live/caelichrawler.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/caelichrawler.example.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket Support
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 6.6 SSL/TLS mit Let's Encrypt

```bash
# Certbot installieren
sudo apt install certbot python3-certbot-nginx

# Zertifikat beantragen
sudo certbot --nginx -d caelichrawler.example.com

# Auto-Renewal testen
sudo certbot renew --dry-run
```

### 6.7 Backup-Strategie

#### Datenbank-Backup

```bash
# Manuelles Backup
docker-compose exec postgres pg_dump -U caelichrawler caelichrawler > backup_$(date +%Y%m%d).sql

# Automatisches Backup (Cron)
# /etc/cron.d/caelichrawler-backup
0 2 * * * root docker-compose -f /path/to/docker-compose.yml exec -T postgres pg_dump -U caelichrawler caelichrawler | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

#### Volume-Backup

```bash
# Alle Volumes sichern
docker run --rm -v caelichrawler_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data.tar.gz /data
docker run --rm -v caelichrawler_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_data.tar.gz /data
docker run --rm -v caelichrawler_document_storage:/data -v $(pwd):/backup alpine tar czf /backup/documents.tar.gz /data
```

---

## 7. Systemvoraussetzungen

### 7.1 Hardware-Anforderungen

#### Minimum (Development)

| Ressource | Minimum |
|-----------|---------|
| CPU | 4 Cores |
| RAM | 8 GB |
| Storage | 50 GB SSD |
| Netzwerk | 100 Mbit/s |

#### Empfohlen (Production)

| Ressource | Empfohlen |
|-----------|-----------|
| CPU | 8+ Cores |
| RAM | 32 GB |
| Storage | 500 GB NVMe SSD |
| Netzwerk | 1 Gbit/s |

#### High-Volume (Enterprise)

| Ressource | Enterprise |
|-----------|------------|
| CPU | 16+ Cores |
| RAM | 64 GB |
| Storage | 2 TB NVMe SSD (RAID) |
| Netzwerk | 10 Gbit/s |

### 7.2 Software-Anforderungen

| Software | Version | Zweck |
|----------|---------|-------|
| Docker | >= 24.0 | Containerisierung |
| Docker Compose | >= 2.20 | Container-Orchestrierung |
| Linux Kernel | >= 5.4 | Host-System |
| Git | >= 2.30 | Versionskontrolle |

### 7.3 Betriebssystem

**Empfohlen:**
- Ubuntu 22.04 LTS
- Debian 12
- RHEL 9 / Rocky Linux 9

**Unterstuetzt:**
- Jedes Linux mit Docker-Support
- macOS (Development)
- Windows mit WSL2 (Development)

### 7.4 Netzwerk-Anforderungen

#### Ausgehende Verbindungen

| Dienst | Endpunkt | Port |
|--------|----------|------|
| Azure OpenAI | *.openai.azure.com | 443 |
| Anthropic | api.anthropic.com | 443 |
| PySis | pisys.caeli-wind.de | 443 |
| Web-Crawling | * | 80, 443 |

#### Eingehende Verbindungen

| Port | Dienst |
|------|--------|
| 80/443 | HTTP/HTTPS (Frontend + API) |
| 22 | SSH (Administration) |

---

## 8. Konfiguration

### 8.1 Umgebungsvariablen

#### Datenbank

```env
# PostgreSQL
POSTGRES_PASSWORD=<sicheres-passwort>
DATABASE_URL=postgresql+asyncpg://caelichrawler:${POSTGRES_PASSWORD}@postgres:5432/caelichrawler
DATABASE_SYNC_URL=postgresql+psycopg://caelichrawler:${POSTGRES_PASSWORD}@postgres:5432/caelichrawler
```

#### Redis

```env
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

#### Anwendung

```env
APP_ENV=production          # development | production
DEBUG=false                 # true | false
SECRET_KEY=<mindestens-32-zeichen>
```

#### Azure OpenAI

```env
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<api-key>
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-3-large
```

#### Anthropic Claude (Optional)

```env
ANTHROPIC_API_ENDPOINT=https://api.anthropic.com
ANTHROPIC_API_KEY=<api-key>
ANTHROPIC_MODEL=claude-opus-4-5
AI_DISCOVERY_USE_CLAUDE=true
```

#### PySis Integration (Optional)

```env
PYSIS_API_BASE_URL=https://pisys.caeli-wind.de/api/pisys/v1
PYSIS_TENANT_ID=<azure-tenant-id>
PYSIS_CLIENT_ID=<client-id>
PYSIS_CLIENT_SECRET=<client-secret>
PYSIS_SCOPE=api://<scope-id>/.default
```

### 8.2 Celery Task Queues

| Queue | Worker | Concurrency | Tasks |
|-------|--------|-------------|-------|
| `default` | worker | 4 | Allgemeine Tasks |
| `processing` | worker | 4 | Dokumentenverarbeitung |
| `crawl` | worker-crawl | 8 | Web-Crawling |
| `ai` | worker-ai | 2 | KI-Analysen |
| `notification` | worker | 4 | Benachrichtigungen |

### 8.3 Celery Beat Schedule

```python
# Wichtigste periodische Tasks
beat_schedule = {
    # Crawling
    "check-scheduled-crawls": {"schedule": 5.0},  # Alle 5 Sekunden

    # Cleanup
    "cleanup-old-jobs": {"schedule": crontab(hour=3)},  # Taeglich 3:00

    # Processing
    "process-pending-documents": {"schedule": crontab(minute="*/5")},

    # Notifications
    "process-notification-digests": {"schedule": crontab(minute=0)},

    # External APIs
    "sync-external-apis": {"schedule": crontab(hour="*/4")},
}
```

---

## 9. Sicherheit

### 9.1 Authentifizierung

- **JWT-basiert** mit Access (15 min) und Refresh Tokens (7 Tage)
- **Token Blacklist** in Redis fuer sofortigen Logout
- **Passwort-Hashing** mit bcrypt (12 Rounds)

### 9.2 Autorisierung (RBAC)

| Rolle | Berechtigungen |
|-------|----------------|
| VIEWER | Lesen aller Daten, Export |
| EDITOR | + Kategorien, Quellen, Crawler verwalten |
| ADMIN | + Benutzerverwaltung, Audit-Log, System-Config |

### 9.3 Rate Limiting

| Endpunkt | Limit |
|----------|-------|
| Login | 5 Versuche/Minute |
| Fehlgeschlagene Logins | 10/15 Minuten (dann Sperre) |
| Passwort-Aenderung | 3/5 Minuten |
| API (allgemein) | 100/Minute |

### 9.4 Security Headers (Production)

```python
# Automatisch in Production aktiviert
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; ...
```

### 9.5 Audit-Logging

Alle relevanten Aktionen werden protokolliert:
- Benutzeranmeldungen/-abmeldungen
- CRUD-Operationen auf Entitaeten
- Crawl-Starts und -Ergebnisse
- Konfigurationsaenderungen

### 9.6 Secrets Management

**Empfohlene Praktiken:**
1. `.env`-Datei NIE im Git-Repository
2. Docker Secrets fuer Production
3. Externe Secrets Manager (HashiCorp Vault, AWS Secrets Manager)

---

## 10. Monitoring und Wartung

### 10.1 Health Checks

```bash
# Backend Health
curl http://localhost:8000/health

# PostgreSQL
docker-compose exec postgres pg_isready -U caelichrawler

# Redis
docker-compose exec redis redis-cli ping

# Celery Workers
docker-compose exec worker celery -A workers.celery_app inspect ping
```

### 10.2 Logs

```bash
# Alle Container-Logs
docker-compose logs -f

# Spezifische Services
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f worker-ai
```

### 10.3 Metriken (Prometheus)

Das Backend exponiert Prometheus-Metriken:

```bash
curl http://localhost:8000/metrics
```

Verfuegbare Metriken:
- `celery_task_success_total`
- `celery_task_failure_total`
- `celery_task_retry_total`
- `http_requests_total`
- `http_request_duration_seconds`

### 10.4 Datenbank-Wartung

```bash
# Vacuum und Analyze
docker-compose exec postgres psql -U caelichrawler -c "VACUUM ANALYZE;"

# Tabellen-Statistiken
docker-compose exec postgres psql -U caelichrawler -c "
  SELECT relname, n_live_tup, n_dead_tup
  FROM pg_stat_user_tables
  ORDER BY n_dead_tup DESC
  LIMIT 10;
"

# Index-Nutzung pruefen
docker-compose exec postgres psql -U caelichrawler -c "
  SELECT indexrelname, idx_scan, idx_tup_read
  FROM pg_stat_user_indexes
  ORDER BY idx_scan DESC
  LIMIT 10;
"
```

### 10.5 Redis-Wartung

```bash
# Memory-Nutzung
docker-compose exec redis redis-cli INFO memory

# Keys pro Datenbank
docker-compose exec redis redis-cli INFO keyspace

# Celery Queue-Status
docker-compose exec redis redis-cli -n 1 LLEN celery
```

---

## 11. Troubleshooting

### 11.1 Container startet nicht

```bash
# Container-Status pruefen
docker-compose ps

# Logs des fehlerhaften Containers
docker-compose logs <service-name>

# Container neu bauen
docker-compose build --no-cache <service-name>
```

### 11.2 Datenbankverbindung fehlgeschlagen

```bash
# PostgreSQL-Container pruefen
docker-compose exec postgres pg_isready -U caelichrawler

# Manuell verbinden
docker-compose exec postgres psql -U caelichrawler -d caelichrawler

# Connection Pool-Status (im Backend)
docker-compose exec backend python -c "
from app.database import engine
print(engine.pool.status())
"
```

### 11.3 Celery Tasks haengen

```bash
# Aktive Tasks pruefen
docker-compose exec worker celery -A workers.celery_app inspect active

# Queue-Laenge pruefen
docker-compose exec worker celery -A workers.celery_app inspect reserved

# Worker neu starten
docker-compose restart worker worker-crawl worker-ai

# Tasks purgieren (VORSICHT!)
docker-compose exec worker celery -A workers.celery_app purge
```

### 11.4 Out of Memory

```bash
# Memory-Nutzung pro Container
docker stats

# PostgreSQL Memory-Config
docker-compose exec postgres psql -U caelichrawler -c "SHOW shared_buffers;"
docker-compose exec postgres psql -U caelichrawler -c "SHOW work_mem;"
```

### 11.5 Langsame Datenbankabfragen

```bash
# Langsame Queries identifizieren
docker-compose exec postgres psql -U caelichrawler -c "
  SELECT query, calls, mean_time, total_time
  FROM pg_stat_statements
  ORDER BY mean_time DESC
  LIMIT 10;
"

# EXPLAIN ANALYZE fuer spezifische Queries
docker-compose exec postgres psql -U caelichrawler -c "
  EXPLAIN ANALYZE SELECT * FROM entities WHERE entity_type_id = 1;
"
```

### 11.6 Frontend laesst sich nicht bauen

```bash
# Node Modules neu installieren
docker-compose exec frontend rm -rf node_modules
docker-compose exec frontend npm ci

# Cache loeschen
docker-compose exec frontend npm cache clean --force

# Build mit verbose Output
docker-compose exec frontend npm run build -- --debug
```

---

## 12. Smart Query System

### 12.1 Übersicht

Das **Smart Query System** ist eine KI-gestützte, natürlichsprachige Abfrage- und Befehlsverarbeitungs-Engine für das Entity-Facet-System. Es ermöglicht Benutzern, über konversationellen Text mit komplexen Daten zu interagieren.

### 12.2 Architektur

```
Smart Query System
├── API Layer (FastAPI Endpoints)
├── Interpretation Layer (KI-Parsing)
├── Execution Layer (Query + Write Operations)
├── Visualization Layer (Automatische Formatauswahl)
└── Data Access Layer (Entity-Facet Queries)
```

### 12.3 Hauptkomponenten

| Komponente | Pfad | Zweck |
|------------|------|-------|
| `query_interpreter.py` | backend/services/smart_query/ | KI-gestützte Query-Interpretation |
| `data_query_service.py` | backend/services/smart_query/ | Datenabfrage und -formatierung |
| `query_executor.py` | backend/services/smart_query/ | Query-Ausführung |
| `visualization_selector.py` | backend/services/smart_query/ | Automatische Visualisierungsauswahl |
| `write_executor.py` | backend/services/smart_query/ | Schreiboperationen |
| `relation_resolver.py` | backend/services/smart_query/ | Multi-Hop Relation-Auflösung |
| `operations/` | backend/services/smart_query/ | Modulare Operation-Handler |

### 12.4 Betriebsmodi

#### Read Mode (Standard)
Abfragen bestehender Daten mit automatischer Visualisierung.

```
Beispiel: "Zeige alle Gemeinden in NRW mit Pain Points"
→ Gibt formatierte Liste mit Diagramm zurück
```

#### Write Mode (allow_write=true)
Erstellen/Aktualisieren von Entities, Facets, Relations.

```
Beispiel: "Erstelle eine neue Person Max Müller, Bürgermeister von Gummersbach"
→ Erstellt Entity und verknüpft mit Gemeinde
```

#### Plan Mode (mode="plan")
Interaktiver Assistent zur Formulierung korrekter Queries.

```
Beispiel: "Wie kann ich Gemeinden mit Wind-Energie-Problemen finden?"
→ Assistent schlägt optimale Query-Formulierung vor
```

### 12.5 Unterstützte Visualisierungen

| Typ | Verwendung | Datenanforderungen |
|-----|------------|-------------------|
| `table` | Detaillierte Daten, Listen | Beliebige strukturierte Daten |
| `bar_chart` | Kategorienvergleich | 2-15 Kategorien, numerische Werte |
| `line_chart` | Trends, Zeitreihen | Zeitdimension erforderlich |
| `pie_chart` | Verteilung | 2-8 Kategorien, Prozente |
| `stat_card` | KPIs, Einzelwerte | 1-4 numerische Metriken |
| `comparison` | Entity-Vergleich | 2-3 Entities mit gleichen Facets |
| `map` | Geodaten | Lat/Long oder Geometrie |

### 12.6 Relation Chain System

Ermöglicht komplexe Multi-Hop-Abfragen:

```
"Zeige Personen, deren Gemeinden Pain Points haben"
→ persons → [works_for] → municipalities WITH pain_point facet

Max Tiefe: 3 Hops
Richtungen: source (forward), target (reverse)
```

### 12.7 Write Operations

| Operation | Beschreibung |
|-----------|-------------|
| `create_entity` | Neue Entity erstellen |
| `create_facet` | Facet-Wert hinzufügen |
| `create_relation` | Entities verknüpfen |
| `create_entity_type` | Neuen Entity-Typ definieren |
| `create_facet_type` | Neuen Facet-Typ definieren |
| `fetch_and_create_from_api` | Import von externen APIs |
| `start_crawl` | Crawler starten |
| `combined` | Mehrere Operationen |

### 12.8 Performance-Optimierungen

- **Visualization Cache**: 128 Einträge LRU
- **Type Cache**: 5 Minuten TTL
- **Compound Queries**: Parallele Ausführung via asyncio.gather()
- **Max Compound Sub-Queries**: 5

---

## 13. Vollständige Umgebungsvariablen-Referenz

### 13.1 Core Application

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `APP_NAME` | "CaeliCrawler" | Anwendungsname |
| `APP_ENV` | "development" | Environment (development/production) |
| `DEBUG` | false | Debug-Modus |
| `SECRET_KEY` | "change-me-in-production" | Secret Key (min. 32 Zeichen in Prod) |
| `FRONTEND_URL` | "https://app.caeli-wind.de" | Frontend-URL für E-Mail-Links |
| `SCHEDULE_TIMEZONE` | "Europe/Berlin" | Zeitzone für Scheduled Tasks |

### 13.2 Datenbank

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `DATABASE_URL` | postgresql+asyncpg://... | Async PostgreSQL Connection |
| `DATABASE_SYNC_URL` | postgresql://... | Sync PostgreSQL Connection |
| `POSTGRES_PASSWORD` | - | PostgreSQL Passwort |

### 13.3 Redis & Celery

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `REDIS_URL` | redis://localhost:6379/0 | Redis Connection (Cache) |
| `CELERY_BROKER_URL` | redis://localhost:6379/1 | Celery Broker |
| `CELERY_RESULT_BACKEND` | redis://localhost:6379/2 | Celery Results |

### 13.4 Azure OpenAI

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `AZURE_OPENAI_ENDPOINT` | - | Azure OpenAI Endpoint |
| `AZURE_OPENAI_API_KEY` | - | Azure OpenAI API Key |
| `AZURE_OPENAI_API_VERSION` | "2025-04-01-preview" | API Version |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | "gpt-4.1-mini" | Default Deployment |
| `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT` | "text-embedding-3-large" | Embeddings Model |
| `AZURE_OPENAI_DEPLOYMENT_CHAT` | - | Chat Model |
| `AZURE_OPENAI_DEPLOYMENT_EXTRACTION` | - | Extraction Model |
| `AZURE_OPENAI_DEPLOYMENT_PDF` | - | PDF Analysis Model |
| `AZURE_OPENAI_DEPLOYMENT_WEB` | - | Web Extraction Model |
| `AZURE_OPENAI_DEPLOYMENT_CLASSIFICATION` | - | Classification Model |
| `AZURE_OPENAI_DEPLOYMENT_VISION` | - | Vision Model (gpt-4o) |

### 13.5 Azure Document Intelligence

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | - | Document Intelligence Endpoint |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | - | Document Intelligence Key |

### 13.6 Anthropic/Claude

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `ANTHROPIC_API_ENDPOINT` | - | Claude API Endpoint |
| `ANTHROPIC_API_KEY` | - | Claude API Key |
| `ANTHROPIC_MODEL` | "claude-opus-4-5" | Claude Model |
| `AI_DISCOVERY_USE_CLAUDE` | true | Claude für Discovery |

### 13.7 Crawler

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `CRAWLER_USER_AGENT` | "CaeliCrawler/1.0 (Research)" | User-Agent String |
| `CRAWLER_DEFAULT_DELAY` | 2.0 | Request-Delay (Sekunden) |
| `CRAWLER_MAX_CONCURRENT_REQUESTS` | 5 | Max parallele Requests |
| `CRAWLER_RESPECT_ROBOTS_TXT` | true | robots.txt beachten |

### 13.8 Storage

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `DOCUMENT_STORAGE_PATH` | "./storage/documents" | Dokument-Speicherort |
| `ATTACHMENT_STORAGE_PATH` | "./storage/attachments" | Attachment-Speicherort |
| `ATTACHMENT_MAX_SIZE_MB` | 20 | Max Attachment-Größe (MB) |
| `ATTACHMENT_ALLOWED_TYPES` | "image/png,image/jpeg,..." | Erlaubte MIME-Types |

### 13.9 PySis Integration

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `PYSIS_API_BASE_URL` | "https://pisys.caeli-wind.de/api/pisys/v1" | PySis API URL |
| `PYSIS_TENANT_ID` | - | Azure AD Tenant ID |
| `PYSIS_CLIENT_ID` | - | Azure AD Client ID |
| `PYSIS_CLIENT_SECRET` | - | Azure AD Client Secret |
| `PYSIS_SCOPE` | "api://.../.default" | OAuth Scope |

### 13.10 SharePoint Integration

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `SHAREPOINT_TENANT_ID` | - | Azure AD Tenant ID |
| `SHAREPOINT_CLIENT_ID` | - | Azure AD Client ID |
| `SHAREPOINT_CLIENT_SECRET` | - | Azure AD Client Secret |
| `SHAREPOINT_DEFAULT_SITE_URL` | - | Default SharePoint Site |

### 13.11 AI Source Discovery

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `SERPAPI_API_KEY` | - | SerpAPI Key (Primary) |
| `SERPER_API_KEY` | - | Serper.dev Key (Fallback) |
| `AI_DISCOVERY_MAX_SEARCH_RESULTS` | 20 | Max Suchergebnisse |
| `AI_DISCOVERY_MAX_EXTRACTION_PAGES` | 10 | Max Extraction Pages |
| `AI_DISCOVERY_TIMEOUT` | 60 | Timeout (Sekunden) |

### 13.12 Caeli Auction API

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `CAELI_AUCTION_MARKETPLACE_API_URL` | "https://auction.caeli-wind.de/..." | Auction API URL |
| `CAELI_AUCTION_MARKETPLACE_API_AUTH` | - | Base64 Auth Credentials |

### 13.13 E-Mail/SMTP

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `SMTP_HOST` | "smtp.example.com" | SMTP Server |
| `SMTP_PORT` | 587 | SMTP Port |
| `SMTP_USERNAME` | - | SMTP User |
| `SMTP_PASSWORD` | - | SMTP Passwort |
| `SMTP_FROM_EMAIL` | "noreply@caeli-wind.de" | Absender-E-Mail |
| `SMTP_FROM_NAME` | "CaeliCrawler" | Absender-Name |
| `SMTP_USE_TLS` | true | TLS verwenden |
| `SMTP_USE_SSL` | false | SSL verwenden |

### 13.14 Notifications

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `NOTIFICATION_BATCH_SIZE` | 100 | Batch-Größe |
| `NOTIFICATION_RETRY_MAX` | 3 | Max Retries |
| `NOTIFICATION_RETRY_DELAY` | 300 | Retry-Delay (Sekunden) |

### 13.15 Logging

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `LOG_LEVEL` | "INFO" | Log-Level |
| `LOG_FORMAT` | "json" | Log-Format (json/text) |

### 13.16 API Settings

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `API_V1_PREFIX` | "/api/v1" | API v1 Prefix |
| `ADMIN_API_PREFIX` | "/api/admin" | Admin API Prefix |
| `CORS_ORIGINS` | ["http://localhost:5173"] | CORS Origins |

### 13.17 Feature Flags

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `FEATURE_ENTITY_LEVEL_FACETS` | true | Entity-Level Facets |
| `FEATURE_PYSIS_FIELD_TEMPLATES` | false | PySis Field Templates |
| `FEATURE_ENTITY_HIERARCHY` | true | Entity Hierarchien |
| `FEATURE_AUTO_ENTITY_RELATIONS` | true | Auto-Relationen |

### 13.18 Frontend

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `VITE_API_BASE_URL` | "http://backend:8000" | Backend API URL |
| `VITE_MAPBOX_ACCESS_TOKEN` | - | Mapbox Token |

---

## 14. Vollständige API-Referenz

### 14.1 Authentifizierung (`/api/auth`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| POST | `/login` | Anmelden |
| GET | `/me` | Aktueller Benutzer |
| POST | `/logout` | Abmelden |
| POST | `/refresh` | Token erneuern |
| POST | `/change-password` | Passwort ändern |
| POST | `/check-password-strength` | Passwortstärke prüfen |
| PUT | `/language` | Sprache ändern |
| GET | `/sessions` | Aktive Sessions |
| DELETE | `/sessions/{id}` | Session beenden |
| GET | `/email-verification/status` | E-Mail-Status |
| POST | `/email-verification/request` | Verifizierung anfordern |
| POST | `/email-verification/confirm` | E-Mail bestätigen |

### 14.2 Admin - Benutzer (`/api/admin/users`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/` | Benutzer auflisten |
| POST | `/` | Benutzer erstellen |
| GET | `/{id}` | Benutzer abrufen |
| PUT | `/{id}` | Benutzer aktualisieren |
| DELETE | `/{id}` | Benutzer löschen |
| POST | `/{id}/reset-password` | Passwort zurücksetzen |

### 14.3 Admin - Kategorien (`/api/admin/categories`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/` | Kategorien auflisten |
| POST | `/` | Kategorie erstellen |
| GET | `/{id}` | Kategorie abrufen |
| PUT | `/{id}` | Kategorie aktualisieren |
| DELETE | `/{id}` | Kategorie löschen |
| GET | `/{id}/stats` | Kategorie-Statistiken |
| POST | `/preview-ai-setup` | KI-Setup-Vorschau |
| POST | `/{id}/assign-sources-by-tags` | Quellen nach Tags zuweisen |

### 14.4 Admin - Datenquellen (`/api/admin/sources`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/` | Quellen auflisten |
| POST | `/` | Quelle erstellen |
| GET | `/by-tags` | Nach Tags suchen |
| GET | `/{id}` | Quelle abrufen |
| PUT | `/{id}` | Quelle aktualisieren |
| DELETE | `/{id}` | Quelle löschen |
| POST | `/bulk-import` | Massenimport |
| POST | `/{id}/reset` | Status zurücksetzen |
| GET | `/meta/counts` | Aggregierte Zähler |
| GET | `/meta/tags` | Alle Tags |

### 14.5 Admin - Crawler (`/api/admin/crawler`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/jobs` | Jobs auflisten |
| GET | `/jobs/{id}` | Job-Details |
| GET | `/jobs/{id}/log` | Job-Log |
| GET | `/running` | Laufende Jobs |
| POST | `/start` | Crawl starten |
| POST | `/jobs/{id}/cancel` | Job abbrechen |
| GET | `/stats` | Statistiken |
| GET | `/status` | System-Status |
| POST | `/reanalyze` | Neu analysieren |
| GET | `/events` | SSE: Echtzeit-Events |
| GET | `/ai-tasks` | KI-Tasks auflisten |
| POST | `/ai-tasks/{id}/cancel` | KI-Task abbrechen |
| POST | `/documents/{id}/process` | Dokument verarbeiten |
| POST | `/documents/{id}/analyze` | Dokument analysieren |
| POST | `/documents/process-pending` | Pending verarbeiten |
| POST | `/documents/stop-all` | Alle stoppen |

### 14.6 V1 - Entity Types (`/api/v1/entity-types`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/` | Entity-Types auflisten |
| POST | `/` | Entity-Type erstellen |
| GET | `/{id}` | Entity-Type abrufen |
| GET | `/by-slug/{slug}` | Nach Slug abrufen |
| PUT | `/{id}` | Entity-Type aktualisieren |
| DELETE | `/{id}` | Entity-Type löschen |

### 14.7 V1 - Entities (`/api/v1/entities`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/` | Entities auflisten |
| POST | `/` | Entity erstellen |
| GET | `/{id}` | Entity abrufen |
| GET | `/by-slug/{type}/{slug}` | Nach Slug abrufen |
| PUT | `/{id}` | Entity aktualisieren |
| DELETE | `/{id}` | Entity löschen |
| GET | `/{id}/documents` | Entity-Dokumente |
| GET | `/{id}/sources` | Entity-Quellen |
| GET | `/{id}/external-data` | Externe Daten |
| GET | `/{id}/attachments` | Anhänge |

### 14.8 V1 - Facets (`/api/v1/facets`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/types` | Facet-Types auflisten |
| POST | `/types` | Facet-Type erstellen |
| GET | `/types/{id}` | Facet-Type abrufen |
| PUT | `/types/{id}` | Facet-Type aktualisieren |
| DELETE | `/types/{id}` | Facet-Type löschen |
| GET | `/values` | Facet-Values auflisten |
| POST | `/values` | Facet-Value erstellen |
| GET | `/values/{id}` | Facet-Value abrufen |
| PUT | `/values/{id}` | Facet-Value aktualisieren |
| DELETE | `/values/{id}` | Facet-Value löschen |
| GET | `/entity/{id}` | Alle Facets einer Entity |
| GET | `/entity/{id}/history/{type}` | Facet-Historie |

### 14.9 V1 - Relations (`/api/v1/relations`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/types` | Relation-Types auflisten |
| POST | `/types` | Relation-Type erstellen |
| GET | `/` | Relations auflisten |
| POST | `/` | Relation erstellen |
| GET | `/{id}` | Relation abrufen |
| PUT | `/{id}` | Relation aktualisieren |
| DELETE | `/{id}` | Relation löschen |
| GET | `/{entity_id}/graph` | Relations-Graph |

### 14.10 V1 - Smart Query (`/api/v1/analysis`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| POST | `/smart-query` | Smart Query ausführen |
| GET | `/smart-query/history` | Query-Historie |
| GET | `/smart-query/history/{id}` | Query-Details |
| POST | `/smart-query/history/{id}/execute` | Query wiederholen |
| GET | `/reports/overview` | Übersichtsbericht |
| GET | `/reports/entity/{id}` | Entity-Bericht |
| GET | `/templates` | Analyse-Templates |
| POST | `/templates` | Template erstellen |
| GET | `/stats` | Analyse-Statistiken |

### 14.11 V1 - Dashboard (`/api/v1/dashboard`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/preferences` | Dashboard-Einstellungen |
| PUT | `/preferences` | Einstellungen speichern |
| GET | `/stats` | Dashboard-Statistiken |
| GET | `/activity` | Aktivitäts-Feed |
| GET | `/charts/{type}` | Chart-Daten |
| GET | `/insights` | Insights |

### 14.12 V1 - Export (`/api/v1/export`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| POST | `/` | Export starten (async) |
| GET | `/async` | Export-Jobs auflisten |
| GET | `/async/{id}` | Job-Status |
| GET | `/async/{id}/download` | Download |
| POST | `/csv` | CSV-Export (sync) |

### 14.13 V1 - Favorites (`/api/v1/favorites`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/` | Favoriten auflisten |
| POST | `/` | Favorit hinzufügen |
| GET | `/check/{entity_id}` | Status prüfen |
| DELETE | `/{id}` | Favorit entfernen |

### 14.14 V1 - Assistant (`/api/v1/assistant`)

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| POST | `/chat` | Chat-Nachricht (SSE) |
| GET | `/commands` | Verfügbare Commands |
| POST | `/action` | Aktion ausführen |
| POST | `/batch-action` | Batch-Aktion |
| GET | `/batch-action/{id}/status` | Batch-Status |
| POST | `/upload` | Datei hochladen |

### 14.15 System-Endpoints

| Method | Pfad | Beschreibung |
|--------|------|--------------|
| GET | `/` | Root Info |
| GET | `/health` | Health Check |
| GET | `/api/config/features` | Feature Flags |
| GET | `/metrics` | Prometheus Metriken |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |
| GET | `/openapi.json` | OpenAPI Schema |

**Gesamt: ~200+ Endpoints**

---

## Anhang A: Projekt-Struktur

```
CaeliCrawler/
├── backend/
│   ├── app/
│   │   ├── api/           # REST-Endpunkte
│   │   ├── core/          # Sicherheit, Cache, etc.
│   │   ├── models/        # SQLAlchemy Models
│   │   ├── services/      # Business Logic
│   │   ├── schemas/       # Pydantic Schemas
│   │   └── main.py        # FastAPI App
│   ├── workers/           # Celery Tasks
│   ├── crawlers/          # Crawler Implementierungen
│   ├── alembic/           # DB Migrationen
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # Vue Komponenten
│   │   ├── views/         # Seiten
│   │   ├── stores/        # Pinia Stores
│   │   ├── services/      # API Client
│   │   └── locales/       # i18n
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

---

## Anhang B: API-Dokumentation

Die vollstaendige API-Dokumentation ist verfuegbar unter:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

---

## Anhang C: Kontakt und Support

Bei Fragen oder Problemen:
- GitHub Issues: [Repository URL]
- E-Mail: support@caeli-wind.de

---

*Letzte Aktualisierung: Dezember 2025*
*Version: 1.0.0*
