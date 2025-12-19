# Entity-Bereinigung und Normalisierung (2024-12-19)

## Übersicht

Dieses Dokument beschreibt die durchgeführte Bereinigung von Duplikaten und die
implementierten Maßnahmen zur Vermeidung zukünftiger Probleme.

## Das Problem

### Symptome
- 13.752 DE-Gemeinden, aber nur 10.723 Datenquellen
- 3.614 Gemeinden scheinbar ohne Datenquelle
- UK-Daten nur teilweise migriert (444 statt ~1.900)

### Ursache: Inkonsistente Normalisierung

Es gab **8 verschiedene `normalize_name` Funktionen** im Code, die unterschiedlich arbeiteten:

| Datei | Methode | Beispiel "Köln" |
|-------|---------|-----------------|
| `entity_facet_service.py` | NFD + Bug (`{"ae":"ae"}`) | `"koln"` |
| `import_missing_german_municipalities.py` | NFKD only | `"köln"` |
| `import_wikidata_gemeinden.py` | Umlaut replacement | `"koeln"` |
| `app/schemas/entity.py` | Umlaut replacement | `"koeln"` |

**Konsequenz**: Gleicher Gemeindename führte zu unterschiedlichen `name_normalized` Werten
→ Duplikate wurden erstellt, weil keine Matches gefunden wurden.

## Durchgeführte Bereinigungen

### 1. DE-Duplikate (2.723 Stück)

```sql
-- Mapping erstellen: Duplikat → Kanonische Entity (mit AGS bevorzugt)
CREATE TABLE entity_cleanup_mapping AS
WITH ranked AS (
  SELECT id, name,
    LOWER(REGEXP_REPLACE(TRANSLATE(name, 'äöüÄÖÜß', 'aouAOUs'), '[^a-zA-Z0-9]', '', 'g')) as uniform_name,
    CASE WHEN external_id IS NOT NULL THEN 1 ELSE 0 END as has_ags,
    ROW_NUMBER() OVER (PARTITION BY uniform_name ORDER BY has_ags DESC, id) as rn
  FROM entities WHERE country = 'DE'
)
SELECT d.id as duplicate_id, c.id as canonical_id
FROM ranked d JOIN ranked c ON d.uniform_name = c.uniform_name AND c.rn = 1
WHERE d.rn > 1;

-- DataSources umverknüpfen
UPDATE data_sources SET entity_id = em.canonical_id
FROM entity_cleanup_mapping em WHERE data_sources.entity_id = em.duplicate_id;

-- Duplikate löschen
DELETE FROM entities WHERE id IN (SELECT duplicate_id FROM entity_cleanup_mapping);
```

**Ergebnis DE:**
| Metrik | Vorher | Nachher |
|--------|--------|---------|
| Gemeinden | 13.752 | 10.582 |
| Mit Datenquelle | 10.138 | 9.688 |
| Duplikate | 2.723 | 0 |

### 2. UK-Migration (Locations → Entities)

Die UK-Daten waren noch im alten `locations`-System:

```sql
-- UK Locations zu Entities migrieren
INSERT INTO entities (id, entity_type_id, name, name_normalized, ...)
SELECT gen_random_uuid(), ..., l.name, LOWER(REGEXP_REPLACE(l.name, '[^a-zA-Z0-9]', '', 'g')), ...
FROM locations l WHERE l.country = 'GB'
AND NOT EXISTS (SELECT 1 FROM entities e WHERE e.name_normalized = l.name_normalized AND e.country = 'GB');
```

### 3. UK-Duplikate (175 Stück)

Nach der Migration wurden auch UK-Duplikate bereinigt (gleiche Methode wie DE).

**Ergebnis UK:**
| Metrik | Vorher | Nachher |
|--------|--------|---------|
| Entities | 444 | 1.898 |
| Mit Datenquelle | - | 445 |
| Duplikate | 175 | 0 |

## Finale Statistik

| Land | Entities | Mit Datenquelle | Ohne Datenquelle |
|------|----------|-----------------|------------------|
| DE | 10.582 | 9.688 | 894 |
| GB | 1.898 | 445 | 1.453 |

**Hinweis:** Entities ohne Datenquelle sind normal - das sind Gemeinden ohne
bekannte Website oder OParl-API.

## Präventive Maßnahmen

### 1. Zentrale Normalisierungsfunktion

**Neue Datei:** `backend/app/utils/text.py`

```python
def normalize_entity_name(name: str, country: str = "DE") -> str:
    """
    Zentrale Normalisierung für alle Entity-Namen.
    IMMER diese Funktion verwenden - nie eigene Normalisierung schreiben!
    """
    result = name.lower()

    # Länder-spezifische Ersetzungen
    if country == "DE":
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

### 2. Angepasste Services und Scripts

Diese Dateien verwenden jetzt die zentrale Funktion:
- `services/entity_facet_service.py`
- `scripts/import_missing_german_municipalities.py`

### 3. Cleanup-Script für Zukunft

```bash
# Prüfen auf Duplikate (dry-run)
docker compose exec backend python -m scripts.cleanup_duplicate_municipalities --dry-run

# Bereinigen
docker compose exec backend python -m scripts.cleanup_duplicate_municipalities
```

## DataSource-Verknüpfungslogik

### Wann entity_id gesetzt sein sollte

| DataSource-Typ | entity_id | Beispiel |
|----------------|-----------|----------|
| Kommunale Website | ✅ Ja | `Stadt Köln - Website` |
| OParl-API | ✅ Ja | `Stadt Köln - Ratsinformation` |
| Nationale Quelle | ❌ Nein | `Bundestag - Kleine Anfragen` |
| Allgemeine API | ❌ Nein | `FragDenStaat - Windkraft` |

### SQL zur Prüfung

```sql
-- Prüfen auf Duplikate
SELECT COUNT(*) FROM (
  SELECT LOWER(REGEXP_REPLACE(TRANSLATE(name, 'äöüÄÖÜß', 'aouAOUs'), '[^a-zA-Z0-9]', '', 'g'))
  FROM entities WHERE country = 'DE'
  GROUP BY 1 HAVING COUNT(*) > 1
) sub;

-- Statistik nach Land
SELECT
  e.country,
  COUNT(DISTINCT e.id) as entities,
  COUNT(DISTINCT ds.entity_id) as mit_datenquelle
FROM entities e
LEFT JOIN data_sources ds ON ds.entity_id = e.id
WHERE e.entity_type_id = (SELECT id FROM entity_types WHERE slug = 'municipality')
GROUP BY e.country;
```

## Regeln für zukünftige Entwicklung

1. **NIE** eigene `normalize_name` Funktionen schreiben
2. **IMMER** `from app.utils.text import normalize_entity_name` verwenden
3. **BEI NEUEN IMPORTS**: Prüfen ob Entity bereits existiert via `name_normalized`
4. **NACH GROSSEN IMPORTS**: Duplikat-Check durchführen
5. **locations-Tabelle**: Ist deprecated, nur noch für Legacy-Kompatibilität
