# CaeliCrawler - TODO & Roadmap

## Aktueller Stand (2025-12-18)

### Fertig
- [x] FastAPI Backend mit Admin & Data APIs
- [x] Vue.js Frontend Dashboard
- [x] Docker-Compose Setup (PostgreSQL, Redis, Celery)
- [x] Azure OpenAI Integration (Chat + Embeddings)
- [x] API Clients für GovData, DIP Bundestag, FragDenStaat, OParl
- [x] Sales Intelligence Kategorien mit AI-Prompts
- [x] API-Crawler für CUSTOM_API Quellen
- [x] Celery Task-Pipeline (Crawl → Process → Analyze)
- [x] **PDF-Download für DIP Bundestag Drucksachen** (2025-12-18)
- [x] **Text-Extraktion Pipeline (PDF, HTML, DOCX)** (2025-12-18)
- [x] **Event-Loop Problem behoben (nest_asyncio)** (2025-12-18)
- [x] **Dedizierte Celery DB-Session Factory** (2025-12-18)
- [x] **AI-Analyse Pipeline funktioniert** (2025-12-18)

### In Arbeit
- [ ] Frontend "Betrachten" Button für Dokumente
- [ ] Mehrstufige KI-Suche

## Offene Punkte

### 1. FragDenStaat PDF-Attachments (Priorität: Mittel)

**Problem:** FragDenStaat Attachments werden noch nicht als separate Downloads behandelt.

**Aktuell:**
```python
# FOIRequest hat attachments[]
req.attachments = [
    {"file_url": "https://fragdenstaat.de/files/...", "filetype": "pdf"}
]
# Diese werden in der API-Response als "content" zurückgegeben
```

**Geplante Lösung:**
1. Erstes PDF-Attachment als `file_url` setzen
2. Oder: Alle Attachments als separate Dokumente speichern

### 2. Mehrstufige KI-Suche (Priorität: Mittel)

**Konzept:**
```python
async def smart_search(category, base_keywords):
    # Stufe 1: Direkte Keyword-Suche
    results = await api_search(base_keywords)

    if len(results) < MIN_RESULTS:
        # Stufe 2: KI-basierte Keyword-Erweiterung
        expanded = await ai_expand_keywords(base_keywords, category.context)
        results += await api_search(expanded)

    if len(results) < MIN_RESULTS:
        # Stufe 3: Semantische Suche
        query_embedding = await get_embedding(category.purpose)
        results += await vector_search(query_embedding)

    return results
```

**AI Prompt für Keyword-Erweiterung:**
```
Gegeben diese Suchbegriffe: {keywords}
Und diesen Kontext: {category.purpose}

Generiere 10 zusätzliche relevante Suchbegriffe.
Berücksichtige:
- Synonyme
- Verwandte Fachbegriffe
- Regionale Varianten
- Abkürzungen
```

### 3. Website-Crawling (Priorität: Mittel)

**Aktuell:**
- RSS-Feeds werden als CUSTOM_API behandelt
- Kein echtes HTML-Crawling

**Geplant:**
1. RSS-Feed Parsing für News
2. HTML-Extraktion für Gemeindewebsites
3. KI-Filterung für Relevanz

### 4. Frontend Verbesserungen (Priorität: Niedrig)

- [ ] "Betrachten" Button: PDF-Viewer/Download
- [ ] Dokument-Detail-Ansicht mit extrahierten Daten
- [ ] Lead-Scoring Dashboard
- [ ] Export-Funktionen

## Gelöste Technische Schulden

### Event-Loop Problem in Celery (GELÖST 2025-12-18)

**Problem:**
```
RuntimeError: Task got Future attached to a different loop
```

**Lösung implementiert:**
1. `nest_asyncio>=1.6.0` zu requirements.txt hinzugefügt
2. In `celery_app.py`: `nest_asyncio.apply()` beim Import
3. Worker-Init-Signal: Re-apply in jedem Worker-Prozess
4. Dedizierte `get_celery_session_context()` für Celery-Tasks
5. Separate Engine-Instanz pro Worker-Prozess

```python
# celery_app.py
import nest_asyncio
nest_asyncio.apply()

@worker_process_init.connect
def configure_worker(**kwargs):
    nest_asyncio.apply()
    reset_celery_engine()

# database.py
@asynccontextmanager
async def get_celery_session_context():
    factory = get_celery_session_factory()  # Lazy init per worker
    async with factory() as session:
        yield session
```

## Nächste Schritte

1. **Kurzfristig:**
   - [ ] Frontend Document-Viewer implementieren
   - [ ] Mehrstufige Suche implementieren

2. **Mittelfristig:**
   - [ ] Website-Crawling für Gemeinde-News
   - [ ] Embeddings-basierte semantische Suche
   - [ ] Lead-Scoring Dashboard

3. **Langfristig:**
   - [ ] OParl API vollständig integrieren
   - [ ] Automatische Benachrichtigungen bei neuen relevanten Dokumenten
   - [ ] CRM-Integration
