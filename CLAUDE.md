# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CaeliCrawler is a modular platform for automated collection, analysis, and management of municipal data. It combines web crawling, AI-powered document analysis, and a flexible Entity-Facet system.

## Tech Stack

- **Backend**: FastAPI 0.115+ (Python 3.13), SQLAlchemy 2.0 (async), PostgreSQL 17 with pgvector, Celery with Redis
- **Frontend**: Vue 3.5 (Composition API), Vuetify 3.7, Pinia 3, Vite 7, TypeScript 5.7
- **AI**: Azure OpenAI, Anthropic Claude, LangChain

## Common Commands

### Backend (from `backend/` directory)

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
pytest

# Run specific test file
pytest tests/test_api/test_entities.py

# Run single test
pytest tests/test_api/test_entities.py::test_create_entity -v

# Linting and formatting
ruff check .
ruff format .

# Type checking
mypy app/

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Frontend (from `frontend/` directory)

```bash
# Install dependencies
npm install

# Dev server
npm run dev

# Build (includes type checking)
npm run build

# Linting
npm run lint

# Unit tests (Vitest)
npm run test

# E2E tests (Playwright)
npm run test:e2e
npm run test:e2e:ui    # With UI
```

### Docker

```bash
# Start all services
docker-compose up -d

# With monitoring stack
docker-compose --profile monitoring up -d

# Run migrations in container
docker-compose exec backend alembic upgrade head

# View logs
docker-compose logs -f backend
```

## Architecture

### Entity-Facet System

The core data model uses:
- **Entities**: Core objects (municipalities, organizations, persons)
- **Entity Types**: Entity classification
- **Facet Types**: Schema definitions for structured data
- **Facet Values**: Concrete values attached to entities

### Worker Architecture

Celery workers are separated by task type:
- **General** (`default`, `processing` queues): Standard tasks, concurrency 4
- **Crawl** (`crawl` queue): Web crawling, concurrency 8
- **AI** (`ai` queue): AI analysis tasks, concurrency 2 (API rate limits)

### Backend Structure

```
backend/
├── app/
│   ├── api/v1/          # REST endpoints (entities, facets, assistant, analysis)
│   ├── core/            # Config, security, dependencies
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   └── utils/           # Utilities
├── services/            # Business logic
│   ├── assistant/       # AI chat assistant
│   ├── smart_query/     # Natural language query engine
│   └── summaries/       # Custom AI reports
├── workers/             # Celery tasks
│   ├── ai_tasks/        # AI analysis tasks
│   └── crawl_tasks.py   # Crawler tasks
└── crawlers/            # Web crawlers (unified, OParl, RSS, SharePoint)
```

### Frontend Structure

```
frontend/src/
├── components/          # Vue components
├── views/               # Page views
├── stores/              # Pinia stores
├── composables/         # Vue composables
├── services/            # API services
├── types/               # TypeScript types
└── locales/             # i18n (de, en)
```

## Code Conventions

### PostgreSQL Enums

Python enum values must exactly match PostgreSQL enum labels. Use UPPERCASE:

```python
class BudgetType(str, Enum):
    GLOBAL = "GLOBAL"    # Correct
    CATEGORY = "CATEGORY"
    # NOT: global = "global"  # Will cause asyncpg errors
```

### Pre-commit Hooks

Pre-commit hooks are configured for:
- Ruff (Python linting + formatting)
- mypy (Python type checking)
- ESLint (Frontend)
- vue-tsc (TypeScript checking)

Install: `pip install pre-commit && pre-commit install`

### Commit Style

Use Conventional Commits format.

## API Documentation

- Interactive docs: http://localhost:8000/docs
- Modular docs in `docs/api/` (AUTH, ENTITIES, SMART_QUERY, ASSISTANT, etc.)

## Environment

Required variables:
- `POSTGRES_PASSWORD` - Database password
- `SECRET_KEY` - JWT secret (32+ chars, required in production)

AI API keys are configured via the Admin UI (Admin > API Credentials), not environment variables.
