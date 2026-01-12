# Smart Query API Audit Report (2026-01-05)

## Zusammenfassung

Umfassendes Audit der Dokumentation (docs/api/SMART_QUERY.md) gegen den Backend-Code durchgeführt.

Analysierte Quellen:
- backend/services/smart_query/operations/*.py (10 Dateien)
- backend/services/smart_query/write_executor.py
- backend/services/smart_query/interpreters/*.py

## Gefundene @register_operation Dekoratoren

Total: 24 registrierte Operationen

### Operations Registry (alphabetisch):
1. add_history_point (facet_ops.py:325)
2. analyze_pysis (pysis_ops.py:22)
3. assign_facet_type (facet_ops.py:155)
4. assign_facet_types (category_ops.py:22)
5. batch_delete (batch_ops.py:182)
6. batch_operation (batch_ops.py:21)
7. create_custom_summary (summary_ops.py:18)
8. create_facet_type (facet_ops.py:25)
9. create_relation_type (category_ops.py:281)
10. delete_entity (entity_ops.py:99)
11. delete_facet (facet_ops.py:202)
12. discover_sources (discovery.py:29)
13. enrich_facets_from_pysis (pysis_ops.py:76)
14. export (export_ops.py:24)
15. fetch_and_create_from_api (api_import_ops.py:22)
16. get_history (export_ops.py:263)
17. link_category_entity_types (category_ops.py:144)
18. link_existing_category (category_ops.py:229)
19. push_to_pysis (pysis_ops.py:130)
20. update_crawl_schedule (schedule_ops.py:22)
21. update_entity (entity_ops.py:21)
22. undo (export_ops.py:210)

### Direct Handler Operationen (write_executor.py):
Folgende Operationen werden direkt in write_executor.py behandelt, NOT in operations registry:

23. combined (write_executor.py:370)
24. create_category_setup (write_executor.py:306)
25. create_entity (write_executor.py:241)
26. create_facet (write_executor.py:257)
27. create_relation (write_executor.py:271)
28. create_entity_type (write_executor.py:284)
29. start_crawl (write_executor.py:362)

## Diskrepanzen gefunden

### 1. KRITISCH: Fehlende create_facet Operation in Registry

**Status**: NICHT in operations registry registriert
**Dokumentation**: Zeile 113 - dokumentiert als Supported Operation
**Backend**: Wird direkt in write_executor.py behandelt (Zeile 257)

**Details**:
- Dokumentation verspricht `create_facet` Operation
- Code in write_executor.py:257-269 behandelt sie direkt
- Sie ist NICHT via @register_operation registriert
- Parameter: `facet_data` mit `facet_type`, Entity-Bezug, usw.

**Priorität**: KRITISCH - Architektur-Inkonsistenz

---

### 2. KRITISCH: Fehlende create_entity Operation in Registry

**Status**: NICHT in operations registry registriert
**Dokumentation**: Zeile 111 - dokumentiert als Supported Operation
**Backend**: Wird direkt in write_executor.py behandelt (Zeile 241)

**Details**:
- Dokumentation verspricht `create_entity` Operation
- Code in write_executor.py:241-255 behandelt sie direkt
- Sie ist NICHT via @register_operation registriert
- Parameter: `entity_type`, `entity_data`

**Priorität**: KRITISCH - Architektur-Inkonsistenz

---

### 3. KRITISCH: Fehlende create_relation Operation in Registry

**Status**: NICHT in operations registry registriert
**Dokumentation**: Zeile 116 - dokumentiert als Supported Operation
**Backend**: Wird direkt in write_executor.py behandelt (Zeile 271)

**Details**:
- Dokumentation verspricht `create_relation` Operation
- Code in write_executor.py:271-282 behandelt sie direkt
- Sie ist NICHT via @register_operation registriert
- Parameter: `relation_data`

**Priorität**: KRITISCH - Architektur-Inkonsistenz

---

### 4. KRITISCH: Fehlende create_entity_type Operation in Registry

**Status**: NICHT in operations registry registriert
**Dokumentation**: Zeile 112 - dokumentiert als Supported Operation
**Backend**: Wird direkt in write_executor.py behandelt (Zeile 284)

**Details**:
- Dokumentation verspricht `create_entity_type` Operation
- Code in write_executor.py:284-304 behandelt sie direkt
- Sie ist NICHT via @register_operation registriert
- Parameter: `entity_type_data`

**Priorität**: KRITISCH - Architektur-Inkonsistenz

---

### 5. KRITISCH: Fehlende create_category_setup Operation in Registry

**Status**: NICHT in operations registry registriert
**Dokumentation**: Zeile 117 - dokumentiert als Supported Operation
**Backend**: Wird direkt in write_executor.py behandelt (Zeile 306)

**Details**:
- Dokumentation verspricht `create_category_setup` Operation
- Code in write_executor.py:306-361 behandelt sie direkt
- Sie ist NICHT via @register_operation registriert
- Parameter: `category_setup_data`

**Priorität**: KRITISCH - Architektur-Inkonsistenz

---

### 6. KRITISCH: Fehlende start_crawl Operation in Registry

**Status**: NICHT in operations registry registriert
**Dokumentation**: Zeile 118 - dokumentiert als Supported Operation
**Backend**: Wird direkt in write_executor.py behandelt (Zeile 362)

**Details**:
- Dokumentation verspricht `start_crawl` Operation
- Code in write_executor.py:362-368 behandelt sie direkt
- Sie ist NICHT via @register_operation registriert
- Parameter: `crawl_command_data`

**Priorität**: KRITISCH - Architektur-Inkonsistenz

---

### 7. KRITISCH: Fehlende combined Operation in Registry

**Status**: NICHT in operations registry registriert
**Dokumentation**: Zeile 129 - dokumentiert als Supported Operation
**Backend**: Wird direkt in write_executor.py behandelt (Zeile 370)

**Details**:
- Dokumentation verspricht `combined` Operation
- Code in write_executor.py:370-377 (und 417-569) behandelt sie direkt
- Sie ist NICHT via @register_operation registriert
- Parameter: `operations` oder `combined_operations` Liste

**Priorität**: KRITISCH - Architektur-Inkonsistenz

---

### 8. HOCH: Dokumentation fehlt für assign_facet_type

**Status**: Nicht dokumentiert
**Backend**: Registriert als @register_operation("assign_facet_type")
**Datei**: backend/services/smart_query/operations/facet_ops.py:155

**Details**:
- Operation exists im Code (facet_ops.py:155-199)
- Dokumentation erwähnt nur `assign_facet_types` (Plural)
- Diese Operation (Singular) ist NICHT dokumentiert
- Parameter: `assign_facet_type_data` mit `facet_type_slug`, `target_entity_type_slugs`

**Priorität**: HOCH - Fehlende Dokumentation einer existierenden Operation

---

### 9. HOCH: Dokumentation und Code stimmen nicht überein - assign_facet_types

**Dokumentation**: Zeile 135 - "assign_facet_types"
**Backend**: Zwei verschiedene Operationen!

**Details**:
- facet_ops.py:155 - `assign_facet_type` (Singular) - assigniert einen Facet-Typ
- category_ops.py:22 - `assign_facet_types` (Plural) - assigniert multiple Facet-Typen

**Dokumentation erwähnt nur**:
- "assign_facet_types" (Zeile 701-770)
- Unterstützt 2 Formate (ein Facet zu vielen Entity-Types, oder viele Facets zu einem Entity-Type)

**Code hat zwei UNTERSCHIEDLICHE Operations**:
1. `assign_facet_type` (Singular): Ein Facet zu mehreren Entity-Types
2. `assign_facet_types` (Plural): Wie dokumentiert

**Priorität**: HOCH - Verwirrende Dokumentation, zwei unterschiedliche Operations

---

### 10. MITTEL: Undokumentierte Operation: assign_facet_types in category_ops.py

**Status**: Registriert, aber mit unterschiedlichem Intent
**Backend**: backend/services/smart_query/operations/category_ops.py:22
**Dokumentation**: Zeile 701-770 (aber unklar ob dies die richtige Operation ist)

**Details**:
- Zwei Operations mit ähnlichen Namen: singular vs plural
- Dokumentation ist mehrdeutig
- Code-Implementierung unterstützt zwei verschiedene Formate

**Priorität**: MITTEL - Benötigt Klarstellung

---

## Parameter-Genauigkeit

### create_facet Dokumentation vs Code

**Dokumentation** (Zeile 113):
- Generisch: "Facet hinzufügen (Pain Point, Positive Signal, Kontakt)"
- Zeigt keine genauen Parameter

**Code** (write_executor.py:257-269):
- Erwartet: `facet_data` dict mit:
  - `facet_type`: String (Type des Facets)
  - Weitere Entity-Bezüge

**Priorität**: MITTEL - Parameter nicht detailliert dokumentiert

---

### create_entity Dokumentation vs Code

**Dokumentation** (Zeile 111):
- Generisch: "Entity erstellen (Person, Gemeinde, Organisation, Event)"

**Code** (write_executor.py:241-255):
- Erwartet: `entity_type` (default "territorial_entity"), `entity_data`

**Priorität**: MITTEL - Parameter nicht detailliert dokumentiert

---

### create_relation Dokumentation vs Code

**Dokumentation** (Zeile 116):
- Generisch: "Verknüpfung zwischen Entities erstellen"

**Code** (write_executor.py:271-282):
- Erwartet: `relation_data` dict

**Priorität**: MITTEL - Parameter nicht detailliert dokumentiert

---

## Korrekt dokumentierte Operationen

Folgende Operationen sind gut dokumentiert UND im Code registriert:

- analyze_pysis (Zeile 120)
- batch_delete (Zeile 134)
- batch_operation (Zeile 119)
- create_custom_summary (Zeile 131) - Zeile 359-472
- delete_facet (Zeile 125)
- discover_sources (Zeile 132) - Zeile 476-544
- enrich_facets_from_pysis (Zeile 121)
- export (Zeile 126)
- fetch_and_create_from_api (Zeile 133) - Zeile 1251-1323
- get_history (Zeile 128)
- link_category_entity_types (Zeile 136)
- link_existing_category (Zeile 137)
- push_to_pysis (Zeile 122)
- update_crawl_schedule (Zeile 130)
- update_entity (Zeile 123)
- delete_entity (Zeile 124)
- undo (Zeile 127)
- create_facet_type (Zeile 114)
- create_relation_type (Zeile 138)
- add_history_point (Zeile 139)

---

## Architektur-Problem: Mixed Handler Patterns

**Problem**: Das System nutzt zwei unterschiedliche Handler-Patterns:

1. **Operations Registry Pattern** (Command Pattern):
   - 22 Operationen mit @register_operation Dekorator
   - Zentral in operations/base.py registriert
   - Ermöglicht bessere Testbarkeit und Modularität

2. **Direct Handler Pattern** (in write_executor.py):
   - 7 Core-Operationen direkt behandelt:
     - create_entity, create_facet, create_relation, create_entity_type
     - create_category_setup, start_crawl, combined

**Folge**: 
- Manche Operationen sind leichter zu testen (Registry-basiert)
- Andere Operationen sind schwerer zu testen (Direct Handler)
- Dokumentation ist mehrdeutig über Handler-Location

**Empfehlung**: Alle 7 Core-Operationen sollten entweder:
1. In operations/ als @register_operation registriert werden ODER
2. Klar dokumentiert werden als "Direct Handler Operationen"

---

## Summary Table: Alle 29 Operationen

| # | Operation | Dokumentiert | Im Code | Registriert | Priorität |
|----|-----------|--------------|---------|-------------|-----------|
| 1 | add_history_point | JA (139) | JA | JA | OK |
| 2 | analyze_pysis | JA (120) | JA | JA | OK |
| 3 | assign_facet_type | NEIN | JA | JA | HOCH |
| 4 | assign_facet_types | JA (135) | JA (2x) | JA | HOCH |
| 5 | batch_delete | JA (134) | JA | JA | OK |
| 6 | batch_operation | JA (119) | JA | JA | OK |
| 7 | combined | JA (129) | JA | NEIN | KRITISCH |
| 8 | create_category_setup | JA (117) | JA | NEIN | KRITISCH |
| 9 | create_custom_summary | JA (131) | JA | JA | OK |
| 10 | create_entity | JA (111) | JA | NEIN | KRITISCH |
| 11 | create_entity_type | JA (112) | JA | NEIN | KRITISCH |
| 12 | create_facet | JA (113) | JA | NEIN | KRITISCH |
| 13 | create_facet_type | JA (114) | JA | JA | OK |
| 14 | create_relation | JA (116) | JA | NEIN | KRITISCH |
| 15 | create_relation_type | JA (138) | JA | JA | OK |
| 16 | delete_entity | JA (124) | JA | JA | OK |
| 17 | delete_facet | JA (125) | JA | JA | OK |
| 18 | discover_sources | JA (132) | JA | JA | OK |
| 19 | enrich_facets_from_pysis | JA (121) | JA | JA | OK |
| 20 | export | JA (126) | JA | JA | OK |
| 21 | fetch_and_create_from_api | JA (133) | JA | JA | OK |
| 22 | get_history | JA (128) | JA | JA | OK |
| 23 | link_category_entity_types | JA (136) | JA | JA | OK |
| 24 | link_existing_category | JA (137) | JA | JA | OK |
| 25 | push_to_pysis | JA (122) | JA | JA | OK |
| 26 | start_crawl | JA (118) | JA | NEIN | KRITISCH |
| 27 | update_crawl_schedule | JA (130) | JA | JA | OK |
| 28 | update_entity | JA (123) | JA | JA | OK |
| 29 | undo | JA (127) | JA | JA | OK |

