# CaeliCrawler - Sales Intelligence Platform

## Übersicht

CaeliCrawler ist eine interne Datenplattform zur Überwachung kommunaler Veröffentlichungen im Bereich Windenergie. Ziel ist die Identifikation von **Pain Points** und **positiven Signalen** für personalisierte Vertriebsansprachen.

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue.js)                         │
│                     localhost:5173                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│                     localhost:8000                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Admin API    │  │ Data API     │  │ Export API           │   │
│  │ /api/admin/* │  │ /api/v1/*    │  │ /api/v1/export/*     │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     Celery Workers                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Crawl Tasks  │  │ Processing   │  │ AI Tasks             │   │
│  │ - API Crawl  │  │ - Download   │  │ - Analyse            │   │
│  │ - Website    │  │ - Text Extr. │  │ - Embeddings         │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     Datenbank & Storage                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ PostgreSQL   │  │ Redis        │  │ File Storage         │   │
│  │ - Categories │  │ - Celery     │  │ - PDFs               │   │
│  │ - Documents  │  │ - Cache      │  │ - HTML               │   │
│  │ - Extracted  │  │              │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Datenquellen

### 1. OParl API (Ratsinformationen)
- **Zweck**: Kommunale Ratsbeschlüsse, Tagesordnungen, Vorlagen
- **Beispiel**: Stadt Münster, Kreis Steinfurt
- **Datentyp**: JSON (strukturiert)
- **Relevanz**: Flächennutzungspläne, Windenergie-Beschlüsse

### 2. GovData.de (Open Data)
- **Zweck**: Offene Verwaltungsdaten
- **API**: CKAN REST API
- **Datentyp**: Datasets mit Ressourcen (PDF, CSV, JSON, Geodaten)
- **Relevanz**: Potenzialflächen, Schutzgebiete, Statistiken

### 3. DIP Bundestag (Parlamentsdokumente)
- **Zweck**: Drucksachen, Kleine Anfragen, Gesetzentwürfe
- **API**: DIP REST API (mit API-Key)
- **Datentyp**: JSON + PDF-Downloads
- **Relevanz**: Regulierung, politische Positionen, Statistiken

### 4. FragDenStaat (IFG-Anfragen)
- **Zweck**: Informationsfreiheits-Anfragen an Behörden
- **API**: FragDenStaat REST API
- **Datentyp**: JSON + Anhänge (PDFs)
- **Relevanz**: Behördliche Einblicke, Genehmigungsverfahren

## Crawling-Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   1. CRAWL   │───▶│  2. DOWNLOAD │───▶│  3. EXTRACT  │───▶│ 4. ANALYZE   │
│              │    │              │    │              │    │              │
│ API-Abfrage  │    │ PDF/HTML     │    │ Text aus     │    │ KI-Analyse   │
│ mit Keywords │    │ herunterladen│    │ Dokumenten   │    │ Pain Points  │
│              │    │              │    │              │    │ Signale      │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     │                    │                   │                   │
     ▼                    ▼                   ▼                   ▼
 documents           file_path            raw_text           extracted_data
 (PENDING)           file_size            (COMPLETED)        (AI output)
```

### Status-Flow
1. **PENDING**: Dokument gefunden, wartet auf Download
2. **DOWNLOADING**: Datei wird heruntergeladen
3. **PROCESSING**: Text wird extrahiert
4. **ANALYZING**: KI analysiert den Text
5. **COMPLETED**: Fertig verarbeitet
6. **FAILED**: Fehler aufgetreten

## KI-Integration (Azure OpenAI)

### Deployments
| Task | Deployment | Modell |
|------|------------|--------|
| Chat/Standard | gpt-4.1-mini | GPT-4.1 Mini |
| Embeddings | text-embedding-3-large | 3072 Dimensionen |
| PDF-Extraktion | (konfigurierbar) | - |
| Classification | (konfigurierbar) | - |

### Analyse-Prompts (pro Kategorie)

Jede Kategorie hat einen spezifischen `ai_extraction_prompt` der folgendes extrahiert:

```json
{
  "is_relevant": true,
  "municipality": "Name der Kommune",

  "pain_points": [
    {
      "type": "Bürgerprotest|Naturschutz|Kosten|...",
      "description": "Konkrete Beschreibung",
      "severity": "hoch|mittel|niedrig",
      "quote": "Originalzitat"
    }
  ],

  "positive_signals": [
    {
      "type": "Interesse|Planung|Genehmigung|...",
      "description": "Beschreibung",
      "quote": "Originalzitat"
    }
  ],

  "decision_makers": [
    {
      "name": "Name",
      "role": "Bürgermeister|Ratsmitglied|...",
      "stance": "positiv|neutral|negativ"
    }
  ],

  "outreach_recommendation": {
    "priority": "hoch|mittel|niedrig",
    "approach": "Empfohlene Strategie",
    "key_message": "Kernbotschaft",
    "contact_timing": "Optimaler Zeitpunkt"
  },

  "lead_score": {
    "total": 0-100,
    "interest_level": 0-100,
    "urgency": 0-100
  }
}
```

## Content-Typen

Das System monitort **verschiedene Content-Typen**, nicht nur PDFs:

| Typ | Quelle | Beispiel |
|-----|--------|----------|
| **PDF** | DIP Bundestag, Ratsinformationen | Drucksachen, Beschlüsse |
| **HTML/News** | Gemeinde-Websites | "Aktuelles", Pressemitteilungen |
| **Strukturierte Daten** | GovData, FragDenStaat | Datasets, IFG-Anfragen |
| **RSS/Atom** | News-Feeds | Automatische Updates |

### Website-Monitoring Strategie

```
┌─────────────────────────────────────────────────────────────────┐
│                    Gemeinde-Website                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Aktuelles│  │ Presse   │  │ Rat &    │  │ Bauleitplanung   │ │
│  │ /news    │  │ /presse  │  │ Politik  │  │ /bauen           │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
└───────┼─────────────┼─────────────┼─────────────────┼───────────┘
        │             │             │                 │
        ▼             ▼             ▼                 ▼
   ┌────────────────────────────────────────────────────────────┐
   │                      CaeliCrawler                          │
   │  1. RSS-Feed checken (wenn vorhanden)                      │
   │  2. HTML-Seite laden                                       │
   │  3. Relevante Abschnitte extrahieren                       │
   │  4. Keywords prüfen (Windenergie, Windkraft, etc.)         │
   │  5. Bei Treffer: Vollständige Analyse mit KI               │
   └────────────────────────────────────────────────────────────┘
```

### Zwei-Phasen Analyse

**Phase 1: Schnelle Relevanz-Prüfung**
- Keyword-Matching auf Titel/Teaser
- Kein AI-Aufruf nötig
- Schnell, kostengünstig

**Phase 2: Tiefe KI-Analyse (nur bei Relevanz)**
- Volltext-Extraktion
- AI-Analyse für Pain Points, Signale
- Lead-Scoring

## Geplante Erweiterungen

### 1. Mehrstufige KI-Suche (TODO)

```
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│ 1. Keyword     │───▶│ 2. Wenig       │───▶│ 3. KI-basierte │
│    Suche       │    │    Ergebnisse? │    │    Erweiterung │
│                │    │                │    │                │
│ "Windenergie"  │    │ < 10 Treffer   │    │ Synonyme,      │
│ "Windkraft"    │    │                │    │ verwandte      │
│                │    │                │    │ Begriffe       │
└────────────────┘    └────────────────┘    └────────────────┘
```

**Implementierung:**
1. Keywords aus Kategorie-Konfiguration
2. Wenn < N Ergebnisse: KI-Prompt zur Keyword-Erweiterung
3. Erneute Suche mit erweiterten Keywords
4. Optional: Semantische Suche via Embeddings

### 2. Website-Crawling mit KI

- RSS-Feeds von Gemeinde-Websites
- HTML-Extraktion relevanter Inhalte
- KI zur Relevanz-Bewertung vor vollem Download

### 3. PDF-Download für alle APIs

**Problem:** Manche APIs liefern nur Metadaten, keine direkten PDF-URLs

**Lösung:**
- DIP Bundestag: PDF-URL aus `fundstelle` extrahieren
- FragDenStaat: Attachments durchsuchen
- GovData: Ressourcen mit Format "PDF" bevorzugen

## Datenmodell

### Categories
```sql
- id: UUID
- name: "Ratsinformationen NRW"
- slug: "ratsinformationen-nrw"
- purpose: "Beschreibung des Zwecks"
- search_terms: ["Windkraft", "Windenergie", ...]
- ai_extraction_prompt: "Analysiere..."
- schedule_cron: "0 6 * * *"
```

### DataSources
```sql
- id: UUID
- category_id: FK
- name: "Stadt Münster - Ratsinformation"
- source_type: OPARL_API | CUSTOM_API | RSS | WEBSITE
- base_url: "https://..."
- crawl_config: { "api_type": "govdata", "search_query": "..." }
```

### Documents
```sql
- id: UUID
- source_id: FK
- title: "Beschluss zur Windkraft"
- original_url: "https://..."
- document_type: "PDF" | "HTML" | "Dataset"
- file_path: "/storage/documents/..."
- raw_text: "Extrahierter Text..."
- processing_status: PENDING | COMPLETED | FAILED
```

### ExtractedData
```sql
- id: UUID
- document_id: FK
- extraction_type: "pain_points" | "signals" | "lead_score"
- data: { ... JSON ... }
- confidence: 0.85
- model_used: "gpt-4.1-mini"
```

## API-Endpunkte

### Admin API
- `POST /api/admin/crawler/start` - Crawl starten
- `GET /api/admin/crawler/jobs` - Jobs anzeigen
- `GET /api/admin/categories` - Kategorien verwalten
- `GET /api/admin/sources` - Quellen verwalten

### Data API
- `GET /api/v1/data/documents` - Dokumente abrufen
- `GET /api/v1/data/search` - Volltextsuche
- `GET /api/v1/data/stats` - Statistiken

### Export API
- `GET /api/v1/export/csv` - CSV-Export
- `GET /api/v1/export/json` - JSON-Export

## Change Detection

Um unnötige Crawls zu vermeiden, implementiert das System mehrere Change-Detection-Mechanismen:

### 1. Dokument-Level (file_hash)

```sql
-- Dokumente werden über hash eindeutig identifiziert
UNIQUE (source_id, file_hash)

-- Hash wird berechnet aus:
hash = sha256(f"{source_id}:{url}")
```

- **Vorteil**: Exakte Duplikat-Erkennung
- **Nachteil**: Erkennt keine inhaltlichen Änderungen bei gleicher URL

### 2. Quellen-Level (DataSource)

```sql
-- DataSource Felder für Change Detection
content_hash: VARCHAR(64)        -- Hash des letzten Inhalts
last_change_detected: TIMESTAMP  -- Wann wurde Änderung erkannt
last_crawl: TIMESTAMP            -- Letzter Crawl-Zeitpunkt
```

**Ablauf:**
1. `detect_changes` Task führt HEAD-Request durch
2. Prüft `ETag`, `Last-Modified`, `Content-Length` Header
3. Bei Änderung: `last_change_detected` setzen, Crawl triggern
4. Bei keiner Änderung: Crawl überspringen

### 3. Website-Content-Hash

Für HTML-Seiten:
```python
# Hash des relevanten Inhalts (ohne Navigation, Footer, etc.)
relevant_content = extract_main_content(html)
content_hash = sha256(relevant_content)
```

### 4. API-basierte Change Detection

Manche APIs bieten eigene Mechanismen:

| API | Mechanismus |
|-----|-------------|
| OParl | `modified` Timestamp auf Objekten |
| GovData | `metadata_modified` in CKAN |
| DIP | `aktualisiert` Feld |
| FragDenStaat | `last_message` Timestamp |

### Implementierung (geplant)

```python
async def should_crawl(source: DataSource) -> bool:
    """Entscheide ob Quelle gecrawlt werden soll."""

    # 1. Nie gecrawlt → Crawlen
    if not source.last_crawl:
        return True

    # 2. Schedule-basiert (Cron)
    if is_due_for_scheduled_crawl(source):
        # 2a. Schnelle Change Detection
        if await detect_remote_changes(source):
            return True
        # 2b. Keine Änderung erkannt
        return False

    return False

async def detect_remote_changes(source: DataSource) -> bool:
    """Prüfe auf Änderungen ohne vollen Crawl."""

    if source.source_type == SourceType.WEBSITE:
        # HEAD Request, ETag/Last-Modified prüfen
        headers = await fetch_headers(source.base_url)
        new_hash = compute_header_hash(headers)
        return new_hash != source.content_hash

    elif source.source_type == SourceType.RSS:
        # RSS Feed laden, auf neue Items prüfen
        feed = await fetch_rss(source.api_endpoint)
        latest_date = get_latest_item_date(feed)
        return latest_date > source.last_crawl

    elif source.source_type == SourceType.CUSTOM_API:
        # API-spezifische Logik
        return await check_api_updates(source)

    return True  # Im Zweifel crawlen
```

## Konfiguration

### Umgebungsvariablen
```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-3-large

# Database
DATABASE_URL=postgresql+asyncpg://...

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
```

## Entwicklung

### Lokaler Start
```bash
docker-compose up -d
```

### Services
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Logs
```bash
docker-compose logs -f celery-worker
docker-compose logs -f backend
```
