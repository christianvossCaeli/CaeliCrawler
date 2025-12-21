# Analysis API

[Zurueck zur Uebersicht](./README.md)

API-Endpoints fuer Entity-Analyse, Reports und Statistiken.

---

## Statistiken

### GET /v1/analysis/stats
Gesamtstatistiken fuer das Entity-Facet-System.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_type_slug` | string | Filter nach Entity-Typ |
| `category_id` | uuid | Filter nach Kategorie |

**Response:**
```json
{
  "overview": {
    "total_entities": 1234,
    "total_facet_values": 5678,
    "total_relations": 890,
    "verified_facet_values": 2345,
    "verification_rate": 0.41
  },
  "by_entity_type": {
    "municipality": {"name": "Gemeinde", "count": 800},
    "person": {"name": "Person", "count": 300},
    "organization": {"name": "Organisation", "count": 134}
  },
  "by_facet_type": {
    "pain_point": {"name": "Schmerzpunkt", "count": 2000},
    "positive_signal": {"name": "Positives Signal", "count": 1500},
    "contact": {"name": "Kontakt", "count": 1000}
  },
  "by_relation_type": {
    "works_for": {"name": "Arbeitet fuer", "count": 400},
    "located_in": {"name": "Befindet sich in", "count": 490}
  }
}
```

---

## Analyse-Uebersicht

### GET /v1/analysis/overview
Uebersicht ueber Entities mit aggregierten Facet-Daten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `template_id` | uuid | Analyse-Template ID |
| `template_slug` | string | Analyse-Template Slug |
| `entity_type_slug` | string | Entity-Typ (falls kein Template) |
| `category_id` | uuid | Filter nach Kategorie |
| `facet_types` | string | Komma-getrennte Facet-Typ-Slugs |
| `time_filter` | string | `future_only`, `past_only`, `all` |
| `min_confidence` | float | Min. Konfidenz (default: 0.7) |
| `min_facet_values` | int | Min. Facet-Anzahl (default: 1) |
| `limit` | int | Max. Ergebnisse (default: 100) |

**Response:**
```json
{
  "entity_type": {
    "id": "uuid",
    "slug": "municipality",
    "name": "Gemeinde",
    "name_plural": "Gemeinden"
  },
  "template": {
    "id": "uuid",
    "slug": "wind-energy-analysis",
    "name": "Windenergie-Analyse"
  },
  "filters": {
    "category_id": null,
    "facet_types": ["pain_point", "positive_signal"],
    "time_filter": "future_only",
    "min_confidence": 0.7
  },
  "total_entities": 50,
  "entities": [
    {
      "entity_id": "uuid",
      "entity_name": "Musterstadt",
      "entity_slug": "musterstadt",
      "external_id": "05123000",
      "hierarchy_path": "DE/NRW/Kreis Muster/Musterstadt",
      "latitude": 51.2277,
      "longitude": 6.7735,
      "total_facet_values": 45,
      "verified_count": 20,
      "avg_confidence": 0.82,
      "facet_counts": {
        "pain_point": 15,
        "positive_signal": 20,
        "contact": 10
      },
      "relation_count": 5,
      "source_count": 3,
      "latest_facet_date": "2025-01-15T14:30:00Z"
    }
  ]
}
```

---

## Entity-Report

### GET /v1/analysis/report/{entity_id}
Detaillierter Analyse-Report fuer eine Entity.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `template_id` | uuid | Analyse-Template ID |
| `template_slug` | string | Analyse-Template Slug |
| `category_id` | uuid | Filter nach Kategorie |
| `time_filter` | string | `future_only`, `past_only`, `all` |
| `min_confidence` | float | Min. Konfidenz (default: 0.7) |

**Response:**
```json
{
  "entity": {
    "id": "uuid",
    "name": "Musterstadt",
    "slug": "musterstadt",
    "external_id": "05123000",
    "hierarchy_path": "DE/NRW/Kreis Muster/Musterstadt",
    "core_attributes": {
      "population": 50000,
      "area_km2": 45.5
    },
    "latitude": 51.2277,
    "longitude": 6.7735
  },
  "entity_type": {
    "id": "uuid",
    "slug": "municipality",
    "name": "Gemeinde"
  },
  "template": {
    "id": "uuid",
    "slug": "wind-energy-analysis",
    "name": "Windenergie-Analyse"
  },
  "overview": {
    "total_facet_values": 45,
    "verified_values": 20,
    "facet_type_count": 5,
    "relation_count": 8,
    "source_count": 3
  },
  "facets": {
    "pain_point": {
      "facet_type_id": "uuid",
      "facet_type_slug": "pain_point",
      "facet_type_name": "Schmerzpunkte",
      "icon": "mdi-alert-circle",
      "color": "#F44336",
      "values": [
        {
          "id": "uuid",
          "value": {"text": "Strenge Abstandsregelungen", "type": "regulation"},
          "text": "Strenge Abstandsregelungen von 1000m",
          "event_date": null,
          "confidence": 0.92,
          "verified": true,
          "source_url": "https://...",
          "document": {
            "id": "uuid",
            "title": "Ratsbeschluss 2025/01",
            "url": "https://..."
          },
          "occurrence_count": 3,
          "first_seen": "2025-01-10T00:00:00Z",
          "last_seen": "2025-01-15T00:00:00Z"
        }
      ],
      "aggregated": {
        "total": 15,
        "unique": 10,
        "verified": 5,
        "avg_confidence": 0.85
      }
    }
  },
  "relations": [
    {
      "id": "uuid",
      "relation_type": "works_for",
      "relation_name": "Arbeitet fuer",
      "direction": "incoming",
      "related_entity": {
        "id": "uuid",
        "name": "Max Mustermann",
        "slug": "max-mustermann",
        "type": "person",
        "type_name": "Person"
      },
      "attributes": {"position": "Buergermeister"},
      "confidence": 0.95,
      "verified": true
    }
  ],
  "sources": [
    {
      "id": "uuid",
      "name": "Stadt Musterstadt - Ratsinformationssystem",
      "url": "https://...",
      "is_active": true
    }
  ]
}
```

---

## Analyse-Templates

### GET /v1/analysis/templates
Verfuegbare Analyse-Templates.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_type_slug` | string | Filter nach Entity-Typ |
| `page` | int | Seite |
| `per_page` | int | Eintraege pro Seite |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "wind-energy-analysis",
      "name": "Windenergie-Analyse",
      "description": "Analyse von Gemeinden bzgl. Windenergie-Projekten",
      "primary_entity_type": {
        "id": "uuid",
        "slug": "municipality",
        "name": "Gemeinde"
      },
      "facet_config": [
        {
          "facet_type_slug": "pain_point",
          "label": "Hindernisse",
          "enabled": true,
          "display_order": 1
        }
      ],
      "is_system": true,
      "is_active": true,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-15T00:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 50,
  "pages": 1
}
```

### GET /v1/analysis/templates/{template_id}
Template nach ID abrufen.

### GET /v1/analysis/templates/by-slug/{slug}
Template nach Slug abrufen.

### POST /v1/analysis/templates
Neues Template erstellen (Admin).

**Request Body:**
```json
{
  "slug": "solar-analysis",
  "name": "Solar-Analyse",
  "description": "Analyse fuer Solarenergie-Projekte",
  "primary_entity_type_id": "uuid",
  "facet_config": [
    {
      "facet_type_slug": "pain_point",
      "label": "Hindernisse",
      "enabled": true,
      "display_order": 1,
      "time_filter": null
    }
  ],
  "report_config": {
    "show_map": true,
    "export_formats": ["pdf", "excel"]
  }
}
```

### PUT /v1/analysis/templates/{template_id}
Template aktualisieren.

### DELETE /v1/analysis/templates/{template_id}
Template loeschen (nur nicht-System-Templates).

---

## Verwendung in der iOS-App

Die Analysis-Endpoints werden verwendet fuer:

1. **Dashboard**: Anzeige von Gesamtstatistiken
2. **Entity-Detail**: Detaillierte Reports mit Facetten und Relationen
3. **Entity-Liste**: Uebersicht mit aggregierten Kennzahlen
4. **Export**: Vorschau vor Datenexport

### Swift-Code-Beispiel

```swift
// Repository-Aufruf
let stats = try await AnalysisRepository.shared.fetchDataQualityStats()
let report = try await AnalysisRepository.shared.fetchEntityReport(
    entityId: entityId,
    templateSlug: "wind-energy-analysis"
)
```
