# CaeliCrawler Development Notes

## Aktuelle Arbeiten (2025-12-19)

### 1. DocumentsView Verbesserungen (FERTIG)

**Ziel:** Transparenz über Dokumentenverarbeitung

**Implementiert:**
- Statistik-Leiste mit Status-Counts (Wartend, Verarbeitung, Fertig, Gefiltert, Fehler)
- Klickbare Status-Chips zum Filtern
- "Alle Pending verarbeiten" Button
- Einzelne "Verarbeiten" und "Analysieren" Buttons pro Dokument
- Filter-Grund-Anzeige für gefilterte Dokumente
- Auto-Refresh während Verarbeitung
- **Location-Filter** (Autocomplete für Gemeinde/Ort)

**Dateien:**
- `frontend/src/views/DocumentsView.vue` - Komplett überarbeitet
- `frontend/src/services/api.ts` - Neue Methoden: `processDocument`, `analyzeDocument`, `processAllPending`, `getDocumentLocations`
- `backend/app/api/admin/crawler.py` - Neue Endpoints: `POST /documents/{id}/process`, `POST /documents/{id}/analyze`, `POST /documents/process-pending`
- `backend/app/api/v1/data.py` - Neuer Endpoint: `GET /documents/locations`, neuer Parameter `location_name` für Filter

### 2. Auto-Processing nach Crawl (FERTIG)

**Problem:** Dokumente blieben nach Crawl bis zu 5 Minuten in "Pending" (warteten auf Celery Beat).

**Lösung:** `crawl_source` Task triggert `process_pending_documents.delay()` sofort nach erfolgreichem Crawl.

**Datei:** `backend/workers/crawl_tasks.py` - Zeile 82-89

### 3. HTML Content Capturing (FERTIG)

**Problem:** Der Crawler speichert nur Links zu Dokumenten (PDFs, DOCs), aber nicht den HTML-Inhalt der Seiten selbst.

**Lösung:** Beim Crawlen werden HTML-Seiten auf Relevanz (Keywords) geprüft. Relevante Seiten werden als Dokument gespeichert.

**Workflow:**
1. Seite abrufen
2. Text extrahieren (ohne Scripts, Styles, Nav, Footer)
3. Keywords prüfen (via `services/relevance_checker.py`)
4. Bei Relevanz-Score >= 0.2: HTML als Dokument speichern
5. Document durchläuft normale Pipeline (KI-Analyse) - Text bereits extrahiert

**Neue Methoden in `crawlers/website_crawler.py`:**
- `_extract_html_text(soup)` - Bereinigter Text aus HTML
- `_get_page_title(soup)` - Titel aus <title> oder <h1>
- `_check_and_capture_html(url, html_content, soup, category)` - Relevanzprüfung & Capture

**Neue Instance-Variablen:**
- `html_documents: List[Dict]` - Erfasste HTML-Seiten
- `capture_html_content: bool` - Feature-Toggle (default: True)
- `html_min_relevance_score: float` - Mindest-Score (default: 0.2)

**Konfiguration via `crawl_config`:**
```json
{
  "capture_html_content": true,
  "html_min_relevance_score": 0.2
}
```

**HTML-Dokumente werden gespeichert mit:**
- `processing_status=COMPLETED` - Überspringt Download-Phase
- `raw_text` bereits extrahiert
- `file_path` zeigt auf gespeicherte HTML-Datei
- **KI-Analyse wird sofort getriggert** via `analyze_document.delay(doc.id, skip_relevance_check=True)`

**Kompletter Flow:**
```
Crawl → HTML abrufen → Text extrahieren → Relevanz-Check (Keywords)
  ↓ (wenn Score >= 0.2)
Document erstellen → HTML-Datei speichern → analyze_document.delay()
  ↓
Azure OpenAI API → ExtractedData mit Erkenntnissen
```

### 4. Bug-Fix: Null-Bytes in PDFs (FERTIG)

**Problem:** Manche PDFs enthalten Null-Bytes (`\x00`), die PostgreSQL nicht akzeptiert.

**Lösung:** `text.replace('\x00', '')` in `workers/processing_tasks.py` Zeile 49-51

### 5. Stop/Cancel Button für Processing (FERTIG)

**Problem:** Keine Möglichkeit laufende Verarbeitung zu stoppen.

**Lösung:**
- Backend Endpoint: `POST /admin/crawler/documents/stop-all`
- Frontend Button: "Verarbeitung stoppen" (erscheint wenn processing > 0)

**Funktionsweise:**
1. `celery_app.control.purge()` - Löscht alle wartenden Tasks aus Queue
2. Setzt alle Dokumente mit `PROCESSING` Status zurück auf `PENDING`

**Dateien:**
- `backend/app/api/admin/crawler.py` - Zeile 623-654: `stop_all_processing` Endpoint
- `frontend/src/services/api.ts` - `stopAllProcessing()` Methode
- `frontend/src/views/DocumentsView.vue` - Stop-Button + Handler

---

## Wichtige Dateien

| Datei | Beschreibung |
|-------|--------------|
| `backend/workers/crawl_tasks.py` | Celery Tasks für Crawling |
| `backend/workers/processing_tasks.py` | Celery Tasks für Dokumentenverarbeitung |
| `backend/workers/ai_tasks.py` | Celery Tasks für KI-Analyse |
| `backend/crawlers/website_crawler.py` | Website Crawler |
| `backend/services/relevance_checker.py` | Keyword-basierte Relevanzprüfung |
| `backend/app/models/document.py` | Document Model |
| `frontend/src/views/DocumentsView.vue` | Dokumenten-Übersicht |

---

## Crawl-Prozess Flow

```
1. crawl_source (crawl_tasks.py)
   ├── WebsiteCrawler.crawl()
   │   ├── Seiten besuchen
   │   ├── Links finden
   │   ├── Dokument-URLs sammeln (PDFs, DOCs)
   │   ├── [NEU] HTML-Seiten auf Relevanz prüfen & capturen
   │   └── Documents in DB erstellen (status=PENDING)
   └── process_pending_documents.delay() [NEU: sofort nach Crawl]

2. process_pending_documents (processing_tasks.py)
   └── process_document() für jedes PENDING Document
       ├── Download Datei
       ├── Text extrahieren (PDF, HTML, DOCX)
       ├── Null-Bytes entfernen
       ├── Status → COMPLETED
       └── analyze_document.delay()

3. analyze_document (ai_tasks.py)
   ├── Relevanz-Check (Keywords)
   │   ├── Nicht relevant → FILTERED
   │   └── Relevant → weiter
   ├── Azure OpenAI API Call
   └── ExtractedData erstellen
```

---

## Datenmodell-Hinweise

- `DataSource.location_name` - String für Gemeinde/Ort
- `DataSource.location_id` - FK zu `locations` Tabelle
- `Document.processing_status` - Enum: PENDING, PROCESSING, ANALYZING, COMPLETED, FILTERED, FAILED
- `Document.processing_error` - Fehler/Filter-Grund
- `Document.discovered_at` - Zeitstempel (für Duplikat-Vermeidung)
- `Document.file_hash` - Hash der URL (für Duplikat-Erkennung)
- `Document.content_hash` - Hash des Inhalts (für Änderungserkennung)

---

## Filter-Verbesserungen (2025-12-19)

### Behobene Probleme

1. **SourcesView Location-Filter**: War case-sensitive, jetzt case-insensitive mit `func.lower()`
2. **MunicipalitiesView Confidence-Filter**: Client-seitiger Filter brach Pagination - entfernt, Server-seitig via `overviewReport`
3. **ResultsView**: Location/Country-Filter hinzugefügt
4. **ExportView**: Location/Country-Filter hinzugefügt

### Neue API-Endpoints

- `GET /v1/data/locations` - Locations mit extrahierten Daten
- `GET /v1/data/countries` - Länder mit extrahierten Daten
- `GET /v1/data` - Erweitert um `location_name` und `country` Parameter

### Filter-Übersicht pro Seite

| Seite | Filter |
|-------|--------|
| SourcesView | Country, Location, Category, Status, Search |
| DocumentsView | Search, Location, Category, Status, Type |
| ResultsView | Country, Location, Category, Confidence |
| MunicipalitiesView | Country, AdminLevel1/2, Category, Confidence, Search |
| ExportView | Country, Location, Category, Confidence, Verified |
| CrawlerView | Status (Toggle) |
| DashboardView | Crawler-Dialog: Category, Country, Search, Limit, Status, SourceType |

---

## Nächste Schritte

1. Bessere Duplikat-Erkennung (basierend auf content_hash + Zeitstempel)
2. Conditional Requests (HTTP 304) für effizienteres Re-Crawling
