# Public Data API

[Zurueck zur Uebersicht](./README.md)

Public API (v1/data) fuer extrahierte Daten, Dokumente, Gemeinden-Reports und Export.

---

## Extrahierte Daten

### GET /v1/data
Extrahierte Daten abrufen.

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `page` | int | 1 | Seite (1-basiert) |
| `per_page` | int | 20 | Eintraege pro Seite (max 100) |
| `document_id` | uuid | - | Filter nach Dokument |
| `category_id` | uuid | - | Filter nach Kategorie |
| `source_id` | uuid | - | Filter nach Quelle |
| `extraction_type` | string | - | Filter nach Extraktionstyp |
| `min_confidence` | float | - | Min. Konfidenz (0.0-1.0) |
| `human_verified` | boolean | - | Filter nach Verifikationsstatus |
| `include_rejected` | boolean | `false` | Abgelehnte Extraktionen einschliessen |
| `created_from` | date | - | Von-Datum Filter (YYYY-MM-DD) |
| `created_to` | date | - | Bis-Datum Filter (YYYY-MM-DD) |
| `search` | string | - | Suche in Dokumenttitel, URL, Inhalt und Entity-Referenzen |
| `sort_by` | string | `"created_at"` | Sortierfeld |
| `sort_order` | string | `"desc"` | Sortierreihenfolge: `asc`, `desc` |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "document_id": "uuid",
      "document_url": "https://...",
      "document_title": "Beschluss 2025/01",
      "source_id": "uuid",
      "source_name": "Stadt Musterstadt",
      "category_name": "Windenergie",
      "confidence": 0.85,
      "is_verified": false,
      "is_rejected": false,
      "rejected_by": null,
      "rejected_at": null,
      "rejection_reason": null,
      "final_content": {
        "topic": "Windkraftanlage Genehmigung",
        "summary": "Der Rat hat beschlossen...",
        "is_relevant": true,
        "municipality": "Musterstadt",
        "pain_points": ["Abstandsregelungen", "Laermschutz"],
        "positive_signals": ["Grundsaetzliche Zustimmung"],
        "decision_makers": [
          {"name": "Max Mustermann", "role": "Buergermeister"}
        ],
        "sentiment": "neutral",
        "relevanz": "hoch",
        "outreach_recommendation": {
          "priority": "high",
          "reason": "Aktive Entscheidungsphase"
        }
      },
      "extracted_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 1234
}
```

**Neue Felder in v2.2.0:**
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `is_rejected` | boolean | `true` wenn Extraktion abgelehnt |
| `rejected_by` | uuid | User-ID des ablehnenden Users |
| `rejected_at` | datetime | Zeitpunkt der Ablehnung |
| `rejection_reason` | string | Optionaler Ablehnungsgrund |

### GET /v1/data/stats
Extraktions-Statistiken.

**Query-Parameter:** Gleiche Filter wie `GET /v1/data` (document_id, category_id, source_id, extraction_type, min_confidence, human_verified, include_rejected, created_from, created_to, search)

**Response:**
```json
{
  "total": 1234,
  "verified": 456,
  "unverified": 778,
  "avg_confidence": 0.78,
  "by_type": {
    "Windenergie-Beschluss": 500,
    "Solar-Projekt": 400
  },
  "by_category": {
    "Windenergie": 800,
    "Solarenergie": 434
  },
  "high_confidence_count": 890,
  "low_confidence_count": 45
}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `total` | int | Gesamtzahl Extraktionen |
| `verified` | int | Manuell verifizierte Extraktionen |
| `unverified` | int | Noch nicht verifizierte Extraktionen |
| `avg_confidence` | float | Durchschnittliche Konfidenz (kann `null` sein) |
| `by_type` | object | Anzahl nach Extraktionstyp |
| `by_category` | object | Anzahl nach Kategorie |
| `high_confidence_count` | int | Extraktionen mit Konfidenz >= 0.8 |
| `low_confidence_count` | int | Extraktionen mit Konfidenz < 0.5 |

### GET /v1/data/stats/unverified-count
Anzahl unverifizerter Extraktionen (optimiert fuer Badge-Anzeige).

> **NEU in v2.2.0**

**Response:**
```json
{
  "unverified": 156
}
```

### GET /v1/data/locations
Orte mit extrahierten Daten.

> **Hinweis:** Dieser Endpoint gibt derzeit ein leeres Array zurueck (Legacy-Endpoint).

### GET /v1/data/countries
Laender mit extrahierten Daten.

> **Hinweis:** Dieser Endpoint gibt derzeit ein leeres Array zurueck (Legacy-Endpoint).

---

## Dokumente

### GET /v1/data/documents
Dokumente auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `source_id` | uuid | Filter nach Quelle |
| `category_id` | uuid | Filter nach Kategorie |
| `processing_status` | string | PENDING, PROCESSING, COMPLETED, FILTERED, FAILED |
| `location_name` | string | Filter nach Ort |
| `search` | string | Volltextsuche |
| `page` | int | Seite (default: 1) |
| `per_page` | int | Eintraege pro Seite (default: 20) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "url": "https://...",
      "title": "Beschluss_2025_01.pdf",
      "file_type": "application/pdf",
      "file_size": 245000,
      "processing_status": "COMPLETED",
      "processing_error": null,
      "discovered_at": "2025-01-15T10:00:00Z",
      "downloaded_at": "2025-01-15T10:01:00Z",
      "processed_at": "2025-01-15T10:02:00Z",
      "extraction_count": 1
    }
  ],
  "total": 5000
}
```

### GET /v1/data/documents/{document_id}
Dokument-Details.

**Response:**
```json
{
  "id": "uuid",
  "url": "https://...",
  "title": "Beschluss_2025_01.pdf",
  "file_type": "application/pdf",
  "file_size": 245000,
  "page_count": 5,
  "raw_text": "Volltext des Dokuments...",
  "processing_status": "COMPLETED",
  "source_name": "Stadt Musterstadt",
  "category_name": "Windenergie",
  "extractions": [
    {
      "id": "uuid",
      "confidence": 0.85,
      "final_content": {...}
    }
  ]
}
```

### GET /v1/data/documents/locations
Orte mit Dokumenten.

### GET /v1/data/search
Volltextsuche.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `q` | string | Suchbegriff |
| `category_id` | uuid | Filter |
| `limit` | int | Max. Ergebnisse |

**Response:**
```json
{
  "results": [
    {
      "document_id": "uuid",
      "title": "...",
      "snippet": "...Suchbegriff im Kontext...",
      "score": 0.95
    }
  ],
  "total": 50
}
```

### PUT /v1/data/extracted/{extraction_id}/verify
Extraktion verifizieren.

**Request Body:**
```json
{
  "verified": true,
  "notes": "Manuell geprueft"
}
```

### PUT /v1/data/extracted/{extraction_id}/reject
Extraktion ablehnen oder Ablehnung aufheben.

> **NEU in v2.2.0:** Extrahierte Daten koennen als "abgelehnt" markiert werden, wenn sie fehlerhaft, irrelevant oder falsch klassifiziert sind.

**Request Body:**
```json
{
  "rejected": true,
  "reason": "Fehlerhaft extrahiert - falsches Dokument zugeordnet",
  "cascade_to_facets": true
}
```

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `rejected` | boolean | `true` | Ablehnung setzen (`true`) oder aufheben (`false`) |
| `reason` | string | `null` | Optionaler Ablehnungsgrund (max. 1000 Zeichen) |
| `cascade_to_facets` | boolean | `true` | Verknuepfte Facet-Values ebenfalls deaktivieren |

**Response:**
```json
{
  "id": "uuid",
  "is_rejected": true,
  "rejected_by": "user-uuid",
  "rejected_at": "2025-01-15T14:30:00Z",
  "rejection_reason": "Fehlerhaft extrahiert - falsches Dokument zugeordnet",
  "deactivated_facet_values": 3,
  "protected_facet_values": 1
}
```

**Response-Felder:**
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `deactivated_facet_values` | int | Anzahl deaktivierter Facet-Values (wenn `cascade_to_facets=true`) |
| `protected_facet_values` | int | Anzahl geschuetzter Facets (verifiziert oder aus anderer Quelle) |

**Hinweise:**
- Abgelehnte Extraktionen werden standardmaessig aus Listen ausgeblendet
- Verwenden Sie `include_rejected=true` beim Abruf, um sie anzuzeigen
- Bei `cascade_to_facets=true` werden nur Facets deaktiviert, die:
  - Aus derselben Extraktion stammen
  - Nicht manuell verifiziert wurden
  - Keine anderen Quellen haben

### GET /v1/data/extracted/{extraction_id}/facets
Facet-Values abrufen, die aus dieser Extraktion erstellt wurden.

> **NEU in v2.2.0**

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `include_inactive` | boolean | `false` | Auch deaktivierte Facets einschliessen |

**Response:**
```json
[
  {
    "id": "uuid",
    "facet_type_id": "uuid",
    "facet_type_name": "Pain Point",
    "facet_type_slug": "pain_point",
    "entity_id": "uuid",
    "entity_name": "Gummersbach",
    "value": {
      "description": "Personalmangel im Bauamt",
      "severity": "hoch"
    },
    "text_representation": "Personalmangel im Bauamt",
    "confidence_score": 0.85,
    "is_active": true,
    "human_verified": false,
    "source_type": "AI_EXTRACTION",
    "source_document_id": "uuid",
    "created_at": "2025-01-15T14:30:00Z"
  }
]
```

**Hinweise:**
- Zeigt alle Facet-Values, deren `source_document_id` mit dem Dokument der Extraktion uebereinstimmt
- Mit `include_inactive=true` werden auch durch Ablehnung deaktivierte Facets angezeigt
- Nuetzlich um zu verstehen, welche Facets von einer Extraktion abhaengen

### PUT /v1/data/extracted/bulk-verify
Mehrere Extraktionen auf einmal verifizieren.

> **NEU in v2.2.0**

**Berechtigung:** Editor

Verifiziert bis zu 100 Extraktionen in einer einzigen Anfrage.

**Request Body:**
```json
{
  "ids": ["uuid1", "uuid2", "uuid3"]
}
```

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `ids` | uuid[] | Liste der Extraktions-IDs (max. 100) |

**Response:**
```json
{
  "verified_ids": ["uuid1", "uuid2"],
  "failed_ids": ["uuid3"],
  "verified_count": 2,
  "failed_count": 1
}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `verified_ids` | uuid[] | Erfolgreich verifizierte IDs (inkl. bereits verifizierter) |
| `failed_ids` | uuid[] | Fehlgeschlagene IDs (nicht gefunden oder Fehler) |
| `verified_count` | int | Anzahl erfolgreich verifizierter Extraktionen |
| `failed_count` | int | Anzahl fehlgeschlagener Extraktionen |

### GET /v1/data/by-entity/{entity_id}
Extrahierte Daten abrufen, die eine bestimmte Entity referenzieren.

> **NEU in v2.2.0**

Sucht sowohl in `primary_entity_id` als auch in `entity_references` (JSONB).

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `page` | int | 1 | Seite |
| `per_page` | int | 20 | Eintraege pro Seite (1-100) |

**Response:** ExtractedDataListResponse (wie bei `/v1/data`)

**Verwendung:**
Nuetzlich um alle Extraktionen zu finden, die sich auf eine bestimmte Kommune, Person oder Organisation beziehen.

### GET /v1/data/display-config
Globale Display-Konfiguration fuer die Ergebnistabelle abrufen.

> **NEU in v2.2.0**

Analysiert existierende `entity_references` und liefert dynamische Spaltenkonfiguration.

**Response:**
```json
{
  "columns": [
    {"key": "document", "label": "Dokument", "type": "document_link", "width": "220px"},
    {"key": "entity_references.territorial-entity", "label": "Kommune", "type": "entity_link", "width": "150px"},
    {"key": "entity_references.person", "label": "Person", "type": "entity_link", "width": "150px"},
    {"key": "confidence_score", "label": "Konfidenz", "type": "confidence", "width": "110px"},
    {"key": "relevance_score", "label": "Relevanz", "type": "confidence", "width": "110px"},
    {"key": "human_verified", "label": "Geprueft", "type": "boolean", "width": "80px"},
    {"key": "created_at", "label": "Erfasst", "type": "date", "width": "100px"}
  ],
  "entity_reference_columns": ["territorial-entity", "person"]
}
```

### GET /v1/data/display-config/{category_id}
Kategorie-spezifische Display-Konfiguration fuer die Ergebnistabelle.

> **NEU in v2.2.0**

Falls die Kategorie eine benutzerdefinierte `display_fields`-Konfiguration hat, wird diese verwendet.
Andernfalls wird eine Standardkonfiguration basierend auf `entity_reference_config` generiert.

**Response:** Wie `GET /v1/data/display-config`

---

## Document Stats & Page-Analysis

### GET /v1/data/documents/stats
Dokumenten-Statistiken nach Verarbeitungsstatus.

> **NEU in v2.2.0**

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `category_id` | uuid | Filter nach Kategorie |
| `source_id` | uuid | Filter nach Quelle |
| `document_type` | string | Filter nach Dokumenttyp |
| `search` | string | Suche in Titel und URL |
| `discovered_from` | string | Von-Datum (YYYY-MM-DD) |
| `discovered_to` | string | Bis-Datum (YYYY-MM-DD) |

**Response:**
```json
{
  "total": 1500,
  "by_status": {
    "PENDING": 50,
    "PROCESSING": 10,
    "COMPLETED": 1200,
    "FILTERED": 150,
    "FAILED": 90
  }
}
```

### GET /v1/data/documents/{document_id}/page-analysis
Status der seitenweisen Dokumentenanalyse abrufen.

> **NEU in v2.2.0**

Zeigt an, welche Seiten relevant sind und welche bereits analysiert wurden.

**Response:**
```json
{
  "document_id": "uuid",
  "page_count": 45,
  "page_analysis_status": "has_more",
  "relevant_pages": [1, 5, 12, 23, 34],
  "analyzed_pages": [1, 5, 12],
  "total_relevant_pages": 5,
  "pages_remaining": 2,
  "page_analysis_note": "Seiten mit Suchbegriffen gefunden",
  "can_analyze_more": true,
  "needs_manual_review": false
}
```

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `page_analysis_status` | string | Status: `pending`, `complete`, `has_more`, `partial`, `needs_review` |
| `relevant_pages` | int[] | Seiten mit Keyword-Matches |
| `analyzed_pages` | int[] | Bereits analysierte Seiten |
| `can_analyze_more` | boolean | Weitere Seiten koennen analysiert werden |
| `needs_manual_review` | boolean | Keine Keywords gefunden, manuelle Pruefung noetig |

### POST /v1/data/documents/{document_id}/analyze-pages
Weitere Seiten eines Dokuments analysieren.

> **NEU in v2.2.0**

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `page_numbers` | int[] | - | Spezifische Seitenzahlen (optional) |
| `max_pages` | int | 10 | Maximum zu analysierende Seiten (1-50) |

**Logik:**
- Mit `page_numbers`: Analysiert nur diese Seiten
- Ohne `page_numbers`: Analysiert verbleibende relevante Seiten

**Response:**
```json
{
  "status": "started",
  "task_id": "celery-task-uuid",
  "pages_to_analyze": [23, 34],
  "message": "Analysis started for 2 pages"
}
```

**Moegliche Status:**
- `started` - Analyse gestartet
- `complete` - Alle relevanten Seiten bereits analysiert
- `error` - Keine relevanten Seiten vorhanden

### POST /v1/data/documents/{document_id}/full-analysis
Vollstaendige Dokumentanalyse ohne Seitenfilterung starten.

> **NEU in v2.2.0**

Verwendet fuer:
- Dokumente mit `page_analysis_status = "needs_review"` (keine Keywords gefunden)
- Manuelles Override zur Analyse des gesamten Dokuments

**Response:**
```json
{
  "status": "started",
  "task_id": "celery-task-uuid",
  "message": "Full document analysis started"
}
```

---

## History

### GET /v1/data/history/crawls
Crawl-Historie.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `source_id` | uuid | Filter nach Quelle |
| `category_id` | uuid | Filter nach Kategorie |
| `limit` | int | Max. Ergebnisse (default: 20) |

**Response:**
```json
{
  "crawls": [
    {
      "id": "uuid",
      "source_id": "uuid",
      "source_name": "Stadt Musterstadt",
      "status": "COMPLETED",
      "documents_found": 15,
      "documents_new": 3,
      "started_at": "2025-01-15T10:00:00Z",
      "finished_at": "2025-01-15T10:05:00Z"
    }
  ],
  "total": 100
}
```

> **Hinweis:** Die Gemeinden-Reports (`/municipalities/*`) wurden durch das Entity-Facet-System ersetzt.
> Fuer Entity-basierte Analysen siehe [ENTITIES.md](./ENTITIES.md) und [Analysis API](#analysis-api).

---

## Export

### GET /v1/export/json
JSON-Export.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `category_id` | uuid | Filter |
| `country` | string | Filter |
| `location_name` | string | Filter |
| `min_confidence` | float | Min. Konfidenz |
| `verified_only` | boolean | Nur verifizierte |

**Response:** JSON-Datei als Download

### GET /v1/export/csv
CSV-Export.

**Query-Parameter:** Wie JSON-Export

**Response:** CSV-Datei als Download

### GET /v1/export/changes
Aenderungs-Feed.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `since` | datetime | Aenderungen seit |
| `limit` | int | Max. Ergebnisse |

**Response:**
```json
[
  {
    "id": "uuid",
    "change_type": "NEW",
    "entity_type": "extraction",
    "entity_id": "uuid",
    "changed_at": "2025-01-15T14:30:00Z",
    "data": {...}
  }
]
```

### POST /v1/export/webhook/test
Webhook testen.

---

## Async Export

Fuer Exports mit >5000 Datensaetzen wird ein asynchroner Job gestartet.

### POST /v1/export/async
Startet einen asynchronen Export-Job.

**Request Body:**
```json
{
  "entity_type": "municipality",
  "format": "json",
  "location_filter": "Nordrhein-Westfalen",
  "facet_types": ["pain_point", "positive_signal"],
  "position_keywords": ["Buergermeister"],
  "country": "DE",
  "include_facets": true,
  "filename": "mein_export"
}
```

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_type` | string | Entity-Typ (municipality, person, etc.) |
| `format` | string | json, csv, excel |
| `location_filter` | string | Filter nach Bundesland/Region |
| `facet_types` | string[] | Nur bestimmte Facet-Typen |
| `position_keywords` | string[] | Position-Filter (fuer Personen) |
| `country` | string | Laenderfilter |
| `include_facets` | boolean | Facetten einschliessen (Standard: true) |
| `filename` | string | Dateiname ohne Extension |

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "export_format": "json",
  "total_records": null,
  "processed_records": 0,
  "progress_percent": 0,
  "progress_message": null,
  "created_at": "2025-12-20T18:00:00Z",
  "is_downloadable": false
}
```

### GET /v1/export/async/{job_id}
Status eines Export-Jobs abfragen.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "export_format": "json",
  "total_records": 5432,
  "processed_records": 2500,
  "progress_percent": 46,
  "progress_message": "Verarbeitet: 2500/5432",
  "file_size": null,
  "created_at": "2025-12-20T18:00:00Z",
  "started_at": "2025-12-20T18:00:05Z",
  "is_downloadable": false
}
```

**Status-Werte:**
| Status | Beschreibung |
|--------|--------------|
| `pending` | Job wartet auf Verarbeitung |
| `processing` | Job wird verarbeitet |
| `completed` | Export fertig, Download verfuegbar |
| `failed` | Export fehlgeschlagen |
| `cancelled` | Job abgebrochen |

### GET /v1/export/async/{job_id}/download
Fertigen Export herunterladen.

**Response:** Datei als Download (JSON, CSV oder XLSX)

**Fehler:**
- `400 Bad Request` - Export noch nicht fertig
- `404 Not Found` - Job nicht gefunden oder Datei abgelaufen

### DELETE /v1/export/async/{job_id}
Export-Job abbrechen.

### GET /v1/export/async
Liste aller Export-Jobs des aktuellen Benutzers.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `status_filter` | string | Filter nach Status |
| `limit` | int | Max. Ergebnisse (Standard: 20) |
