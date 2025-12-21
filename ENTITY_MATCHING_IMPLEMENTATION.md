# Entity-Matching Implementierung - Checkliste

> Diese Datei dient als Kontext-Erhalt nach `compact`. Alle Schritte sind abhakbar.

## Zusammenfassung

Behebung von Entity-Matching-Inkonsistenzen und Race Conditions im automatischen KI-Import.

**Hauptprobleme:**
1. Inkonsistente Normalisierung über 3 Entity-Erstellungspfade
2. Race Conditions bei parallelen Crawl-Workern
3. N+1 Query-Problem bei Relations
4. Fehlende Similarity-Prüfung für Entities

---

## Aktueller API-Stand (geprüft am 21.12.2024)

### Normalisierungs-Inkonsistenz

| Datei | Zeile | Methode | Korrekt? |
|-------|-------|---------|----------|
| `entity_facet_service.py` | 36 | `normalize_entity_name(name, country="DE")` | ✅ Zentral |
| `entity_operations.py` | 117 | `unicodedata.normalize("NFKD", name.lower())` | ❌ Ad-hoc |
| `entities.py` | 271 | `unicodedata.normalize("NFKD", data.name.lower())` | ❌ Ad-hoc |
| `entities.py` | 693 | `unicodedata.normalize("NFKD", update_data["name"].lower())` | ❌ Ad-hoc |

### Zentrale Normalisierungsfunktion

**Datei:** `backend/app/utils/text.py`
```python
def normalize_entity_name(name: str, country: str = "DE") -> str:
    # Korrekte Normalisierung mit country-spezifischer Logik
```

Diese Funktion MUSS überall verwendet werden!

---

## Phase 0: Database Constraint

- [x] Prüfe auf existierende Duplikate:
  ```sql
  SELECT entity_type_id, name_normalized, COUNT(*) as count
  FROM entities WHERE deleted_at IS NULL
  GROUP BY entity_type_id, name_normalized
  HAVING COUNT(*) > 1;
  ```
- [x] Falls Duplikate: Merge-Script erstellen oder manuell bereinigen
- [x] Migration erstellen: `backend/alembic/versions/aj1234567926_add_entity_unique_constraint.py`
- [x] Constraint: `UNIQUE(entity_type_id, name_normalized) WHERE deleted_at IS NULL`
- [x] Migration testen
- [ ] Migration deployen

---

## Phase 1: Zentraler EntityMatchingService

- [x] Neue Datei erstellen: `backend/services/entity_matching_service.py`
- [x] Klasse `EntityMatchingService` implementieren mit:
  - [x] `get_or_create_entity()` - Zentrale Methode
  - [x] `_get_entity_type()` - EntityType laden
  - [x] `_find_by_external_id()` - External ID Match
  - [x] `_find_by_normalized_name()` - Normalized Name Match
  - [x] `_create_entity_safe()` - Race-Condition-Safe Creation
- [x] Konsistente Normalisierung via `app.utils.text.normalize_entity_name`
- [x] UPSERT Pattern für Race Conditions implementieren
- [x] Tests schreiben

---

## Phase 2: Multi-Entity-Extraction-Service migrieren

**Datei:** `backend/services/multi_entity_extraction_service.py`

- [x] Import `normalize_entity_name` von `app.utils.text`
- [x] `_batch_find_entities()` korrigieren:
  - [x] Normalisierung vor Lookup
  - [x] `Entity.name_normalized.in_(chunk)` statt `Entity.name.in_(chunk)`
  - [x] Mapping für Original-Namen beibehalten
- [x] Entity-Erstellung via EntityMatchingService
- [x] Tests aktualisieren

---

## Phase 3: Smart Query Entity-Operations migrieren

**Datei:** `backend/services/smart_query/entity_operations.py`

- [x] Import EntityMatchingService
- [x] `create_entity_from_command()` refactoren:
  - [x] Delegieren an `EntityMatchingService.get_or_create_entity()`
  - [x] Ad-hoc Normalisierung entfernt
- [x] Response-Format beibehalten für Rückwärtskompatibilität

---

## Phase 4: REST API Entities migrieren

**Datei:** `backend/app/api/v1/entities.py`

- [x] Import `normalize_entity_name` von `app.utils.text`
- [x] `create_entity()` Endpoint: Zentrale Normalisierung verwendet
- [x] `update_entity()` Endpoint: Zentrale Normalisierung verwendet
- [x] Response-Format beibehalten

---

## Phase 5: N+1 Query-Problem bei Relations beheben

**Datei:** `backend/services/multi_entity_extraction_service.py`

- [x] `process_extraction_result()` optimieren:
  - [x] Batch-Load für RelationTypes via `_batch_get_or_create_relation_types()`
  - [x] Batch-Query für existierende Relations via `_batch_find_existing_relations()`
  - [x] Set für schnelle Duplikat-Prüfung
- [x] Performance optimiert

---

## Phase 6: Entity-Facet-Service delegieren

**Datei:** `backend/services/entity_facet_service.py`

- [x] Import EntityMatchingService
- [x] `get_or_create_entity()` delegiert an EntityMatchingService
- [x] Neue Parameter: `country`, `similarity_threshold`
- [x] Rückwärtskompatibel

---

## Phase 7: Similarity-Matching

**Neue Datei:** `backend/app/utils/similarity.py`

- [x] `calculate_name_similarity()` implementieren
- [x] `_normalize_for_comparison()` implementieren
- [x] `find_similar_entities()` implementieren
- [x] `is_likely_duplicate()` implementieren
- [x] In EntityMatchingService integriert (Standard-Threshold: 0.85)

---

## Phase 8: Tests

**Neue Datei:** `backend/tests/test_services/test_entity_matching.py`

- [x] Test: Exakter Name-Match
- [x] Test: Normalisierter Name-Match (Umlaute)
- [x] Test: Race Condition Handling
- [x] Test: External ID Match
- [x] Test: Similarity Match
- [x] Test: Batch Entity Lookup

---

## Phase 9-10: Dokumentation

**Frontend-Hilfsbereich:**
- [x] `frontend/src/locales/de/help/features.json` - Neuer Abschnitt "entityMatching"
- [x] `frontend/src/locales/en/help/features.json` - Neuer Abschnitt "entityMatching"

**Inhalte:**
- [x] Entity-Matching-Verhalten erklärt
- [x] Automatische Deduplizierung dokumentiert
- [x] Beispiele für Matching-Verhalten

---

## Phase 11: iOS-App Kompatibilität geprüft

**Projekt:** `/Users/christian.voss/iosCrawler/CaeliCrawler`

**Ergebnis: ✅ Vollständig kompatibel**

- [x] Entity-Modelle unterstützen bereits alle Felder inkl. `nameNormalized`
- [x] API-Response-Format unverändert
- [x] Keine Breaking Changes

**Geprüfte Dateien:**
- [x] `Domain/Models/API/EntityModels.swift` - Keine Änderungen nötig
- [x] `Domain/Models/API/AssistantModels.swift` - Keine Änderungen nötig

---

## Abschluss

- [x] Alle Code-Änderungen abgeschlossen
- [x] Tests ausführen: `cd backend && pytest tests/test_services/test_entity_matching.py -v` ✅ 21/21 passed
- [x] Alembic Migration ausführen: `alembic upgrade head` ✅ Duplikate bereinigt (100 deaktiviert)
- [x] Code Review ✅ `deleted_at` → `is_active` in similarity.py und multi_entity_extraction_service.py korrigiert
- [ ] Staging-Deployment
- [ ] Smoke-Tests auf Staging
- [ ] Production-Deployment
- [ ] Monitoring für 24h

---

## Referenz-Dateien

### Backend (zu ändern)
```
backend/
├── alembic/versions/xxx_add_entity_unique_constraint.py  # NEU
├── services/
│   ├── entity_matching_service.py                        # NEU
│   ├── entity_facet_service.py                           # ÄNDERN
│   ├── multi_entity_extraction_service.py                # ÄNDERN
│   └── smart_query/
│       └── entity_operations.py                          # ÄNDERN
├── app/
│   ├── api/v1/entities.py                                # ÄNDERN
│   └── utils/similarity.py                               # NEU
└── tests/test_services/
    └── test_entity_matching.py                           # NEU
```

### Dokumentation (zu aktualisieren)
```
docs/
├── API_REFERENCE.md
└── api/
    ├── DATA.md
    └── README.md

frontend/src/locales/
├── de/help/features.json
└── en/help/features.json
```

### iOS (zu prüfen)
```
/Users/christian.voss/iosCrawler/CaeliCrawler/
└── Domain/
    ├── Models/API/EntityModels.swift
    └── Repositories/EntityRepository.swift
```

---

## Kontext für Claude nach Compact

Bei Wiederaufnahme der Arbeit:
1. Diese Datei lesen
2. Plan-Datei lesen: `/Users/christian.voss/.claude/plans/playful-bubbling-diffie.md`
3. Zuletzt bearbeitete Phase identifizieren (abhaken!)
4. Weiterarbeiten

**Haupt-Audit-Ergebnis:**
Entity-Erstellung erfolgt über 3 verschiedene Pfade (Crawling, Smart Query, REST API) mit unterschiedlichen Normalisierungsmethoden. Dies führt zu Duplikaten. Lösung: Zentraler EntityMatchingService mit konsistenter Normalisierung und Race-Condition-Safety.
