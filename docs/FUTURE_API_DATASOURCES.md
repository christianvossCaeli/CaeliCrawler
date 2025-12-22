# Future Feature: APIs als DataSources

## Kontext
Aktuell werden APIs nur für einmalige Bulk-Imports genutzt. DataSources unterstützen nur:
- WEBSITE (HTML crawling)
- RSS (Feed parsing)
- OPARL_API (Ratsinformationssysteme)
- CUSTOM_API (generisch)

## Anforderung
APIs sollen als vollwertige DataSources fungieren, die regelmäßig abgefragt werden um Entities aktuell zu halten.

## Konzept

### 1. Neue SourceTypes
```python
class SourceType(str, enum.Enum):
    WEBSITE = "WEBSITE"
    OPARL_API = "OPARL_API"
    RSS = "RSS"
    CUSTOM_API = "CUSTOM_API"
    # NEU:
    REST_API = "REST_API"       # REST APIs (z.B. Caeli Auction)
    SPARQL_API = "SPARQL_API"   # SPARQL Endpoints (z.B. Wikidata)
    GRAPHQL_API = "GRAPHQL_API" # GraphQL APIs
```

### 2. API-Response als "Dokument"
Jede API-Antwort wird wie ein Dokument behandelt:
- Content-Hash für Änderungserkennung
- Diff-Tracking zwischen Abfragen
- Event-Auslösung bei Änderungen (Entity aktualisieren, Notification)

### 3. DataSource Konfiguration für APIs
```python
class DataSource:
    # Existierend
    base_url: str
    crawl_config: Dict  # max_depth, patterns etc.

    # NEU für APIs:
    api_config: Dict = {
        "type": "rest|sparql|graphql",
        "auth_config": {...},
        "endpoint": "/api/v1/windparks",
        "method": "GET",
        "query": "SELECT ...",  # für SPARQL
        "field_mapping": {...},  # API-Felder → Entity-Felder
        "entity_type_slug": "windpark",
        "update_strategy": "merge|replace|append",
    }
```

### 4. Use Cases

#### A) Wikidata als DataSource für Gemeinden
- DataSource: `type=SPARQL_API, base_url=wikidata.org`
- Schedule: Wöchentlich
- Bei Änderung: Entity-Attribute aktualisieren (Einwohner, Fläche)

#### B) Caeli Auction als DataSource für Windparks
- DataSource: `type=REST_API, base_url=auction.caeli-wind.de`
- Schedule: Täglich
- Bei Änderung: Neue Windparks erstellen, Status aktualisieren

#### C) Einzelne API-Responses tracken
- Nicht nur die Liste aller Windparks, sondern auch:
- `/api/windpark/{id}` → Einzelne Entity-Details
- Änderungen an einzelnen Einträgen erkennen

### 5. Vorteile
1. **Konsistenz**: Entities bleiben aktuell
2. **Automatisierung**: Keine manuellen Re-Imports
3. **Tracking**: Änderungshistorie für API-Daten
4. **Skalierbarkeit**: Beliebig viele API-Quellen

### 6. Integration mit bestehendem System
- Celery Beat für Scheduling (wie Website-Crawls)
- Änderungen triggern Notifications
- AI kann Änderungen analysieren und Facets extrahieren

## Implementierungsschritte
1. [ ] SourceType erweitern (REST_API, SPARQL_API)
2. [ ] api_config Feld zu DataSource hinzufügen
3. [ ] API-Crawler Worker erstellen (analog zu Website-Crawler)
4. [ ] Diff-Tracking für API-Responses implementieren
5. [ ] Entity-Update-Logic bei API-Änderungen
6. [ ] UI für API-DataSource Konfiguration

## Notizen
- Erstellt: 2024-12-22
- Status: Konzept/Future Feature
- Priorität: Mittel-Hoch (wichtig für Skalierung)
