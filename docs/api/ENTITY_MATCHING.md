# Entity-Matching API

Das Entity-Matching-System gewährleistet konsistente Entity-Erstellung und verhindert Duplikate über alle Import-Pfade hinweg.

## Übersicht

Entities werden über drei Pfade erstellt:
1. **Crawling-Pipeline** - Automatische Extraktion aus Dokumenten
2. **Smart Query** - KI-gesteuerte Entity-Erstellung
3. **REST API** - Manuelle Entity-Erstellung

Alle Pfade nutzen den zentralen `EntityMatchingService` für konsistentes Verhalten.

## Matching-Strategie

Die Entity-Suche erfolgt in dieser Reihenfolge:

```
1. external_id Match (wenn vorhanden)
   ↓ nicht gefunden
2. name_normalized + entity_type Match (exakt)
   ↓ nicht gefunden
3. Similarity Match (wenn threshold < 1.0)
   ↓ nicht gefunden
4. Neue Entity erstellen
```

## Name-Normalisierung

### Algorithmus

```python
def normalize_entity_name(name: str, country: str = "DE") -> str:
    result = name.lower()

    # Länder-spezifische Ersetzungen (DE/AT/CH)
    replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
    for old, new in replacements.items():
        result = result.replace(old, new)

    # Diakritische Zeichen entfernen (é → e, ñ → n)
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if not unicodedata.combining(c))

    # Nur alphanumerische Zeichen behalten
    result = re.sub(r"[^a-z0-9]", "", result)

    return result
```

### Beispiele

| Original | Normalisiert |
|----------|--------------|
| `München` | `muenchen` |
| `Köln` | `koeln` |
| `Sankt Augustin` | `sanktaugustin` |
| `Bad Homburg v.d.H.` | `badhomburgvdh` |
| `BERLIN` | `berlin` |

## Unique Constraint

Die Datenbank erzwingt Eindeutigkeit über einen partiellen Index:

```sql
CREATE UNIQUE INDEX uq_entity_type_name_normalized
ON entities (entity_type_id, name_normalized)
WHERE is_active = true AND name_normalized IS NOT NULL;
```

### Verhalten bei Duplikaten

- Bei Versuch, eine Entity mit existierendem `(entity_type_id, name_normalized)` zu erstellen:
  - **API gibt existierende Entity zurück** (kein Fehler)
  - Race Conditions werden automatisch behandelt

## Similarity-Matching

Für Fuzzy-Deduplizierung kann ein Similarity-Threshold < 1.0 gesetzt werden.

### Algorithmus

1. **Normalisierung für Vergleich**:
   - Lowercase
   - Präfix-Entfernung: `stadt`, `gemeinde`, `landkreis`, etc.
   - Suffix-Entfernung: `stadt`, `gemeinde`
   - Umlaut-Ersetzung

2. **Similarity-Berechnung**:
   - SequenceMatcher Ratio (Levenshtein-basiert)
   - Substring-Boost (wenn einer im anderen enthalten)
   - Jaccard-Similarity für Multi-Wort-Namen

### Konfiguration

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `similarity_threshold` | `1.0` | Nur exakte Matches (kein Fuzzy) |
| `similarity_threshold` | `0.85` | Empfohlen für Fuzzy-Matching |

### Beispiele

| Name 1 | Name 2 | Similarity | Ergebnis |
|--------|--------|------------|----------|
| `München` | `München` | 1.0 | Match |
| `München` | `Muenchen` | 0.95 | Match (bei threshold ≤ 0.95) |
| `Stadt München` | `München` | 0.90 | Match (bei threshold ≤ 0.90) |
| `Berlin` | `Hamburg` | 0.35 | Kein Match |

## Race-Condition-Safety

Der Service verwendet ein UPSERT-Pattern:

```python
try:
    entity = Entity(...)
    session.add(entity)
    await session.flush()
    return entity
except IntegrityError:
    # Concurrent creation detected
    await session.rollback()
    return await find_by_normalized_name(entity_type_id, name_normalized)
```

**Garantie**: Bei parallelen Anfragen mit gleichem Namen wird nur eine Entity erstellt.

## API-Verwendung

### Entity erstellen/finden

```http
POST /api/v1/entities
Content-Type: application/json

{
  "entity_type_slug": "municipality",
  "name": "München",
  "country": "DE",
  "external_id": "09162000",  // Optional
  "core_attributes": {
    "population": 1500000
  }
}
```

**Response** (Entity gefunden):
```json
{
  "id": "a1b2c3d4-...",
  "name": "München",
  "name_normalized": "muenchen",
  "entity_type_id": "...",
  "was_existing": true
}
```

**Response** (Entity erstellt):
```json
{
  "id": "e5f6g7h8-...",
  "name": "München",
  "name_normalized": "muenchen",
  "entity_type_id": "...",
  "was_existing": false
}
```

### Batch Entity Lookup

Für Performance-optimierte Batch-Operationen:

```python
service = EntityMatchingService(session)
result = await service.batch_get_or_create_entities(
    entity_type_slug="municipality",
    names=["München", "Berlin", "Hamburg"],
    country="DE"
)
# result: {"München": Entity, "Berlin": Entity, "Hamburg": Entity}
```

## Fehlerfälle

| Fehler | HTTP Code | Beschreibung |
|--------|-----------|--------------|
| Entity Type nicht gefunden | 400 | `entity_type_slug` existiert nicht |
| Name fehlt | 400 | `name` ist leer oder fehlt |

## Best Practices

1. **Immer `country` angeben** für korrekte Normalisierung
2. **`external_id` nutzen** für API-Imports (z.B. AGS-Code)
3. **Similarity-Threshold anpassen** je nach Use-Case:
   - Import aus bekannten Quellen: `1.0` (nur exakt)
   - KI-Extraktion: `0.85` (Fuzzy erlauben)
4. **Batch-Operationen nutzen** für Bulk-Imports
