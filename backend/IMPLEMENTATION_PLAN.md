# Implementation Plan: API-Import mit Tags + Tag-basierte Kategorie-Zuordnung

**Erstellt:** 2025-12-21
**Status:** In Planung

---

## Übersicht

Vereinfachte DataSource-Verwaltung durch:
1. Generischer API-Import Dialog mit KI-Analyse
2. Tag-basierte Kategorie-Zuordnung
3. Neuimport statt Rückwärts-Tagging

---

## Phase 0: Sofort-Fixes

- [ ] Fehler in DataSource-Liste beheben (Migration prüfen)
- [ ] Bulk-Tags Code entfernen (nicht benötigt)
- [ ] Tag-Filter Parameter in Sources-Liste hinzufügen

---

## Phase 1: API-Import (Kern-Feature)

- [ ] Backend: API-Import Endpoints (`backend/app/api/admin/api_import.py`)
  - [ ] `/preview` - API aufrufen, Vorschau generieren
  - [ ] `/execute` - Import durchführen
- [ ] Backend: KI-Analyzer für API-Responses (`backend/services/api_import/ai_analyzer.py`)
- [ ] Backend: Vorgefertigte Templates (`backend/services/api_import/templates.py`)
  - [ ] Wikidata - DE Gemeinden (pro Bundesland)
  - [ ] Wikidata - AT Gemeinden
  - [ ] Wikidata - UK Local Authorities
  - [ ] OParl - System-Liste
- [ ] Frontend: ApiImportDialog.vue
- [ ] Test: Wikidata-Import für NRW Gemeinden

---

## Phase 2: Kategorie-Zuordnung

- [ ] Backend: Tag-basierte Source-Suche (UND/ODER Logik)
- [ ] Backend: Bulk-Zuordnung Endpoint (`/categories/{id}/assign-sources-by-tags`)
- [ ] Frontend: DataSources-Tab in Kategorie-Dialog
- [ ] Test: Tag-basierte Zuordnung

---

## Phase 3: Smart Query Integration

- [ ] Assistant-Prompt anpassen (Tags für DataSource-Filterung erklären)
- [ ] AI-Generierung: Tags vorschlagen beim Kategorie-Setup
- [ ] Write Mode: Tags für Source-Matching nutzen (bereits teilweise implementiert)
- [ ] Test: Smart Query mit Tags

---

## Phase 4: Dokumentation

- [ ] User-Hilfe: DataSource Tags Sektion
- [ ] API-Dokumentation: Neue Endpoints
- [ ] iOS Migrations-Hinweise aktualisieren (`IOS_API_UPDATE_TODOS.md`)

---

## Phase 5: Cleanup & Neuimport

- [ ] Alle bestehenden DataSources löschen
- [ ] **DE Gemeinden** via Wikidata importieren
  - [ ] NRW (Tags: de, nrw, kommunal)
  - [ ] Bayern (Tags: de, bayern, kommunal)
  - [ ] Baden-Württemberg (Tags: de, bw, kommunal)
  - [ ] Weitere Bundesländer...
- [ ] **AT Gemeinden** via Wikidata importieren (Tags: at, kommunal)
- [ ] **UK Councils** via Wikidata importieren (Tags: uk, council)
- [ ] **OParl Bodies** via OParl API importieren (Tags: de, oparl, ratsinformation)
- [ ] Kategorien via Tags zuordnen:
  - [ ] "NRW Kommunen" ← Tags: nrw, kommunal
  - [ ] "Bayern Kommunen" ← Tags: bayern, kommunal
  - [ ] "OParl Ratsinformationen" ← Tags: oparl
- [ ] End-to-End Test

---

## Betroffene Dateien

### Backend (Neu)
- `backend/app/api/admin/api_import.py`
- `backend/services/api_import/ai_analyzer.py`
- `backend/services/api_import/templates.py`

### Backend (Anpassen)
- `backend/app/api/admin/sources.py`
- `backend/app/api/admin/categories.py`
- `backend/services/smart_query/assistant.py`
- `backend/services/smart_query/ai_generation.py`

### Frontend (Neu)
- `frontend/src/components/sources/ApiImportDialog.vue`

### Frontend (Anpassen)
- `frontend/src/views/SourcesView.vue`
- `frontend/src/views/CategoriesView.vue`
- `frontend/src/services/api.ts`
- `frontend/src/locales/*/help/*.json`

### Dokumentation
- `IOS_API_UPDATE_TODOS.md`
- `frontend/src/locales/*/help/apiDocs.json`

---

## Wikidata Templates

### DE Gemeinden (pro Bundesland)
```sparql
SELECT ?item ?itemLabel ?website WHERE {
  ?item wdt:P31 wd:Q262166 .      # ist Gemeinde in DE
  ?item wdt:P131* wd:Q1198 .      # liegt in NRW (änderbar)
  OPTIONAL { ?item wdt:P856 ?website }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de" }
}
```

### AT Gemeinden
```sparql
SELECT ?item ?itemLabel ?website WHERE {
  ?item wdt:P31 wd:Q667509 .      # ist Gemeinde in AT
  OPTIONAL { ?item wdt:P856 ?website }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de" }
}
```

### UK Local Authorities
```sparql
SELECT ?item ?itemLabel ?website WHERE {
  ?item wdt:P31/wdt:P279* wd:Q6501447 .  # local authority in UK
  OPTIONAL { ?item wdt:P856 ?website }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
```

---

## Notizen

- Tag-Filter unterstützt UND/ODER Logik (user-wählbar)
- API-Import speichert Konfiguration in ExternalAPIConfig für späteren Re-Import
- Smart Query nutzt bereits 3-Strategie-Matching (Kategorie, Tags, Keywords)
