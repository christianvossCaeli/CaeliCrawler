# Entity Attachments

[Zurueck zur Uebersicht](./README.md)

Das Attachment-System ermoeglicht das Hochladen und Verwalten von Dateianhängen (Bilder, PDFs) zu Entities mit optionaler KI-Analyse.

---

## Uebersicht

Das Attachment-System ermoeglicht:
- Upload von Bildern (PNG, JPEG, GIF, WebP) und PDFs zu Entities
- Automatische Thumbnail-Generierung fuer Bilder
- KI-gestuetzte Analyse (Vision API fuer Bilder, Text-Extraktion fuer PDFs)
- Extraktion von Facet-Vorschlaegen aus analysierten Anhängen
- Uebernahme erkannter Facets in das Entity-Facet-System

---

## Konfiguration (.env)

```bash
# Attachment Storage
ATTACHMENT_STORAGE_PATH=./storage/attachments
ATTACHMENT_MAX_SIZE_MB=20
ATTACHMENT_ALLOWED_TYPES=image/png,image/jpeg,image/gif,image/webp,application/pdf

# Azure OpenAI Vision Deployment (fuer KI-Analyse)
AZURE_OPENAI_DEPLOYMENT_VISION=gpt-4o
```

---

## Endpoints

### POST /v1/entities/{entity_id}/attachments
Datei zu einer Entity hochladen.

**Content-Type:** `multipart/form-data`

**Request Body:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `file` | File | Die hochzuladende Datei (Bild oder PDF) |
| `description` | string | Optionale Beschreibung des Anhangs |
| `auto_analyze` | boolean | Automatisch KI-Analyse starten (default: false) |

**Erlaubte Dateitypen:** PNG, JPEG, GIF, WebP, PDF

**Max. Dateigroesse:** 20 MB (konfigurierbar)

**Response:**
```json
{
  "id": "uuid",
  "entity_id": "uuid",
  "filename": "dokument.pdf",
  "content_type": "application/pdf",
  "file_size": 1234567,
  "description": "Beschlussdokument",
  "analysis_status": "PENDING",
  "is_image": false,
  "is_pdf": true,
  "uploaded_by_id": "uuid",
  "created_at": "2025-01-15T14:30:00Z",
  "updated_at": "2025-01-15T14:30:00Z"
}
```

**Fehler:**
- `400 Bad Request` - Ungueltiger Dateityp oder Datei zu gross
- `404 Not Found` - Entity nicht gefunden

---

### GET /v1/entities/{entity_id}/attachments
Alle Anhänge einer Entity auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `skip` | int | Offset (default: 0) |
| `limit` | int | Max. Ergebnisse (default: 50) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "entity_id": "uuid",
      "filename": "foto.jpg",
      "content_type": "image/jpeg",
      "file_size": 512000,
      "description": "Standortfoto",
      "analysis_status": "COMPLETED",
      "analysis_result": {
        "description": "Luftaufnahme eines Windparks...",
        "detected_text": ["Windpark Nord", "2024"],
        "entities": {
          "locations": ["Musterstadt"],
          "organizations": ["Stadtwerke GmbH"]
        },
        "facet_suggestions": [...]
      },
      "analyzed_at": "2025-01-15T14:35:00Z",
      "is_image": true,
      "is_pdf": false,
      "uploaded_by_id": "uuid",
      "created_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 5
}
```

---

### GET /v1/entities/{entity_id}/attachments/{attachment_id}
Einzelnes Attachment-Metadaten abrufen.

**Response:** Attachment-Objekt (wie oben)

---

### GET /v1/entities/{entity_id}/attachments/{attachment_id}/download
Datei herunterladen.

**Response:** Binary-Daten mit entsprechendem Content-Type Header

**Fehler:**
- `404 Not Found` - Attachment nicht gefunden
- `500 Internal Server Error` - Datei nicht auf dem Filesystem

---

### GET /v1/entities/{entity_id}/attachments/{attachment_id}/thumbnail
Thumbnail herunterladen (nur fuer Bilder).

**Response:** Binary-Daten (JPEG, max. 256x256 px)

**Fehler:**
- `404 Not Found` - Attachment oder Thumbnail nicht gefunden
- `400 Bad Request` - Kein Bild-Attachment

---

### PATCH /v1/entities/{entity_id}/attachments/{attachment_id}
Attachment-Beschreibung aktualisieren.

**Request Body:**
```json
{
  "description": "Aktualisierte Beschreibung"
}
```

**Response:** Aktualisiertes Attachment-Objekt

---

### DELETE /v1/entities/{entity_id}/attachments/{attachment_id}
Attachment loeschen (Datei + DB-Eintrag).

**Response:**
```json
{
  "message": "Attachment deleted successfully"
}
```

---

## KI-Analyse

### POST /v1/entities/{entity_id}/attachments/{attachment_id}/analyze
KI-Analyse fuer ein Attachment starten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `extract_facets` | boolean | Facet-Vorschlaege extrahieren (default: true) |

**Funktionsweise:**
1. Fuer Bilder: Azure OpenAI Vision API analysiert den Bildinhalt
2. Fuer PDFs: Text wird extrahiert (pymupdf) und mit KI analysiert
3. Extrahierte Informationen werden als `analysis_result` gespeichert
4. Optional werden Facet-Vorschlaege basierend auf Entity-Typ generiert

**Response:**
```json
{
  "message": "Analysis started",
  "task_id": "uuid",
  "attachment_id": "uuid"
}
```

**Analyse-Status Werte:**
| Status | Beschreibung |
|--------|--------------|
| `PENDING` | Noch nicht analysiert |
| `ANALYZING` | Analyse laeuft |
| `COMPLETED` | Analyse abgeschlossen |
| `FAILED` | Analyse fehlgeschlagen |

**Analyse-Ergebnis Schema:**
```json
{
  "analysis_result": {
    "description": "KI-generierte Beschreibung des Inhalts",
    "detected_text": ["Text1", "Text2"],
    "entities": {
      "persons": ["Max Mustermann"],
      "organizations": ["Firma GmbH"],
      "locations": ["Berlin"],
      "dates": ["2025-01-15"]
    },
    "facet_suggestions": [
      {
        "facet_type_slug": "pain_point",
        "value": {"text": "Hohe Kosten"},
        "confidence": 0.85,
        "source_text": "...die hohen Investitionskosten..."
      }
    ],
    "raw_ocr": "Vollstaendiger extrahierter Text...",
    "ai_model_used": "gpt-4o"
  },
  "analysis_error": null,
  "analyzed_at": "2025-01-15T14:35:00Z"
}
```

---

### POST /v1/entities/{entity_id}/attachments/{attachment_id}/apply-facets
Ausgewaehlte Facet-Vorschlaege aus der Analyse als FacetValues uebernehmen.

> **NEU:** Dieser Endpoint ermoeglicht die Uebernahme von durch KI erkannten Facet-Vorschlaegen in das Entity-Facet-System.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `facet_indices` | int[] | Indices der zu uebernehmenden Vorschlaege (0-basiert) |

**Beispiel-Request:**
```http
POST /v1/entities/{entity_id}/attachments/{attachment_id}/apply-facets?facet_indices=0&facet_indices=2&facet_indices=3
```

**Voraussetzungen:**
- Attachment muss analysiert sein (status: COMPLETED)
- `analysis_result.facet_suggestions` muss vorhanden sein
- Angegebene Indices muessen gueltig sein

**Response:**
```json
{
  "success": true,
  "applied_count": 3,
  "facet_value_ids": [
    "uuid-1",
    "uuid-2",
    "uuid-3"
  ],
  "message": "3 Facet(s) erfolgreich uebernommen"
}
```

**Fehler:**
- `400 Bad Request` - Keine Indices angegeben
- `404 Not Found` - Attachment nicht gefunden
- `422 Unprocessable Entity` - Attachment nicht analysiert oder keine Vorschlaege

**Details zur Facet-Erstellung:**
- `source_type` wird auf `ATTACHMENT` gesetzt
- `source_attachment_id` referenziert das Quell-Attachment
- `confidence_score` wird aus dem Vorschlag uebernommen
- `human_verified` wird auf `false` gesetzt (kann spaeter verifiziert werden)

---

## Integration mit Entity Enrichment

Attachments koennen als Datenquelle fuer das Entity Enrichment System verwendet werden.

### Enrichment Sources

Bei Verwendung des Entity Enrichment Systems (`GET /v1/entity-data/enrichment-sources/{entity_id}`) werden Attachments als Quelle angezeigt:

```json
{
  "sources": {
    "attachments": {
      "available": true,
      "count": 3,
      "last_updated": "2025-01-15T14:35:00Z",
      "label": "Anhaenge"
    }
  }
}
```

### Automatische Facet-Extraktion

Beim Enrichment-Prozess werden analysierte Attachments automatisch einbezogen:
1. Alle analysierten Attachments der Entity werden gesammelt
2. Deren `facet_suggestions` werden in den Enrichment-Prompt einbezogen
3. Die KI schlaegt Facets basierend auf allen Quellen (inkl. Attachments) vor

Siehe [ENRICHMENT.md](./ENRICHMENT.md) fuer Details.

---

## Datenmodell

### EntityAttachment

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | UUID | Eindeutige ID |
| `entity_id` | UUID | Referenz zur Entity |
| `filename` | string | Originaler Dateiname |
| `content_type` | string | MIME-Type |
| `file_size` | integer | Groesse in Bytes |
| `file_path` | string | Relativer Pfad im Storage |
| `file_hash` | string | SHA256 Hash der Datei |
| `description` | string | Optionale Beschreibung |
| `analysis_status` | enum | PENDING, ANALYZING, COMPLETED, FAILED |
| `analysis_result` | JSONB | Ergebnis der KI-Analyse |
| `analysis_error` | string | Fehlermeldung bei FAILED |
| `analyzed_at` | datetime | Zeitpunkt der Analyse |
| `ai_model_used` | string | Verwendetes KI-Modell |
| `uploaded_by_id` | UUID | Referenz zum Uploader |
| `created_at` | datetime | Erstellungszeitpunkt |
| `updated_at` | datetime | Letzter Aenderungszeitpunkt |

### FacetValue Source Types

FacetValues koennen verschiedene Quelltypen haben:

| Source Type | Beschreibung |
|-------------|--------------|
| `DOCUMENT` | Aus Dokument extrahiert |
| `MANUAL` | Manuell erstellt |
| `PYSIS` | Aus PySis importiert |
| `ENRICHMENT` | Durch Entity Enrichment erstellt |
| `ATTACHMENT` | Aus Attachment-Analyse |

Bei `ATTACHMENT` wird zusaetzlich `source_attachment_id` gesetzt.

---

## Best Practices

### Datei-Upload
1. Dateien sollten komprimiert werden bevor sie hochgeladen werden
2. Aussagekraeftige Beschreibungen hinzufuegen
3. Bei grossen Mengen: Batch-Upload implementieren

### KI-Analyse
1. Analyse nur bei Bedarf starten (nicht automatisch fuer alle Uploads)
2. Vor Uebernahme von Facets: Vorschlaege pruefen
3. Bei schlechter Qualitaet: Manuell Facets erstellen

### Facet-Uebernahme
1. Immer die Vorschlaege vor Uebernahme pruefen
2. Bei niedriger Konfidenz (<0.7): Kritisch hinterfragen
3. Uebernommene Facets spaeter verifizieren

---

## Fehler-Codes

| Code | Bedeutung |
|------|-----------|
| `400` | Ungueltiger Dateityp, Datei zu gross, keine Indices |
| `404` | Entity oder Attachment nicht gefunden |
| `422` | Attachment nicht analysiert |
| `500` | Filesystem-Fehler |
