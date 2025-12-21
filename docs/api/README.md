# CaeliCrawler API Reference

Vollstaendige technische Dokumentation aller API-Endpunkte.

**Base URL:** `http://localhost:8000/api`

**Interaktive Dokumentation:** `http://localhost:8000/docs` (Swagger UI)

> **Vollstaendige Referenz:** Fuer die komplette API-Dokumentation siehe [API_REFERENCE.md](../API_REFERENCE.md).
> Diese modulare Struktur bietet eine uebersichtlichere Navigation.

---

## Dokumentationsstruktur

Die API-Dokumentation ist in mehrere thematische Dateien aufgeteilt:

| Datei | Beschreibung |
|-------|--------------|
| [AUTH.md](./AUTH.md) | Authentifizierung & Benutzerverwaltung |
| [ADMIN.md](./ADMIN.md) | Admin-Endpunkte (Kategorien, Datenquellen, Crawler, Locations) |
| [NOTIFICATIONS.md](./NOTIFICATIONS.md) | Benachrichtigungssystem (E-Mail, Push, Webhooks) |
| [DATA.md](./DATA.md) | Public Data API, Dokumente, Export |
| [ENTITIES.md](./ENTITIES.md) | Entity-Facet System |
| [ANALYSIS.md](./ANALYSIS.md) | Entity-Analyse, Reports, Statistiken |
| [DASHBOARD.md](./DASHBOARD.md) | Dashboard-Statistiken, Activity, Insights, Charts |
| [FAVORITES.md](./FAVORITES.md) | Favoriten-Verwaltung |
| [ATTACHMENTS.md](./ATTACHMENTS.md) | Entity Attachments mit KI-Analyse |
| [ENRICHMENT.md](./ENRICHMENT.md) | Entity Data Enrichment |
| [ASSISTANT.md](./ASSISTANT.md) | KI-Assistant (Chat, Wizards, Reminders) |
| [SMART_QUERY.md](./SMART_QUERY.md) | Smart Query & Analyse |
| [PYSIS.md](./PYSIS.md) | PySis Integration |
| [SYSTEM.md](./SYSTEM.md) | System & Health, Konfiguration |

---

## Schnellstart

### Authentifizierung

Alle geschuetzten Endpoints erfordern einen gueltigen Bearer-Token im Authorization-Header:

```http
Authorization: Bearer <your-jwt-token>
```

Token erhalten via:
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

Siehe [AUTH.md](./AUTH.md) fuer Details.

---

## API Bereiche

### Authentifizierung & Benutzer
- **Login/Logout** - JWT-basierte Authentifizierung
- **Benutzerverwaltung** - CRUD fuer Benutzer (Admin)
- **Passwort aendern** - Selbstverwaltung

### Admin API
- **Kategorien** - Analysethemen verwalten
- **Datenquellen** - Quellen fuer Crawler konfigurieren
- **Crawler & Jobs** - Crawl-Jobs starten und ueberwachen
- **KI-Tasks** - Dokumentenverarbeitung
- **Locations** - Standorte verwalten
- **Audit Logging** - Aenderungsverlauf
- **Versionierung** - Versionierung von Entities

### Public API v1
- **Data API** - Dokumente, Extractions, Crawl-History
- **Export** - Datenexport (JSON, CSV, Excel)

### Analysis API
- **Statistiken** - Gesamtuebersicht Entity-Facet-System
- **Entity Reports** - Detaillierte Analyse-Reports
- **Templates** - Analyse-Templates konfigurieren

### Entity-Facet System
- **Entities** - Kern-Entitaeten (Gemeinden, Organisationen, etc.)
- **Entity Types** - Entity-Typen definieren
- **Facet Types** - Facet-Typen definieren
- **Facet Values** - Werte zu Entities hinzufuegen
- **Relations** - Beziehungen zwischen Entities

### Entity Attachments
- **Upload** - Dateien zu Entities hochladen
- **Thumbnails** - Vorschaubilder fuer Bilder
- **KI-Analyse** - Bilder/PDFs analysieren
- **Facet-Vorschlaege** - Erkannte Daten als Facets uebernehmen

### KI-Assistant
- **Chat** - Natuerlichsprachliche Interaktion
- **Streaming** - Server-Sent Events fuer Echtzeit-Antworten
- **Batch Operations** - Massenoperationen mit Vorschau
- **Wizards** - Gefuehrte Workflows
- **Reminders** - Erinnerungen erstellen und verwalten

### Smart Query
- **Natural Language Queries** - Datenabfragen in natuerlicher Sprache
- **Write Operations** - Datenmanipulation ueber Sprache

---

## Allgemeine Konventionen

### HTTP Methoden
| Methode | Verwendung |
|---------|------------|
| GET | Daten abrufen |
| POST | Daten erstellen |
| PUT | Daten vollstaendig aktualisieren |
| PATCH | Daten teilweise aktualisieren |
| DELETE | Daten loeschen |

### Paginierung
Endpoints mit Listen unterstuetzen Paginierung:
```
?page=1&page_size=20
```

### Sortierung
```
?sort_by=created_at&sort_order=desc
```

### Filterung
```
?status=active&entity_type=municipality
```

---

## Fehler-Responses

Alle API-Fehler folgen einem einheitlichen Format:

```json
{
  "detail": "Fehlerbeschreibung"
}
```

Oder bei Validierungsfehlern:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### HTTP Status Codes

| Code | Bedeutung |
|------|-----------|
| 200 | Erfolg |
| 201 | Erstellt |
| 204 | Kein Inhalt (bei DELETE) |
| 400 | Ungueltige Anfrage |
| 401 | Nicht authentifiziert |
| 403 | Zugriff verweigert |
| 404 | Nicht gefunden |
| 409 | Konflikt (z.B. Duplikat) |
| 422 | Validierungsfehler |
| 429 | Rate Limit ueberschritten |
| 500 | Serverfehler |

---

## Rate Limiting

Die API implementiert Rate Limiting zum Schutz vor Ueberlastung:

- **Standard:** 100 Anfragen pro Minute pro IP
- **Authentifiziert:** 500 Anfragen pro Minute pro Benutzer
- **KI-Endpoints:** 20 Anfragen pro Minute

Bei Ueberschreitung:
```
HTTP 429 Too Many Requests
Retry-After: 60
```

---

## Sicherheit

### CORS
CORS ist fuer konfigurierte Origins aktiviert.

### HTTPS
In Produktion sollte HTTPS verwendet werden.

### Token-Sicherheit
- Access Tokens haben eine begrenzte Lebensdauer
- Refresh Tokens ermoeglichen Token-Erneuerung
- Tokens koennen invalidiert werden (Logout)

---

## Aenderungshistorie

| Version | Datum | Aenderungen |
|---------|-------|-------------|
| 1.0.0 | 2024-12-20 | Initiale Dokumentation |
| 1.1.0 | 2024-12-20 | Entity Attachments mit KI-Analyse |
| 1.2.0 | 2024-12-20 | Assistant: Save to Entity Attachments |
| 2.0.0 | 2025-12-20 | Vollstaendige Modularisierung der API-Dokumentation |
