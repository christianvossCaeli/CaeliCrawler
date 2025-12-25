# CaeliCrawler

**Intelligente Datenerfassung und -analyse fuer kommunale Informationssysteme**

CaeliCrawler ist eine modulare Plattform zur automatisierten Erfassung, Analyse und Verwaltung kommunaler Daten. Die Anwendung kombiniert Web-Crawling, KI-gestuetzte Dokumentenanalyse und ein flexibles Entity-Facet-System.

---

## Tech Stack

### Backend
- **Framework**: FastAPI 0.115+ (Python 3.12)
- **Datenbank**: PostgreSQL 17 mit pgvector
- **Task Queue**: Celery mit Redis
- **ORM**: SQLAlchemy 2.0 (async)
- **KI**: Azure OpenAI, LangChain
- **Validation**: Pydantic 2.x

### Frontend
- **Framework**: Vue 3.5 (Composition API, script setup)
- **UI Library**: Vuetify 3.7
- **State**: Pinia
- **Build**: Vite 7
- **Sprache**: TypeScript 5.7

### DevOps
- **Container**: Docker Compose
- **Monitoring**: Prometheus, Grafana
- **CI/CD**: GitHub Actions

---

## Quick Start

### Voraussetzungen
- Docker & Docker Compose
- Node.js 20+ (fuer lokale Frontend-Entwicklung)
- Python 3.12+ (fuer lokale Backend-Entwicklung)

### 1. Repository klonen
```bash
git clone <repository-url>
cd CaeliCrawler
```

### 2. Umgebungsvariablen konfigurieren
```bash
cp .env.example .env
# .env bearbeiten und Werte eintragen
```

**Wichtige Variablen:**
- `POSTGRES_PASSWORD` - Datenbank-Passwort
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API Key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI Endpoint

### 3. Services starten
```bash
# Alle Services starten
docker-compose up -d

# Mit Monitoring-Stack
docker-compose --profile monitoring up -d
```

### 4. Datenbank migrieren
```bash
docker-compose exec backend alembic upgrade head
```

### 5. Anwendung aufrufen
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3001 (mit Monitoring-Profil)

---

## Projektstruktur

```
CaeliCrawler/
├── backend/                 # FastAPI Backend
│   ├── app/                 # Haupt-Applikation
│   │   ├── api/             # API-Endpoints (v1, admin)
│   │   ├── core/            # Konfiguration, Security, Dependencies
│   │   ├── models/          # SQLAlchemy Models
│   │   ├── schemas/         # Pydantic Schemas
│   │   └── utils/           # Utilities
│   ├── services/            # Business Logic
│   │   ├── assistant/       # KI-Assistant Service
│   │   ├── smart_query/     # Smart Query Engine
│   │   └── summaries/       # Custom Summaries
│   ├── workers/             # Celery Tasks
│   │   ├── ai_tasks/        # KI-Analysetasks
│   │   └── crawl_tasks.py   # Crawler Tasks
│   ├── crawlers/            # Web Crawler
│   └── tests/               # Backend Tests
├── frontend/                # Vue.js Frontend
│   ├── src/
│   │   ├── components/      # Vue-Komponenten
│   │   ├── views/           # Seiten-Views
│   │   ├── stores/          # Pinia Stores
│   │   ├── composables/     # Vue Composables
│   │   ├── services/        # API-Services
│   │   ├── types/           # TypeScript Types
│   │   └── locales/         # i18n (de, en)
│   └── e2e/                 # Playwright E2E Tests
├── docs/                    # Dokumentation
│   └── api/                 # API-Referenz
├── monitoring/              # Prometheus & Grafana Config
├── docker-compose.yml       # Container-Orchestrierung
└── .env.example             # Umgebungsvariablen Template
```

---

## Entwicklung

### Backend

```bash
cd backend

# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Dependencies installieren
pip install -r requirements.txt

# Development Server starten
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests ausfuehren
pytest

# Linting & Formatting
ruff check .
ruff format .

# Type Checking
mypy app/
```

### Frontend

```bash
cd frontend

# Dependencies installieren
npm install

# Development Server starten
npm run dev

# Build erstellen
npm run build

# Type Checking
npm run type-check

# Linting
npm run lint

# Unit Tests
npm run test

# E2E Tests
npm run test:e2e
```

### Pre-Commit Hooks

```bash
# Pre-Commit installieren
pip install pre-commit
pre-commit install

# Alle Hooks manuell ausfuehren
pre-commit run --all-files
```

---

## API-Dokumentation

Die vollstaendige API-Dokumentation ist modular aufgebaut:

| Bereich | Datei | Beschreibung |
|---------|-------|--------------|
| **Uebersicht** | [docs/api/README.md](docs/api/README.md) | API-Schnellstart |
| **Auth** | [docs/api/AUTH.md](docs/api/AUTH.md) | Authentifizierung |
| **Entities** | [docs/api/ENTITIES.md](docs/api/ENTITIES.md) | Entity-Facet System |
| **Analysis** | [docs/api/ANALYSIS.md](docs/api/ANALYSIS.md) | Analyse & Reports |
| **Smart Query** | [docs/api/SMART_QUERY.md](docs/api/SMART_QUERY.md) | KI-Abfragen |
| **Assistant** | [docs/api/ASSISTANT.md](docs/api/ASSISTANT.md) | Chat-Assistant |
| **Admin** | [docs/api/ADMIN.md](docs/api/ADMIN.md) | Admin-Funktionen |

**Interaktive Dokumentation:** http://localhost:8000/docs (Swagger UI)

---

## Architektur

### Entity-Facet System

CaeliCrawler verwendet ein flexibles Entity-Facet-System:

- **Entities**: Kern-Objekte (Gemeinden, Organisationen, Personen)
- **Entity Types**: Typisierung der Entities
- **Facet Types**: Schema-Definition fuer strukturierte Daten
- **Facet Values**: Konkrete Werte zu Entities

### KI-Integration

- **Dokumentenanalyse**: Automatische Extraktion strukturierter Daten
- **Smart Query**: Natuerlichsprachliche Datenabfragen
- **Assistant**: Interaktiver Chat-Assistent
- **Custom Summaries**: Konfiguierbare KI-Berichte

### Worker-Architektur

```
┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│    Redis    │
│   Backend   │     │   Broker    │
└─────────────┘     └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│   Worker    │   │   Worker    │   │   Worker    │
│   General   │   │   Crawl     │   │     AI      │
│   (default) │   │   (crawl)   │   │   (ai)      │
└─────────────┘   └─────────────┘   └─────────────┘
```

---

## Deployment

### Production Build

```bash
# Frontend Build
cd frontend && npm run build

# Docker Images bauen
docker-compose build

# Mit Production Config starten
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Umgebungsvariablen (Production)

```bash
APP_ENV=production
DEBUG=false
POSTGRES_PASSWORD=<secure-password>
AZURE_OPENAI_API_KEY=<api-key>
# ... weitere Variablen in .env.example
```

### Monitoring aktivieren

```bash
docker-compose --profile monitoring up -d
```

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001

---

## Testing

### Backend Tests
```bash
cd backend
pytest                       # Alle Tests
pytest tests/test_api/       # Nur API Tests
pytest -v --cov=app          # Mit Coverage
```

### Frontend Tests
```bash
cd frontend
npm run test                 # Unit Tests (Vitest)
npm run test:e2e             # E2E Tests (Playwright)
npm run test:e2e -- --ui     # Mit Playwright UI
```

---

## Sicherheit

- **Authentifizierung**: JWT-basiert mit Access/Refresh Tokens
- **Autorisierung**: Rollenbasiert (Admin, Editor, Viewer)
- **Rate Limiting**: Schutz vor API-Missbrauch
- **XSS-Schutz**: DOMPurify fuer User-Content
- **CORS**: Konfigurierbare Origins
- **Secrets**: Alle sensiblen Daten via Umgebungsvariablen

**Wichtig:** Niemals `.env` Dateien committen!

---

## Beitragen

1. Feature-Branch erstellen
2. Pre-Commit Hooks aktivieren
3. Tests schreiben
4. PR erstellen

### Code-Standards
- **Python**: Ruff (Linting + Formatting), mypy (Type Checking)
- **TypeScript**: ESLint, Prettier
- **Commits**: Conventional Commits

---

## Lizenz

Proprietaer - Alle Rechte vorbehalten.

---

## Support

Bei Fragen oder Problemen:
- Issues im Repository erstellen
- API-Dokumentation konsultieren
- Logs pruefen: `docker-compose logs -f <service>`
