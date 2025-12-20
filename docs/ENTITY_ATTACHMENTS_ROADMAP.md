# Entity Attachments mit KI-Analyse - Roadmap

## Projektbeschreibung

Feature zum direkten Hochladen von Dateien (Bilder, PDFs) zu Entities mit persistenter Speicherung und KI-Analyse. Die Analyse-Ergebnisse koennen als Facet-Vorschlaege in das Enrichment-System integriert werden.

---

## Meilenstein 1: Backend Models & Migration

### Aufgaben
- [x] EntityAttachment Model erstellen (`backend/app/models/entity_attachment.py`)
- [x] Entity Model erweitern - attachments Relationship
- [x] FacetValue Model erweitern - ATTACHMENT source type + source_attachment_id
- [x] AITask Model erweitern - ATTACHMENT_ANALYSIS task type
- [x] Models in `__init__.py` exportieren
- [x] Config erweitern - Storage Path + Vision Deployment
- [x] Alembic Migration erstellen

### Kritische Dateien
- `backend/app/models/entity_attachment.py` (NEU)
- `backend/app/models/entity.py`
- `backend/app/models/facet_value.py`
- `backend/app/models/ai_task.py`
- `backend/app/models/__init__.py`
- `backend/app/config.py`
- `backend/alembic/versions/xxx_add_entity_attachments.py` (NEU)

---

## Meilenstein 2: AttachmentService (Upload/Storage)

### Aufgaben
- [x] AttachmentService erstellen
- [x] `upload_attachment()` - Validierung, Hash, Speichern
- [x] `get_attachments()` - Liste fuer Entity
- [x] `get_attachment()` - Einzelnes Attachment
- [x] `delete_attachment()` - Datei + DB loeschen
- [x] `get_file_content()` - Datei lesen
- [x] Thumbnail-Generierung fuer Bilder

### Kritische Dateien
- `backend/services/attachment_service.py` (NEU)

---

## Meilenstein 3: API Endpoints

### Aufgaben
- [x] Attachment Router erstellen
- [x] POST `/entities/{id}/attachments` - Upload
- [x] GET `/entities/{id}/attachments` - Liste
- [x] GET `/entities/{id}/attachments/{att_id}` - Metadata
- [x] GET `/entities/{id}/attachments/{att_id}/download` - Datei
- [x] GET `/entities/{id}/attachments/{att_id}/thumbnail` - Thumbnail
- [x] DELETE `/entities/{id}/attachments/{att_id}` - Loeschen
- [x] POST `/entities/{id}/attachments/{att_id}/analyze` - Analyse starten
- [x] Router in main.py registrieren

### Kritische Dateien
- `backend/app/api/v1/attachments.py` (NEU)
- `backend/app/main.py`

---

## Meilenstein 4: Frontend - Basis Tab

### Aufgaben
- [x] API Service erweitern - attachmentApi
- [x] EntityAttachmentsTab Komponente erstellen
- [x] Drag & Drop Upload Zone
- [x] Attachment-Liste mit Thumbnails/Icons
- [x] Download/Loeschen Aktionen
- [x] Tab in EntityDetailView integrieren
- [x] Localization (DE/EN)
- [x] API Dokumentation aktualisieren

### Kritische Dateien
- `frontend/src/services/api.ts`
- `frontend/src/components/entity/EntityAttachmentsTab.vue` (NEU)
- `frontend/src/views/EntityDetailView.vue`
- `frontend/src/locales/de/entities.json`
- `frontend/src/locales/en/entities.json`
- `docs/API_REFERENCE.md`

---

## Meilenstein 5: KI-Analyse Service + Celery

### Aufgaben
- [x] AttachmentAnalysisService erstellen
- [x] `analyze_attachment()` - AITask + Celery trigger
- [x] `analyze_image()` - Vision API Integration (base64 encoding + Vision API)
- [x] `analyze_pdf()` - Text-Extraktion (pymupdf) + AI
- [x] `extract_facet_suggestions()` - Mapping auf FacetTypes
- [x] Celery Task `analyze_attachment_task` implementieren

### Kritische Dateien
- `backend/services/attachment_analysis_service.py` (NEU)
- `backend/workers/ai_tasks.py`

---

## Meilenstein 6: Frontend - Analyse Integration

### Aufgaben
- [x] Analyse-Button pro Attachment (PENDING/FAILED Status)
- [x] Status-Anzeige (PENDING/ANALYZING/COMPLETED/FAILED) mit Spinner
- [x] Analyse-Ergebnis Dialog mit erkannten Entitaeten
- [x] Facet-Vorschlaege mit Checkbox-Auswahl
- [x] "Facets uebernehmen" Funktion mit Backend-Endpoint
- [x] Polling fuer ANALYZING Status
- [x] Snackbar-Feedback fuer alle Aktionen

### Kritische Dateien
- `frontend/src/components/entity/EntityAttachmentsTab.vue`
- `frontend/src/services/api.ts` - applyFacets Methode
- `backend/app/api/v1/attachments.py` - apply-facets Endpoint

---

## Meilenstein 7: Enrichment Integration

### Aufgaben
- [x] `_collect_attachments()` in EntityDataFacetService
- [x] `get_enrichment_sources()` um "attachments" erweitern
- [x] `collect_entity_data()` um attachments erweitern
- [x] valid_sources um "attachments" erweitern
- [x] Enrichment-Dropdown - Checkbox fuer Attachments im Frontend
- [x] TypeScript-Typen aktualisieren
- [x] hasAnyEnrichmentSource computed erweitern

### Kritische Dateien
- `backend/services/entity_data_facet_service.py`
- `frontend/src/views/EntityDetailView.vue`

---

## Meilenstein 8: AI Assistant Integration

### Aufgaben
- [x] Backend: Neuer Endpoint `/v1/assistant/save-to-entity-attachments`
- [x] Backend: SuggestedAction "Als Attachment speichern" in `_handle_image_analysis()`
- [x] Frontend: API Funktion `saveToEntityAttachments`
- [x] Frontend: Handler fuer `save_attachment` Action in `useAssistant.ts`
- [x] Localization (DE/EN)

### Kritische Dateien
- `backend/app/api/v1/assistant.py` - Neuer Endpoint
- `backend/services/assistant_service.py` - SuggestedAction erweitert
- `frontend/src/services/api.ts` - API Funktion
- `frontend/src/composables/useAssistant.ts` - Action Handler
- `frontend/src/locales/*/assistant.json` - Uebersetzungen

---

## Meilenstein 9: API-Dokumentation Refactoring

### Aufgaben
- [x] Neue API-Dokumentationsstruktur erstellen (`docs/api/`)
- [x] README.md mit Index und Uebersicht erstellen
- [x] AUTH.md - Authentifizierung dokumentieren
- [x] ATTACHMENTS.md - Entity Attachments inkl. apply-facets Endpoint
- [x] ASSISTANT.md - KI-Assistant inkl. save-to-entity-attachments Endpoint
- [ ] Weitere Dateien nach Bedarf erstellen (ADMIN, ENTITIES, etc.)

### Erstellte Dateien
- `docs/api/README.md` - Uebersicht, Index, allgemeine Konventionen
- `docs/api/AUTH.md` - Authentifizierung & Benutzerverwaltung
- `docs/api/ATTACHMENTS.md` - Entity Attachments mit KI-Analyse (inkl. apply-facets)
- `docs/api/ASSISTANT.md` - KI-Assistant (inkl. save-to-entity-attachments)

### Kritische Dateien
- `docs/api/README.md` (NEU)
- `docs/api/AUTH.md` (NEU)
- `docs/api/ATTACHMENTS.md` (NEU)
- `docs/api/ASSISTANT.md` (NEU)

---

## Fortschritt

| Meilenstein | Status | Abgeschlossen |
|-------------|--------|---------------|
| 1. Backend Models & Migration | DONE | 2024-12-20 |
| 2. AttachmentService | DONE | 2024-12-20 |
| 3. API Endpoints | DONE | 2024-12-20 |
| 4. Frontend Basis Tab | DONE | 2024-12-20 |
| 5. KI-Analyse Service | DONE | 2024-12-20 |
| 6. Frontend Analyse | DONE | 2024-12-20 |
| 7. Enrichment Integration | DONE | 2024-12-20 |
| 8. Assistant Integration | DONE | 2024-12-20 |
| 9. API-Doku Refactoring | DONE | 2024-12-20 |

---

## Konfiguration (.env)

```env
# Attachment Storage
ATTACHMENT_STORAGE_PATH=./storage/attachments
ATTACHMENT_MAX_SIZE_MB=20
ATTACHMENT_ALLOWED_TYPES=image/png,image/jpeg,image/gif,image/webp,application/pdf

# Azure OpenAI Vision Deployment (z.B. gpt-4o)
AZURE_OPENAI_DEPLOYMENT_VISION=gpt-4o
```

---

## Dependencies

- `Pillow` - Thumbnail-Generierung (vermutlich bereits vorhanden)
- `pymupdf` (fitz) - PDF Text-Extraktion

---

## Notizen

_Hier werden waehrend der Implementierung Notizen hinzugefuegt_
