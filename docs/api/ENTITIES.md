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
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `page` | int | 1 | Seite (1-basiert) |
| `per_page` | int | 50 | Eintraege pro Seite (max 500) |
| `entity_type_slug` | string | - | Filter nach Entity-Typ (Slug) |
| `entity_type_id` | uuid | - | Filter nach Entity-Typ (ID) |
| `parent_id` | uuid | - | Filter nach Parent-Entity |
| `hierarchy_level` | int | - | Filter nach Hierarchie-Ebene (0=root) |
| `is_active` | boolean | - | Nur aktive Entities |
| `search` | string | - | Suche in Name, name_normalized und external_id |
| `country` | string | - | Filter nach Laendercode (DE, GB, etc.) |
| `admin_level_1` | string | - | Filter nach Bundesland/Region |
| `admin_level_2` | string | - | Filter nach Landkreis/District |
| `core_attr_filters` | string | - | JSON-codierte Filter fuer `core_attributes` (siehe unten) |
| `api_configuration_id` | uuid | - | Filter nach API-Konfiguration |
| `has_facets` | boolean | - | Nur Entities mit/ohne Facets |
| `sort_by` | string | - | Sortierung: `name`, `hierarchy_path`, `external_id`, `created_at`, `updated_at`, `facet_count`, `relation_count` |
| `sort_order` | string | `"asc"` | Sortierreihenfolge: `asc`, `desc` |

> **Hinweis:** Die Parameter `facet_type_slugs` und `category_id` existieren nicht in diesem Endpoint. Verwenden Sie stattdessen `/v1/facets/values` mit `entity_id` Filter.

**core_attr_filters Syntax:**

> **NEU in v2.2.0:** Unterstuetzt jetzt Range-Filter fuer numerische Attribute.

Das `core_attr_filters` Query-Parameter ermoeglicht Filterung nach Werten in `core_attributes`. Zwei Filter-Modi werden unterstuetzt:

**1. Exakter Match (String/Zahl):**
```json
{"status": "active", "locality_type": "Stadt"}
```

**2. Range-Filter (fuer numerische Attribute):**
```json
{"power_mw": {"min": 10, "max": 50}}
```

**Kombiniertes Beispiel:**
```
GET /v1/entities?entity_type_slug=wind_turbine&core_attr_filters={"status":"active","power_mw":{"min":10,"max":50}}
```

| Range-Key | Typ | Beschreibung |
|-----------|-----|--------------|
| `min` | number | Minimum (inklusive, >= Vergleich) |
| `max` | number | Maximum (inklusive, <= Vergleich) |

**Dynamische Schema-Introspection:**
Wenn fuer einen Entity-Typ kein `attribute_schema` definiert ist, werden die filterbaren Attribute automatisch aus vorhandenen Entities ermittelt. Der Endpoint `/v1/entities/{entity_type_slug}/attribute-filter-options` liefert dann:
- Automatisch erkannte Attribute aus tatsaechlichen Daten
- Min/Max-Werte fuer numerische Felder
- `is_numeric: true` fuer Range-Filter-faehige Attribute

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

### GET /v1/entities/{id}/sources
DataSources abrufen, die mit einer Entity verknuepft sind.

> **NEU in v2.2.0**

Findet DataSources ueber zwei Pfade:
1. **Direkte Verknuepfung:** `entity_id` in `DataSource.extra_data.entity_ids` Array
2. **Indirekt:** Entity → FacetValues → Documents → DataSources

**Response:**
```json
{
  "entity_id": "uuid",
  "entity_name": "Musterstadt",
  "sources": [
    {
      "id": "uuid",
      "name": "Stadt Musterstadt",
      "url": "https://musterstadt.de",
      "source_type": "WEBSITE",
      "status": "ACTIVE",
      "document_count": 42,
      "last_crawled": "2025-01-15T10:00:00Z"
    }
  ],
  "total_sources": 3
}
```

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
Location-Filter-Optionen abrufen (Laender, Bundeslaender, Landkreise).

> **NEU in v2.2.0**

Liefert verfuegbare Werte fuer geografische Filter. Unterstuetzt kaskadierte Filterung.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `country` | string | Filtert `admin_level_1` Optionen nach Land |
| `admin_level_1` | string | Filtert `admin_level_2` Optionen nach Bundesland |

**Response:**
```json
{
  "countries": ["DE", "AT", "CH"],
  "admin_level_1": ["Bayern", "Nordrhein-Westfalen", "Baden-Wuerttemberg"],
  "admin_level_2": ["Oberbergischer Kreis", "Rheinisch-Bergischer Kreis"]
}
```

**Verwendung:**
```
GET /v1/entities/filter-options/location
→ Alle Laender, Bundeslaender und Landkreise

GET /v1/entities/filter-options/location?country=DE
→ admin_level_1 nur fuer Deutschland

GET /v1/entities/filter-options/location?country=DE&admin_level_1=Nordrhein-Westfalen
→ admin_level_2 nur fuer NRW
```

### GET /v1/entities/filter-options/attributes
Attribut-Filter-Optionen fuer einen Entity-Typ abrufen.

> **NEU in v2.2.0**

Liefert filterbare Attribute basierend auf dem `attribute_schema` des Entity-Typs.
Falls kein Schema definiert ist, werden Attribute dynamisch aus vorhandenen Daten introspiziert.

**Query-Parameter:**
| Parameter | Typ | Required | Beschreibung |
|-----------|-----|----------|--------------|
| `entity_type_slug` | string | ja | Slug des Entity-Typs |
| `attribute_key` | string | nein | Spezifisches Attribut fuer Werte-Lookup |

**Response:**
```json
{
  "entity_type_slug": "wind_turbine",
  "entity_type_name": "Windkraftanlage",
  "attributes": [
    {
      "key": "status",
      "title": "Status",
      "description": "Betriebsstatus der Anlage",
      "type": "string",
      "format": null,
      "is_numeric": false,
      "min_value": null,
      "max_value": null
    },
    {
      "key": "power_mw",
      "title": "Leistung (MW)",
      "description": null,
      "type": "number",
      "format": null,
      "is_numeric": true,
      "min_value": 0.5,
      "max_value": 8.0
    }
  ],
  "attribute_values": null
}
```

**Mit Attribut-Werten:**
```
GET /v1/entities/filter-options/attributes?entity_type_slug=wind_turbine&attribute_key=status
```

```json
{
  "entity_type_slug": "wind_turbine",
  "entity_type_name": "Windkraftanlage",
  "attributes": [...],
  "attribute_values": {
    "status": ["in_betrieb", "geplant", "genehmigt", "ausserbetrieb"]
  }
}
```

**Dynamische Introspection:**
Wenn kein `attribute_schema` definiert ist:
- Attribute werden aus vorhandenen `core_attributes` ermittelt
- Bekannte numerische Felder (population, power_mw, etc.) erhalten `is_numeric: true`
- Min/Max-Werte werden fuer numerische Felder berechnet
- Maximal 50 Attribute werden erkannt

### GET /v1/entities/geojson
Entities als GeoJSON FeatureCollection fuer Kartendarstellung.

> **NEU in v2.2.0**

Optimiert fuer grosse Datensaetze mit Unterstuetzung fuer Clustering.

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `entity_type_slug` | string | - | Filter nach Entity-Typ |
| `country` | string | - | Filter nach Laendercode |
| `admin_level_1` | string | - | Filter nach Bundesland |
| `admin_level_2` | string | - | Filter nach Landkreis |
| `search` | string | - | Suche im Namen |
| `include_geometry` | boolean | `true` | Polygon-Geometrien einschliessen |
| `limit` | int | 50000 | Max. Entities (1-100000) |

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [11.5678, 48.1234]
      },
      "properties": {
        "id": "uuid",
        "name": "Musterstadt",
        "slug": "musterstadt",
        "external_id": "12345678",
        "entity_type_slug": "municipality",
        "entity_type_name": "Gemeinde",
        "icon": "mdi-city",
        "color": "#1976D2",
        "country": "DE",
        "admin_level_1": "Bayern",
        "admin_level_2": "Oberland",
        "geometry_type": "Point"
      }
    }
  ],
  "total_with_coords": 450,
  "total_without_coords": 50
}
```

**Geometrie-Typen:**
- `Point` - Aus `latitude`/`longitude` Feldern generiert
- `Polygon` - Aus `geometry` Feld (z.B. Gemeindegrenzen)
- `MultiPolygon` - Komplexe Geometrien aus `geometry` Feld

**Felder in Properties:**
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | uuid | Entity-ID |
| `name` | string | Name der Entity |
| `slug` | string | URL-freundlicher Slug |
| `entity_type_slug` | string | Typ-Slug fuer Icon/Farbe |
| `icon` | string | Material Design Icon |
| `color` | string | Hex-Farbcode |
| `geometry_type` | string | Point, Polygon, MultiPolygon |

**Statistik-Felder:**
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `total_with_coords` | int | Entities mit Geo-Daten |
| `total_without_coords` | int | Entities ohne Geo-Daten |

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

### GET /v1/facets/types/for-category/{category_id}
Alle FacetTypes abrufen, die fuer eine bestimmte Kategorie relevant sind.

> **NEU in v2.2.0**

Die Verbindung laeuft ueber: Category → EntityTypes → FacetTypes (via `applicable_entity_type_slugs`).
Nuetzlich fuer dynamisches Laden von FacetTypes in der ResultsView basierend auf dem Kategorie-Filter.

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `ai_extraction_enabled` | boolean | `true` | Nur Typen mit aktivierter KI-Extraktion |
| `is_active` | boolean | `true` | Nur aktive Typen |

**Response:**
```json
[
  {
    "id": "uuid",
    "slug": "pain_point",
    "name": "Pain Point",
    "description": "Probleme und Herausforderungen",
    "icon": "mdi-alert-circle",
    "color": "error",
    "applicable_entity_types": ["municipality"],
    "ai_extraction_enabled": true,
    "is_active": true
  }
]
```

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
      "created_at": "2025-01-15T10:00:00Z",
      "target_entity_type_icon": "mdi-account",
      "target_entity_type_color": "secondary"
    }
  ],
  "total": 100
}
```

**Neue Felder in v2.2.0:**
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `target_entity_type_icon` | string | Icon des Ziel-Entity-Typs (bei Relation-Facets) |
| `target_entity_type_color` | string | Farbe des Ziel-Entity-Typs (z.B. `primary`, `secondary`) |

Diese Felder sind relevant fuer Facet-Values, die auf eine andere Entity verweisen (z.B. "arbeitet_fuer" Relationen).

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

### GET /v1/facets/entity/{entity_id}/referenced-by
Alle FacetValues abrufen, die diese Entity als `target_entity` referenzieren.

> **NEU in v2.2.0**

Zeigt, wo diese Entity verwendet/referenziert wird, z.B. eine Person-Entity, die in Kontakt-Facets anderer Entities referenziert wird.

**Query-Parameter:**
| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `page` | int | 1 | Seitennummer |
| `per_page` | int | 50 | Eintraege pro Seite (max 200) |
| `facet_type_slug` | string | - | Filter nach Facet-Typ |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "entity_id": "uuid",
      "entity_name": "Musterstadt",
      "facet_type_slug": "contact",
      "facet_type_name": "Ansprechpartner",
      "value": {"role": "Buergermeister"},
      "text_representation": "Max Mustermann - Buergermeister",
      "confidence_score": 0.95,
      "human_verified": true,
      "source_document_id": "uuid",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 50
}
```

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
