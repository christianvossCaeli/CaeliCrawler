# CaeliCrawler - Implementierungsplan

## Executive Summary

CaeliCrawler ist eine interne Datensammlungsplattform zur automatisierten Erfassung und Analyse von kommunalen Informationen (z.B. Gemeinderatsbeschlüsse zu Windkraft-Restriktionen). Die Plattform kombiniert Web-Crawling, API-Integration, PDF-Verarbeitung und KI-gestützte Datenanalyse.

---

## 1. Technologie-Stack

### Backend-Framework: **Python mit FastAPI**

**Begründung:**
- Hervorragende KI/ML-Integration (Azure OpenAI, LangChain)
- Asynchrone Verarbeitung nativ unterstützt
- Hohe Performance bei I/O-bound Tasks
- Einfache Deployment auf Managed Servern
- Umfangreiches Ökosystem für Web-Scraping (Scrapy, Playwright)

### Komponenten-Übersicht

| Komponente | Technologie | Zweck |
|------------|-------------|-------|
| API/Backend | FastAPI | REST-API, Admin-Backend |
| Frontend | Vue.js 3 + Vuetify | Admin-Dashboard |
| Task Queue | Celery + Redis | Asynchrone Crawler-Jobs |
| Datenbank | PostgreSQL | Strukturierte Daten |
| Dokumenten-Index | Elasticsearch (optional) | Volltextsuche über PDFs |
| PDF-Verarbeitung | PyMuPDF + Azure AI Document Intelligence | Text-Extraktion |
| Web-Crawling | Scrapy + Playwright | Seitennavigation & Scraping |
| KI-Analyse | Azure OpenAI (GPT-4o) | Inhaltsanalyse & Klassifizierung |
| Change Detection | Custom Scheduler | Änderungserkennung |

---

## 2. Systemarchitektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Vue.js 3)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Dashboard   │  │  Kategorien  │  │  Datenquellen│  │  Ergebnisse  │    │
│  │  & Status    │  │  verwalten   │  │  konfigurieren│  │  & Export   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  /api/admin  │  │ /api/sources │  │ /api/crawlers│  │  /api/data   │    │
│  │  Kategorien  │  │  URL-Mgmt    │  │  Job-Control │  │  Output API  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│     CELERY WORKER    │  │   REDIS BROKER   │  │    POSTGRESQL DB     │
│  ┌────────────────┐  │  │                  │  │  ┌────────────────┐  │
│  │ Crawler Tasks  │  │  │  - Task Queue    │  │  │ Kategorien     │  │
│  │ PDF Processing │  │  │  - Result Store  │  │  │ Datenquellen   │  │
│  │ AI Analysis    │  │  │  - Cache         │  │  │ Crawl-Results  │  │
│  │ Change Detection│ │  │  - Rate Limiting │  │  │ Dokumente      │  │
│  └────────────────┘  │  │                  │  │  │ Änderungslog   │  │
└──────────────────────┘  └──────────────────┘  │  └────────────────┘  │
                                               └──────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNE DIENSTE                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Azure OpenAI │  │  OParl APIs  │  │  Gemeinde-   │  │  Webhook     │    │
│  │ GPT-4o       │  │  (Kommunen)  │  │  Websites    │  │  Endpunkte   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Datenmodell

### 3.1 Hauptentitäten

```python
# categories - Kategorien (z.B. "Gemeinden", "Landkreise")
class Category:
    id: UUID
    name: str                          # "Gemeinden"
    description: str                   # Beschreibung
    purpose: str                       # "Windkraft-Restriktionen analysieren"
    search_terms: list[str]            # ["Windkraft", "Bebauungsplan", "Flächennutzung"]
    document_types: list[str]          # ["Gemeinderatsbeschluss", "Sitzungsprotokoll"]
    ai_extraction_prompt: str          # Custom Prompt für KI-Analyse
    schedule_cron: str                 # "0 2 * * *" (täglich 2 Uhr)
    is_active: bool
    created_at: datetime
    updated_at: datetime

# data_sources - Datenquellen pro Kategorie
class DataSource:
    id: UUID
    category_id: UUID                  # FK zu Category
    name: str                          # "Gemeinde Musterstadt"
    source_type: SourceType            # WEBSITE | OPARL_API | RSS | CUSTOM_API
    base_url: str                      # "https://gemeinde-musterstadt.de"
    api_endpoint: str | None           # OParl Endpoint falls vorhanden
    crawl_config: dict                 # Scraping-Konfiguration (Selektoren etc.)
    auth_config: dict | None           # API-Keys, Login-Daten (verschlüsselt)
    last_crawl: datetime | None
    last_change_detected: datetime | None
    content_hash: str | None           # Für Change Detection
    status: SourceStatus               # ACTIVE | PAUSED | ERROR | PENDING
    error_message: str | None
    metadata: dict                     # Zusätzliche Infos (Bundesland, Einwohner, etc.)

# crawl_jobs - Crawling-Aufträge
class CrawlJob:
    id: UUID
    source_id: UUID
    category_id: UUID
    status: JobStatus                  # PENDING | RUNNING | COMPLETED | FAILED
    started_at: datetime | None
    completed_at: datetime | None
    pages_crawled: int
    documents_found: int
    documents_processed: int
    error_log: list[str]
    stats: dict                        # Detaillierte Statistiken

# documents - Gefundene Dokumente
class Document:
    id: UUID
    source_id: UUID
    category_id: UUID
    crawl_job_id: UUID
    document_type: str                 # "PDF" | "HTML" | "DOC"
    original_url: str
    title: str
    file_path: str | None              # Lokaler Speicherpfad
    file_hash: str                     # SHA256 für Duplikat-Erkennung
    raw_text: str | None               # Extrahierter Rohtext
    page_count: int | None
    file_size: int
    discovered_at: datetime
    processed_at: datetime | None
    processing_status: ProcessingStatus

# extracted_data - KI-extrahierte Informationen
class ExtractedData:
    id: UUID
    document_id: UUID
    category_id: UUID
    extraction_type: str               # "Windkraft-Beschluss", "Flächennutzung"
    extracted_content: dict            # Strukturierte extrahierte Daten
    confidence_score: float            # 0.0 - 1.0
    ai_model_used: str                 # "gpt-4o-2024-08-06"
    ai_prompt_version: str
    raw_ai_response: str
    human_verified: bool
    human_corrections: dict | None
    created_at: datetime
    updated_at: datetime

# change_log - Änderungsprotokoll
class ChangeLog:
    id: UUID
    source_id: UUID
    detected_at: datetime
    change_type: ChangeType            # NEW_DOCUMENT | CONTENT_CHANGED | REMOVED
    old_hash: str | None
    new_hash: str
    affected_url: str
    details: dict

# api_exports - Konfigurierte Export-Endpunkte
class ApiExport:
    id: UUID
    name: str
    category_id: UUID | None           # NULL = alle Kategorien
    endpoint_type: ExportType          # INTERNAL_API | WEBHOOK | PUSH_TO_EXTERNAL
    config: dict                       # URL, Auth, Format, Filter
    last_export: datetime | None
    is_active: bool
```

### 3.2 PostgreSQL Schema

```sql
-- Enums
CREATE TYPE source_type AS ENUM ('WEBSITE', 'OPARL_API', 'RSS', 'CUSTOM_API');
CREATE TYPE source_status AS ENUM ('ACTIVE', 'PAUSED', 'ERROR', 'PENDING');
CREATE TYPE job_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED');
CREATE TYPE processing_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
CREATE TYPE change_type AS ENUM ('NEW_DOCUMENT', 'CONTENT_CHANGED', 'REMOVED');
CREATE TYPE export_type AS ENUM ('INTERNAL_API', 'WEBHOOK', 'PUSH_TO_EXTERNAL');

-- Kategorien
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    purpose TEXT NOT NULL,
    search_terms JSONB DEFAULT '[]',
    document_types JSONB DEFAULT '[]',
    ai_extraction_prompt TEXT,
    schedule_cron VARCHAR(100) DEFAULT '0 2 * * *',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Datenquellen
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type source_type NOT NULL,
    base_url TEXT NOT NULL,
    api_endpoint TEXT,
    crawl_config JSONB DEFAULT '{}',
    auth_config JSONB,
    last_crawl TIMESTAMPTZ,
    last_change_detected TIMESTAMPTZ,
    content_hash VARCHAR(64),
    status source_status DEFAULT 'PENDING',
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(category_id, base_url)
);

-- Index für schnelle Suche nach Status
CREATE INDEX idx_sources_status ON data_sources(status);
CREATE INDEX idx_sources_category ON data_sources(category_id);
CREATE INDEX idx_sources_last_crawl ON data_sources(last_crawl);

-- Crawl Jobs
CREATE TABLE crawl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id),
    status job_status DEFAULT 'PENDING',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    pages_crawled INTEGER DEFAULT 0,
    documents_found INTEGER DEFAULT 0,
    documents_processed INTEGER DEFAULT 0,
    error_log JSONB DEFAULT '[]',
    stats JSONB DEFAULT '{}'
);

CREATE INDEX idx_jobs_status ON crawl_jobs(status);
CREATE INDEX idx_jobs_source ON crawl_jobs(source_id);

-- Dokumente
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id),
    crawl_job_id UUID REFERENCES crawl_jobs(id),
    document_type VARCHAR(50) NOT NULL,
    original_url TEXT NOT NULL,
    title TEXT,
    file_path TEXT,
    file_hash VARCHAR(64) NOT NULL,
    raw_text TEXT,
    page_count INTEGER,
    file_size BIGINT,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    processing_status processing_status DEFAULT 'PENDING',
    UNIQUE(source_id, file_hash)
);

CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_documents_source ON documents(source_id);
CREATE INDEX idx_documents_hash ON documents(file_hash);

-- Extrahierte Daten
CREATE TABLE extracted_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    category_id UUID NOT NULL REFERENCES categories(id),
    extraction_type VARCHAR(255) NOT NULL,
    extracted_content JSONB NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    ai_model_used VARCHAR(100),
    ai_prompt_version VARCHAR(50),
    raw_ai_response TEXT,
    human_verified BOOLEAN DEFAULT false,
    human_corrections JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_extracted_document ON extracted_data(document_id);
CREATE INDEX idx_extracted_type ON extracted_data(extraction_type);
CREATE INDEX idx_extracted_verified ON extracted_data(human_verified);

-- Änderungsprotokoll
CREATE TABLE change_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    change_type change_type NOT NULL,
    old_hash VARCHAR(64),
    new_hash VARCHAR(64),
    affected_url TEXT,
    details JSONB DEFAULT '{}'
);

CREATE INDEX idx_changelog_source ON change_log(source_id);
CREATE INDEX idx_changelog_date ON change_log(detected_at DESC);

-- API Export Konfigurationen
CREATE TABLE api_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category_id UUID REFERENCES categories(id),
    endpoint_type export_type NOT NULL,
    config JSONB NOT NULL,
    last_export TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Volltext-Suche über Dokumente (PostgreSQL native)
ALTER TABLE documents ADD COLUMN search_vector tsvector;
CREATE INDEX idx_documents_search ON documents USING GIN(search_vector);

-- Trigger für automatische Aktualisierung des Suchvektors
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('german', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.raw_text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER documents_search_update
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_search_vector();
```

---

## 4. Verfügbare Datenquellen & APIs

### 4.1 OParl - Offene Parlamentarische Informationen

**Was ist OParl?**
OParl ist ein deutscher Standard für den offenen Zugriff auf kommunale Ratsinformationssysteme.

**Technische Details:**
- REST-API mit JSON-Responses
- Keine Authentifizierung erforderlich (öffentliche Daten)
- Version: OParl 1.1

**Beispiel-Endpunkte:**
```
# System-Informationen
https://oparl.stadt-muenster.de/system

# Körperschaften (Gemeinden, Landkreise)
https://oparl.stadt-muenster.de/bodies

# Sitzungen mit Tagesordnungen
https://oparl.stadt-muenster.de/meetings

# Drucksachen und Beschlüsse
https://oparl.stadt-muenster.de/papers
```

**Verfügbare Kommunen (Auswahl):**
- Köln, Düsseldorf, Münster, Aachen
- 27+ Kommunen in NRW über Open.NRW
- Weitere über [Politik bei uns](https://politik-bei-uns.de/)

**Quellen:**
- [OParl Hauptseite](https://oparl.org/)
- [OParl für Entwickler](https://oparl.org/oparl-fuer-entwickler/)
- [NRW OParl-Kommunen](https://open.nrw/open-data/showroom/nutzung-von-oparl-kommunen-aus-nrw)

### 4.2 Politik bei uns

**Beschreibung:** Aggregator für OParl-Daten mit erweiterter Suche.

**Features:**
- Volltextsuche über alle Kommunen
- Geolokalisierung von Beschlüssen
- GitHub: [politik-bei-uns](https://github.com/politik-bei-uns)

### 4.3 GovData

**URL:** https://www.govdata.de/

**Beschreibung:** Zentrales Datenportal für Open Government Data in Deutschland.

**Nutzung:** Metadaten-Suche für verfügbare Datensätze auf allen Verwaltungsebenen.

### 4.4 GENESIS-Datenbank

**URL:** https://www-genesis.destatis.de/

**Beschreibung:** Statistische Daten zu allen Gemeinden (Einwohner, Fläche, etc.).

**API:** RESTful JSON-Schnittstelle verfügbar.

### 4.5 XPlanung24

**URL:** https://xplanung24.de/

**Beschreibung:** Digitale Bauleitplanung mit 400+ Städten und Gemeinden.

**Relevanz:** Flächennutzungspläne, Bebauungspläne (relevant für Windkraft-Standorte).

---

## 5. Crawler-Strategie

### 5.1 Multi-Source Crawler Architektur

```python
# Abstrakte Basis für verschiedene Crawler-Typen
class BaseCrawler(ABC):
    @abstractmethod
    async def crawl(self, source: DataSource) -> CrawlResult:
        pass

    @abstractmethod
    async def detect_changes(self, source: DataSource) -> list[Change]:
        pass

class OparlCrawler(BaseCrawler):
    """Spezialisierter Crawler für OParl-APIs"""

class WebsiteCrawler(BaseCrawler):
    """Scrapy-basierter Crawler für reguläre Websites"""

class RSSCrawler(BaseCrawler):
    """Crawler für RSS/Atom Feeds"""
```

### 5.2 Crawling-Workflow

```
┌──────────────────────────────────────────────────────────────────┐
│                     SCHEDULER (Celery Beat)                       │
│                                                                   │
│  Prüft alle aktiven Kategorien gemäß schedule_cron               │
│  Erstellt CrawlJobs für fällige DataSources                      │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    CHANGE DETECTION                               │
│                                                                   │
│  1. HEAD Request oder Hash-Vergleich                             │
│  2. OParl: Prüfe "modified" Timestamps                           │
│  3. Websites: Compare content_hash                               │
│  4. Bei Änderung → starte Crawl                                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                      CRAWL EXECUTION                              │
│                                                                   │
│  OParl:                                                          │
│  ├─ GET /papers?modified_after={last_crawl}                      │
│  └─ Iteriere durch Pagination                                    │
│                                                                   │
│  Website:                                                         │
│  ├─ Scrapy Spider mit konfigurierten Selektoren                  │
│  ├─ Folge internen Links (max_depth konfigurierbar)             │
│  └─ Playwright für JavaScript-gerenderte Seiten                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                   DOCUMENT PROCESSING                             │
│                                                                   │
│  1. Download PDFs/Dokumente                                      │
│  2. Deduplizierung via file_hash                                 │
│  3. Text-Extraktion:                                             │
│     - PDF: PyMuPDF / Azure Document Intelligence                 │
│     - HTML: BeautifulSoup                                        │
│     - DOC/DOCX: python-docx                                      │
│  4. Speichere raw_text in documents Tabelle                      │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     AI ANALYSIS                                   │
│                                                                   │
│  1. Lade category.ai_extraction_prompt                           │
│  2. Sende an Azure OpenAI GPT-4o:                                │
│     - System Prompt mit Extraktionsregeln                        │
│     - Document Text als User Content                             │
│     - Structured Output (JSON Schema)                            │
│  3. Speichere in extracted_data mit confidence_score             │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                   NOTIFICATION & EXPORT                           │
│                                                                   │
│  1. Neue relevante Daten erkannt?                                │
│  2. Trigger konfigurierte Webhooks                               │
│  3. Push zu externen APIs falls konfiguriert                     │
│  4. Update Dashboard-Statistiken                                 │
└──────────────────────────────────────────────────────────────────┘
```

### 5.3 Rate Limiting & Politeness

```python
CRAWL_CONFIG = {
    "default_delay": 2.0,           # Sekunden zwischen Requests
    "max_concurrent_requests": 5,   # Pro Domain
    "respect_robots_txt": True,
    "user_agent": "CaeliCrawler/1.0 (Research; contact@example.com)",
    "retry_times": 3,
    "retry_backoff": "exponential",
}
```

---

## 6. KI-Integration (Azure OpenAI)

### 6.1 Konfiguration

```python
# Azure OpenAI Setup
AZURE_OPENAI_CONFIG = {
    "endpoint": "https://your-resource.openai.azure.com/",
    "api_version": "2024-08-01-preview",
    "deployment_name": "gpt-4o",
    "max_tokens": 4096,
}
```

### 6.2 Beispiel: Windkraft-Extraktions-Prompt

```python
WINDKRAFT_EXTRACTION_PROMPT = """
Du bist ein Experte für die Analyse kommunaler Dokumente bezüglich Windkraft-Regelungen.

Analysiere das folgende Dokument und extrahiere strukturiert:

1. **Dokumenttyp**: (Beschluss, Protokoll, Satzung, Bebauungsplan, etc.)
2. **Datum**: Wann wurde das Dokument erstellt/beschlossen?
3. **Gemeinde/Kommune**: Welche Kommune betrifft das Dokument?
4. **Windkraft-Relevanz**: (hoch/mittel/gering/keine)
5. **Zusammenfassung**: Kurze Zusammenfassung des Inhalts (max 200 Wörter)
6. **Restriktionen**: Liste aller erwähnten Einschränkungen für Windkraft:
   - Abstandsregelungen (z.B. "1000m zu Wohnbebauung")
   - Höhenbeschränkungen
   - Ausschlussgebiete
   - Sonstige Auflagen
7. **Fördernde Maßnahmen**: Liste aller positiven Regelungen für Windkraft
8. **Erwähnte Gesetze/Verordnungen**: Referenzen auf andere Rechtsgrundlagen
9. **Status**: (geplant, beschlossen, in Kraft, aufgehoben)

Antworte im JSON-Format.
"""
```

### 6.3 Structured Output Schema

```python
from pydantic import BaseModel, Field

class WindkraftRestriktion(BaseModel):
    typ: str = Field(description="Art der Restriktion")
    wert: str = Field(description="Konkreter Wert/Beschreibung")
    quelle_im_dokument: str = Field(description="Zitat aus dem Dokument")

class WindkraftAnalyse(BaseModel):
    dokumenttyp: str
    datum: str | None
    gemeinde: str
    windkraft_relevanz: Literal["hoch", "mittel", "gering", "keine"]
    zusammenfassung: str
    restriktionen: list[WindkraftRestriktion]
    foerdernde_massnahmen: list[str]
    erwaehnete_gesetze: list[str]
    status: str
    confidence: float = Field(ge=0, le=1)
```

---

## 7. API-Endpunkte

### 7.1 Admin-API

```yaml
# Kategorien
POST   /api/admin/categories              # Neue Kategorie erstellen
GET    /api/admin/categories              # Alle Kategorien auflisten
GET    /api/admin/categories/{id}         # Kategorie-Details
PUT    /api/admin/categories/{id}         # Kategorie aktualisieren
DELETE /api/admin/categories/{id}         # Kategorie löschen

# Datenquellen
POST   /api/admin/sources                 # Neue Datenquelle hinzufügen
GET    /api/admin/sources                 # Alle Quellen (mit Filter)
GET    /api/admin/sources/{id}            # Quellen-Details
PUT    /api/admin/sources/{id}            # Quelle aktualisieren
DELETE /api/admin/sources/{id}            # Quelle löschen
POST   /api/admin/sources/bulk-import     # CSV/JSON Import von URLs

# Crawl-Steuerung
POST   /api/admin/crawl/start             # Crawl manuell starten
POST   /api/admin/crawl/stop/{job_id}     # Crawl stoppen
GET    /api/admin/crawl/status            # Aktuelle Jobs
GET    /api/admin/crawl/history           # Job-Historie

# Dokumente & Daten
GET    /api/admin/documents               # Dokumente durchsuchen
GET    /api/admin/documents/{id}          # Dokument-Details
PUT    /api/admin/extracted/{id}          # Extrahierte Daten korrigieren
POST   /api/admin/extracted/{id}/verify   # Als verifiziert markieren
```

### 7.2 Output-API (für externe Konsumenten)

```yaml
# Öffentliche Daten-API
GET    /api/v1/data                       # Alle extrahierten Daten
GET    /api/v1/data/categories/{slug}     # Daten einer Kategorie
GET    /api/v1/data/sources/{id}          # Daten einer Quelle
GET    /api/v1/search                     # Volltextsuche
GET    /api/v1/changes                    # Änderungsfeed (Polling)

# Export
GET    /api/v1/export/csv                 # CSV-Export
GET    /api/v1/export/json                # JSON-Export
```

### 7.3 Webhook-Integration

```python
# Webhook-Konfiguration
{
    "name": "Windkraft-Updates",
    "url": "https://external-system.com/webhook",
    "events": ["new_document", "data_extracted", "change_detected"],
    "filter": {
        "category": "gemeinden",
        "min_confidence": 0.8
    },
    "auth": {
        "type": "bearer",
        "token": "xxx"
    }
}
```

---

## 8. Frontend (Admin-Dashboard)

### 8.1 Technologie

- **Framework:** Vue.js 3 mit Composition API
- **UI-Bibliothek:** Vuetify 3 (Material Design)
- **State Management:** Pinia
- **Charts:** Chart.js oder Apache ECharts

### 8.2 Hauptbereiche

```
┌─────────────────────────────────────────────────────────────────┐
│  SIDEBAR           │  MAIN CONTENT                              │
│  ─────────────     │  ─────────────────────────────────────────│
│  📊 Dashboard      │                                            │
│  📁 Kategorien     │  [Je nach Selektion]                      │
│  🌐 Datenquellen   │                                            │
│  🔄 Crawler-Status │                                            │
│  📄 Dokumente      │                                            │
│  📈 Ergebnisse     │                                            │
│  ⚙️ Einstellungen  │                                            │
│  📤 Export/API     │                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Dashboard-Widgets

1. **Übersichts-Karten:**
   - Gesamtzahl Kategorien / Quellen / Dokumente
   - Aktive Crawler
   - Neue Änderungen (24h)

2. **Crawler-Status-Chart:**
   - Echtzeit-Fortschritt aktiver Jobs
   - Erfolgs-/Fehlerrate

3. **Änderungs-Timeline:**
   - Chronologische Liste neuer Funde
   - Filterbar nach Kategorie

4. **Geografische Karte:**
   - Visualisierung der Gemeinden
   - Farbcodierung nach Status/Ergebnissen

---

## 9. Projektstruktur

```
CaeliCrawler/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI Application
│   │   ├── config.py               # Settings & Environment
│   │   ├── database.py             # SQLAlchemy Setup
│   │   │
│   │   ├── models/                 # SQLAlchemy Models
│   │   │   ├── __init__.py
│   │   │   ├── category.py
│   │   │   ├── data_source.py
│   │   │   ├── document.py
│   │   │   ├── crawl_job.py
│   │   │   └── extracted_data.py
│   │   │
│   │   ├── schemas/                # Pydantic Schemas
│   │   │   ├── __init__.py
│   │   │   ├── category.py
│   │   │   ├── data_source.py
│   │   │   └── ...
│   │   │
│   │   ├── api/                    # API Routes
│   │   │   ├── __init__.py
│   │   │   ├── admin/
│   │   │   │   ├── categories.py
│   │   │   │   ├── sources.py
│   │   │   │   └── crawler.py
│   │   │   └── v1/
│   │   │       ├── data.py
│   │   │       └── export.py
│   │   │
│   │   ├── services/               # Business Logic
│   │   │   ├── __init__.py
│   │   │   ├── crawler_service.py
│   │   │   ├── document_service.py
│   │   │   ├── ai_service.py
│   │   │   └── export_service.py
│   │   │
│   │   └── core/                   # Core Utilities
│   │       ├── __init__.py
│   │       ├── security.py
│   │       └── exceptions.py
│   │
│   ├── crawlers/                   # Crawler Implementations
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract Base Crawler
│   │   ├── oparl_crawler.py        # OParl API Crawler
│   │   ├── website_crawler.py      # Scrapy-based Crawler
│   │   └── rss_crawler.py          # RSS Feed Crawler
│   │
│   ├── workers/                    # Celery Tasks
│   │   ├── __init__.py
│   │   ├── celery_app.py           # Celery Configuration
│   │   ├── crawl_tasks.py          # Crawling Tasks
│   │   ├── processing_tasks.py     # Document Processing
│   │   └── ai_tasks.py             # AI Analysis Tasks
│   │
│   ├── processors/                 # Document Processors
│   │   ├── __init__.py
│   │   ├── pdf_processor.py
│   │   ├── html_processor.py
│   │   └── office_processor.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_api/
│   │   ├── test_crawlers/
│   │   └── test_processors/
│   │
│   ├── alembic/                    # Database Migrations
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/
│   │   ├── stores/                 # Pinia Stores
│   │   ├── components/
│   │   │   ├── dashboard/
│   │   │   ├── categories/
│   │   │   ├── sources/
│   │   │   └── common/
│   │   ├── views/
│   │   │   ├── DashboardView.vue
│   │   │   ├── CategoriesView.vue
│   │   │   ├── SourcesView.vue
│   │   │   ├── DocumentsView.vue
│   │   │   └── SettingsView.vue
│   │   ├── services/               # API Clients
│   │   └── types/
│   │
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── storage/                        # Document Storage
│   └── documents/
│
├── scripts/
│   ├── setup.sh                    # Installation Script
│   ├── start.sh                    # Start All Services
│   └── seed_data.py                # Initial Data Seeding
│
├── config/
│   ├── .env.example
│   └── supervisord.conf            # Process Management
│
└── README.md
```

---

## 10. Deployment (Managed Server)

### 10.1 Systemvoraussetzungen

```
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- Supervisor (Prozessmanagement)
- Nginx (Reverse Proxy)
```

### 10.2 Installation

```bash
#!/bin/bash
# scripts/setup.sh

# 1. Python Environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 2. Frontend Build
cd frontend
npm install
npm run build
cd ..

# 3. Database Setup
createdb caelichrawler
alembic upgrade head

# 4. Environment
cp config/.env.example .env
# → .env anpassen mit DB-Credentials, Azure Keys, etc.
```

### 10.3 Supervisor Konfiguration

```ini
; config/supervisord.conf

[program:caelichrawler-api]
command=/path/to/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
directory=/path/to/CaeliCrawler/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/caelichrawler/api.err.log
stdout_logfile=/var/log/caelichrawler/api.out.log

[program:caelichrawler-worker]
command=/path/to/venv/bin/celery -A workers.celery_app worker --loglevel=info --concurrency=4
directory=/path/to/CaeliCrawler/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/caelichrawler/worker.err.log
stdout_logfile=/var/log/caelichrawler/worker.out.log

[program:caelichrawler-beat]
command=/path/to/venv/bin/celery -A workers.celery_app beat --loglevel=info
directory=/path/to/CaeliCrawler/backend
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/caelichrawler/beat.err.log
stdout_logfile=/var/log/caelichrawler/beat.out.log
```

### 10.4 Nginx Konfiguration

```nginx
server {
    listen 443 ssl http2;
    server_name crawler.internal.example.com;

    ssl_certificate /etc/ssl/certs/crawler.crt;
    ssl_certificate_key /etc/ssl/private/crawler.key;

    # Frontend (Static Files)
    location / {
        root /path/to/CaeliCrawler/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API Proxy
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 11. Implementierungsreihenfolge

### Phase 1: Foundation (Kerninfrastruktur)

1. **Projektsetup**
   - Repository initialisieren
   - Backend-Struktur aufsetzen (FastAPI)
   - Datenbank-Schema implementieren (PostgreSQL + Alembic)
   - Redis-Anbindung für Celery

2. **Basis-Models & API**
   - SQLAlchemy Models
   - Pydantic Schemas
   - CRUD-Endpunkte für Kategorien & Datenquellen

3. **Celery Worker Setup**
   - Task Queue Konfiguration
   - Basis-Tasks definieren

### Phase 2: Crawler Core

4. **OParl-Crawler**
   - API-Client implementieren
   - Pagination & Rate Limiting
   - Dokument-Download

5. **Website-Crawler**
   - Scrapy Spider-Basis
   - Konfigurierbares Crawling
   - Playwright-Integration für JS-Seiten

6. **Document Processing**
   - PDF-Text-Extraktion
   - HTML-Parsing
   - Deduplizierung

### Phase 3: Intelligence

7. **Change Detection**
   - Hash-basierte Änderungserkennung
   - Scheduled Checks (Celery Beat)
   - ChangeLog-Persistierung

8. **KI-Integration**
   - Azure OpenAI Anbindung
   - Extraktions-Pipeline
   - Confidence Scoring

### Phase 4: Frontend & API

9. **Admin-Dashboard**
   - Vue.js Projekt aufsetzen
   - Dashboard-Übersicht
   - Kategorien-/Quellen-Management

10. **Output-API**
    - Öffentliche Daten-Endpunkte
    - Export-Funktionen (CSV, JSON)
    - Webhook-System

### Phase 5: Polish & Scale

11. **Skalierung**
    - Multi-Worker Setup
    - Queue-Priorisierung
    - Performance-Optimierung

12. **Monitoring & Logging**
    - Strukturiertes Logging
    - Metriken-Dashboard
    - Alerting bei Fehlern

---

## 12. Ressourcen & Dokumentation

### Offizielle Dokumentation

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Celery Docs](https://docs.celeryq.dev/)
- [Scrapy Docs](https://docs.scrapy.org/)
- [OParl Spezifikation](https://oparl.org/spezifikation/)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

### Verwandte Projekte

- [Politik bei uns (GitHub)](https://github.com/politik-bei-uns) - OParl-Aggregator
- [Azure PDF Extraction Sample](https://github.com/Azure-Samples/azure-openai-gpt-4-vision-pdf-extraction-sample)

### API-Quellen

| Quelle | Typ | URL |
|--------|-----|-----|
| OParl Standard | API | https://oparl.org/ |
| GovData | Portal | https://www.govdata.de/ |
| GENESIS | API | https://www-genesis.destatis.de/ |
| XPlanung24 | Plattform | https://xplanung24.de/ |

---

## Nächste Schritte

1. **Review & Feedback** zu diesem Plan
2. **Priorisierung** der Features für MVP
3. **Start mit Phase 1** - Projektsetup & Basis-Infrastruktur
