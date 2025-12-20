# Entity-Facet System

[Zurueck zur Uebersicht](./README.md)

Das Entity-Facet System ermoeglicht flexible, generische Datenstrukturen fuer verschiedene Analyse-Szenarien.

---

## Konzept

Das System besteht aus:
- **Entity Types**: Typdefinitionen (municipality, person, organization, event)
- **Entities**: Konkrete Instanzen eines Typs
- **Facet Types**: Eigenschaftsdefinitionen (pain_point, positive_signal, contact)
- **Facet Values**: Konkrete Werte einer Eigenschaft fuer eine Entity
- **Relation Types**: Beziehungsdefinitionen zwischen Entity Types
- **Entity Relations**: Konkrete Beziehungen zwischen Entities
- **Analysis Templates**: Konfiguration fuer Analyse-Ansichten

---

## Entity Types

### GET /v1/entity-types
Liste aller Entity-Typen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `is_active` | boolean | Nur aktive Typen |
| `is_system` | boolean | Nur System-Typen |
| `is_primary` | boolean | Nur primaere Aggregationstypen |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "municipality",
      "name": "Gemeinde",
      "name_plural": "Gemeinden",
      "description": "Kommunale Gebietskoerperschaft",
      "icon": "mdi-city",
      "color": "primary",
      "is_primary": true,
      "supports_hierarchy": true,
      "hierarchy_config": {
        "levels": ["country", "state", "district", "municipality"]
      },
      "attribute_schema": {
        "type": "object",
        "properties": {
          "population": {"type": "integer"},
          "area_km2": {"type": "number"}
        }
      },
      "is_system": true,
      "is_active": true,
      "entity_count": 500
    }
  ],
  "total": 4
}
```

### GET /v1/entity-types/{id}
Entity-Typ abrufen.

### GET /v1/entity-types/by-slug/{slug}
Entity-Typ per Slug abrufen.

### POST /v1/entity-types
Entity-Typ erstellen.

**Request Body:**
```json
{
  "slug": "custom_type",
  "name": "Mein Typ",
  "name_plural": "Meine Typen",
  "icon": "mdi-star",
  "color": "info",
  "is_primary": false,
  "supports_hierarchy": false,
  "attribute_schema": {}
}
```

### PUT /v1/entity-types/{id}
Entity-Typ aktualisieren.

### DELETE /v1/entity-types/{id}
Entity-Typ loeschen. Nur moeglich wenn keine Entities existieren.

---

## Entities

### GET /v1/entities
Entities auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_type_slug` | string | Filter nach Entity-Typ |
| `entity_type_id` | uuid | Filter nach Entity-Typ ID |
| `parent_id` | uuid | Filter nach Parent-Entity |
| `hierarchy_level` | int | Filter nach Hierarchie-Ebene (0=root) |
| `search` | string | Suche in Name |
| `has_facets` | boolean | Nur Entities mit/ohne Facets |
| `facet_type_slugs` | string | Komma-separierte Facet-Typ Slugs |
| `category_id` | uuid | Filter nach verknuepfter Kategorie |
| `is_active` | boolean | Nur aktive Entities |
| `page` | int | Seitennummer |
| `per_page` | int | Eintraege pro Seite |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "entity_type_id": "uuid",
      "entity_type_slug": "municipality",
      "name": "Musterstadt",
      "name_normalized": "musterstadt",
      "slug": "musterstadt",
      "external_id": "12345678",
      "parent_id": null,
      "hierarchy_path": "/DE/Bayern/Musterstadt",
      "hierarchy_level": 2,
      "core_attributes": {
        "population": 50000,
        "area_km2": 75.5
      },
      "latitude": 48.1234,
      "longitude": 11.5678,
      "is_active": true,
      "facet_count": 15,
      "relation_count": 3,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 500,
  "page": 1,
  "per_page": 25
}
```

### GET /v1/entities/{id}
Entity-Details abrufen.

### GET /v1/entities/by-slug/{type_slug}/{entity_slug}
Entity per Slugs abrufen.

### GET /v1/entities/{id}/brief
Kurze Entity-Info (fuer Autocomplete).

**Response:**
```json
{
  "id": "uuid",
  "name": "Musterstadt",
  "entity_type_name": "Gemeinde",
  "hierarchy_path": "/DE/Bayern/Musterstadt"
}
```

### GET /v1/entities/{id}/children
Kind-Entities abrufen (fuer hierarchische Typen).

### GET /v1/entities/{id}/documents
Dokumente abrufen, die mit einer Entity ueber Facet-Werte verknuepft sind.

### GET /v1/entities/{id}/external-data
Rohe API-Daten fuer Entities abrufen, die aus externen APIs synchronisiert wurden.

### GET /v1/entities/hierarchy/{entity_type_slug}
Hierarchie-Baum abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `max_depth` | int | Maximale Tiefe |
| `root_id` | uuid | Nur Unterknoten von |

### POST /v1/entities
Entity erstellen.

**Request Body:**
```json
{
  "entity_type_id": "uuid",
  "name": "Neue Stadt",
  "external_id": "12345679",
  "parent_id": "uuid (optional)",
  "core_attributes": {
    "population": 10000
  },
  "latitude": 48.0,
  "longitude": 11.0
}
```

### PUT /v1/entities/{id}
Entity aktualisieren.

### DELETE /v1/entities/{id}
Entity loeschen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `force` | boolean | Auch Kinder und Facets loeschen |

### GET /v1/entities/filter-options/location
Verfuegbare Filter-Optionen fuer Standort-Felder abrufen.

### GET /v1/entities/filter-options/attributes
Verfuegbare Filter-Optionen fuer core_attributes basierend auf Entity-Typ Schema.

---

## Facet Types

### GET /v1/facets/types
Facet-Typen auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `search` | string | Suche in Name und Slug |
| `is_active` | boolean | Nur aktive Typen |
| `is_time_based` | boolean | Nur zeitbasierte Typen |
| `ai_extraction_enabled` | boolean | Nur mit/ohne AI-Extraktion |
| `page` | int | Seitennummer (default: 1) |
| `per_page` | int | Eintraege pro Seite (default: 50, max: 100) |

**Caching:** Dieser Endpunkt nutzt serverseitiges Caching (5 Min. TTL) fuer bessere Performance.

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "pain_point",
      "name": "Pain Point",
      "description": "Probleme und Herausforderungen",
      "value_schema": {
        "type": "object",
        "properties": {
          "text": {"type": "string"},
          "severity": {"type": "string", "enum": ["low", "medium", "high"]}
        }
      },
      "icon": "mdi-alert-circle",
      "color": "error",
      "applicable_entity_types": ["municipality", "organization"],
      "is_time_based": false,
      "default_time_filter": "all",
      "aggregation_method": "count",
      "ai_extraction_prompt": "Extrahiere Pain Points aus dem Dokument...",
      "is_system": true,
      "is_active": true,
      "display_order": 1
    }
  ],
  "total": 4
}
```

### GET /v1/facets/types/{id}
Facet-Typ abrufen.

### GET /v1/facets/types/by-slug/{slug}
Facet-Typ per Slug.

### POST /v1/facets/types
Facet-Typ erstellen.

### PUT /v1/facets/types/{id}
Facet-Typ aktualisieren.

### DELETE /v1/facets/types/{id}
Facet-Typ loeschen.

### POST /v1/facets/types/generate-schema
KI-gestuetztes Schema und Konfiguration fuer neuen Facet-Typ generieren.

**Request Body:**
```json
{
  "name": "Budget",
  "name_plural": "Budgets",
  "description": "Haushaltsinformationen einer Gemeinde",
  "applicable_entity_types": ["municipality"]
}
```

**Response:**
```json
{
  "success": true,
  "generated": {
    "value_schema": {
      "type": "object",
      "properties": {
        "year": {"type": "integer", "description": "Haushaltsjahr"},
        "amount": {"type": "number", "description": "Betrag in Euro"},
        "category": {"type": "string", "description": "Budgetkategorie"},
        "notes": {"type": "string", "description": "Anmerkungen"}
      },
      "required": ["year", "amount"]
    },
    "ai_extraction_prompt": "Extrahiere Budgetinformationen aus dem Dokument...",
    "icon": "mdi-currency-eur",
    "color": "#4CAF50",
    "aggregation_method": "sum",
    "is_time_based": true,
    "time_field_path": "year"
  },
  "explanation": "Schema basiert auf typischen Haushaltsdaten."
}
```

---

## Facet Values

### GET /v1/facets/values
Facet-Werte auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | uuid | Filter nach Entity |
| `facet_type_id` | uuid | Filter nach Facet-Typ |
| `facet_type_slug` | string | Filter nach Facet-Typ Slug |
| `human_verified` | boolean | Nur verifizierte/unverifizierte |
| `min_confidence` | float | Mindest-Konfidenz (0-1) |
| `search` | string | Volltextsuche in text_representation (min. 2 Zeichen) |
| `time_filter` | string | `future_only`, `past_only`, `all` |
| `is_active` | boolean | Nur aktive/inaktive Werte |
| `page` | int | Seitennummer |
| `per_page` | int | Eintraege pro Seite (max. 200) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "entity_id": "uuid",
      "entity_name": "Musterstadt",
      "facet_type_id": "uuid",
      "facet_type_slug": "pain_point",
      "facet_type_name": "Pain Point",
      "value": {
        "text": "Buerger beschweren sich ueber...",
        "severity": "high"
      },
      "text_representation": "Buerger beschweren sich ueber...",
      "confidence_score": 0.85,
      "human_verified": false,
      "verified_by_id": null,
      "verified_at": null,
      "source_document_id": "uuid",
      "source_url": "https://...",
      "event_date": null,
      "valid_from": null,
      "valid_until": null,
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 100
}
```

### GET /v1/facets/values/{id}
Facet-Wert abrufen.

### POST /v1/facets/values
Facet-Wert manuell erstellen.

**Request Body:**
```json
{
  "entity_id": "uuid",
  "facet_type_id": "uuid",
  "value": {
    "description": "Buergerproteste gegen geplanten Windpark",
    "type": "Buergerprotest",
    "severity": "hoch",
    "quote": "Wir wehren uns gegen diese Verschandelung unserer Landschaft"
  },
  "text_representation": "Buergerproteste gegen geplanten Windpark",
  "confidence_score": 1.0,
  "source_url": "https://example.com/artikel",
  "event_date": "2025-06-15T14:00:00Z"
}
```

### PUT /v1/facets/values/{id}
Facet-Wert aktualisieren.

### PUT /v1/facets/values/{id}/verify
Facet-Wert verifizieren.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `verified` | boolean | Verifiziert ja/nein |

### DELETE /v1/facets/values/{id}
Facet-Wert loeschen.

### GET /v1/facets/search
Volltextsuche ueber alle Facet-Werte mit Relevanz-Ranking.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `q` | string | Suchbegriff (required, min. 2 Zeichen) |
| `entity_id` | uuid | Filter nach Entity |
| `facet_type_slug` | string | Filter nach Facet-Typ |
| `limit` | int | Max. Ergebnisse (1-100, default: 20) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "entity_id": "uuid",
      "entity_name": "Musterstadt",
      "facet_type_slug": "pain_point",
      "value": {"description": "...", "severity": "high"},
      "text_representation": "Buerger beschweren sich ueber Windkraftprojekt",
      "headline": "Buerger beschweren sich ueber <mark>Windkraft</mark>projekt",
      "rank": 0.0891,
      "confidence_score": 0.85,
      "human_verified": false,
      "source_type": "DOCUMENT",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 42,
  "query": "Windkraft",
  "search_time_ms": 12.5
}
```

### GET /v1/facets/entity/{entity_id}/summary
Facet-Zusammenfassung einer Entity.

---

## Relation Types

### GET /v1/relations/types
Beziehungstypen auflisten.

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "works_for",
      "name": "arbeitet fuer",
      "name_inverse": "beschaeftigt",
      "description": "Person arbeitet fuer Organisation/Gemeinde",
      "source_entity_type_id": "uuid",
      "source_entity_type_slug": "person",
      "target_entity_type_id": "uuid",
      "target_entity_type_slug": "municipality",
      "cardinality": "n:1",
      "attributes_schema": {
        "type": "object",
        "properties": {
          "role": {"type": "string"},
          "since": {"type": "string", "format": "date"}
        }
      },
      "is_system": true,
      "is_active": true
    }
  ],
  "total": 4
}
```

### GET /v1/relations/types/{id}
Beziehungstyp abrufen.

### GET /v1/relations/types/by-slug/{slug}
Beziehungstyp per Slug.

### POST /v1/relations/types
Beziehungstyp erstellen.

### PUT /v1/relations/types/{id}
Beziehungstyp aktualisieren.

### DELETE /v1/relations/types/{id}
Beziehungstyp loeschen.

---

## Entity Relations

### GET /v1/relations
Beziehungen auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | uuid | Entity als Source ODER Target |
| `source_entity_id` | uuid | Entity als Source |
| `target_entity_id` | uuid | Entity als Target |
| `relation_type_id` | uuid | Filter nach Beziehungstyp |
| `relation_type_slug` | string | Filter nach Beziehungstyp Slug |
| `human_verified` | boolean | Nur verifizierte |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "relation_type_id": "uuid",
      "relation_type_slug": "works_for",
      "relation_type_name": "arbeitet fuer",
      "relation_type_name_inverse": "beschaeftigt",
      "source_entity_id": "uuid",
      "source_entity_name": "Max Mustermann",
      "source_entity_type_slug": "person",
      "target_entity_id": "uuid",
      "target_entity_name": "Musterstadt",
      "target_entity_type_slug": "municipality",
      "attributes": {
        "role": "Buergermeister",
        "since": "2020-01-01"
      },
      "confidence_score": 0.95,
      "human_verified": true,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 50
}
```

### GET /v1/relations/{id}
Beziehung abrufen.

### POST /v1/relations
Beziehung erstellen.

**Request Body:**
```json
{
  "relation_type_id": "uuid",
  "source_entity_id": "uuid",
  "target_entity_id": "uuid",
  "attributes": {
    "role": "Stadtrat"
  },
  "confidence_score": 1.0
}
```

### PUT /v1/relations/{id}
Beziehung aktualisieren.

### PUT /v1/relations/{id}/verify
Beziehung verifizieren.

### DELETE /v1/relations/{id}
Beziehung loeschen.

### GET /v1/relations/graph/{entity_id}
Beziehungsgraph einer Entity.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `depth` | int | Traversierungstiefe (default: 1) |
| `relation_type_slugs` | string | Komma-separierte Typen |

**Response:**
```json
{
  "center_entity": {
    "id": "uuid",
    "name": "Musterstadt",
    "entity_type_slug": "municipality"
  },
  "nodes": [
    {
      "id": "uuid",
      "name": "Max Mustermann",
      "entity_type_slug": "person"
    }
  ],
  "edges": [
    {
      "source_id": "uuid",
      "target_id": "uuid",
      "relation_type_slug": "works_for",
      "attributes": {"role": "Buergermeister"}
    }
  ]
}
```
