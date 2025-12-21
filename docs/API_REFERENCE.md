# CaeliCrawler API Reference

Vollstaendige technische Dokumentation aller API-Endpunkte.

**Base URL:** `http://localhost:8000/api`

**Interaktive Dokumentation:** `http://localhost:8000/docs` (Swagger UI)

---

## Modulare Dokumentation

Die API-Dokumentation wurde in thematische Module aufgeteilt fuer bessere Uebersichtlichkeit und Wartbarkeit.

| Modul | Datei | Beschreibung |
|-------|-------|--------------|
| Authentifizierung | [AUTH.md](./api/AUTH.md) | Login, Logout, Benutzerverwaltung, Passwortaenderung |
| Admin | [ADMIN.md](./api/ADMIN.md) | Kategorien, Datenquellen, Crawler, Locations, Audit, Versionierung |
| Benachrichtigungen | [NOTIFICATIONS.md](./api/NOTIFICATIONS.md) | E-Mail, Webhooks, In-App-Benachrichtigungen, Regeln |
| Data API | [DATA.md](./api/DATA.md) | Extraktionen, Dokumente, Gemeinden, Reports, Export |
| Entity-Facet System | [ENTITIES.md](./api/ENTITIES.md) | Entity Types, Entities, Facet Types, Facet Values, Relations |
| Favorites | [FAVORITES.md](./api/FAVORITES.md) | Entity-Favoriten verwalten |
| Attachments | [ATTACHMENTS.md](./api/ATTACHMENTS.md) | Datei-Uploads, Thumbnails, KI-Analyse |
| Enrichment | [ENRICHMENT.md](./api/ENRICHMENT.md) | KI-basierte Facet-Anreicherung |
| KI-Assistant | [ASSISTANT.md](./api/ASSISTANT.md) | Chat, Streaming, Batch-Operationen, Wizards, Reminders |
| Smart Query | [SMART_QUERY.md](./api/SMART_QUERY.md) | Natuerlichsprachliche Abfragen und Schreiboperationen |
| Dashboard | [DASHBOARD.md](./api/DASHBOARD.md) | Dashboard-Widgets, Statistiken, Activity Feed, Insights |
| PySis | [PYSIS.md](./api/PYSIS.md) | PySis-Integration, Prozesse, Felder |
| AI Discovery | [AI_DISCOVERY.md](./api/AI_DISCOVERY.md) | KI-gesteuerte Datenquellen-Suche |
| External APIs | [EXTERNAL_APIS.md](./api/EXTERNAL_APIS.md) | Externe API-Konfiguration und Synchronisation |
| System | [SYSTEM.md](./api/SYSTEM.md) | Health, Konfiguration, Sicherheit, Rate Limiting |

**Vollstaendige Uebersicht:** [docs/api/README.md](./api/README.md)

---

## Schnellreferenz - Alle Endpoints

### Authentifizierung (`/auth`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| POST | `/auth/login` | Anmelden |
| POST | `/auth/logout` | Abmelden |
| GET | `/auth/me` | Eigenes Profil abrufen |
| POST | `/auth/change-password` | Passwort aendern |
| GET | `/admin/users` | Benutzer auflisten |
| POST | `/admin/users` | Benutzer erstellen |
| PUT | `/admin/users/{id}` | Benutzer aktualisieren |
| DELETE | `/admin/users/{id}` | Benutzer loeschen |

### Admin - Kategorien (`/admin/categories`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/admin/categories` | Alle Kategorien |
| POST | `/admin/categories` | Kategorie erstellen |
| GET | `/admin/categories/{id}` | Kategorie abrufen |
| PUT | `/admin/categories/{id}` | Kategorie aktualisieren |
| DELETE | `/admin/categories/{id}` | Kategorie loeschen |
| GET | `/admin/categories/{id}/stats` | Kategorie-Statistiken |
| POST | `/admin/categories/preview-ai-setup` | KI-Setup Vorschau |
| POST | `/admin/categories/{id}/assign-sources-by-tags` | Quellen per Tags zuordnen |

### Admin - Datenquellen (`/admin/sources`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/admin/sources` | Alle Quellen |
| POST | `/admin/sources` | Quelle erstellen |
| POST | `/admin/sources/bulk-import` | Massenimport |
| GET | `/admin/sources/{id}` | Quelle abrufen |
| PUT | `/admin/sources/{id}` | Quelle aktualisieren |
| DELETE | `/admin/sources/{id}` | Quelle loeschen |
| POST | `/admin/sources/{id}/reset` | Quelle zuruecksetzen |
| GET | `/admin/sources/meta/counts` | Quellen-Zaehler |
| GET | `/admin/sources/meta/tags` | Alle Tags |
| GET | `/admin/sources/by-tags` | Quellen nach Tags |

### Admin - API Import (`/admin/api-import`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/admin/api-import/templates` | Import-Templates |
| GET | `/admin/api-import/templates/{id}` | Template-Details |
| POST | `/admin/api-import/preview` | Import-Vorschau |
| POST | `/admin/api-import/execute` | Import ausfuehren |

### Admin - KI-Discovery (`/admin/ai-discovery`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/admin/ai-discovery/examples` | Beispiel-Prompts |
| POST | `/admin/ai-discovery/discover` | Quellen suchen |
| POST | `/admin/ai-discovery/import` | Quellen importieren |

### Admin - External APIs (`/admin/external-apis`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/admin/external-apis` | Alle API-Konfigurationen |
| POST | `/admin/external-apis` | Konfiguration erstellen |
| GET | `/admin/external-apis/{id}` | Konfiguration abrufen |
| PATCH | `/admin/external-apis/{id}` | Konfiguration aktualisieren |
| DELETE | `/admin/external-apis/{id}` | Konfiguration loeschen |
| POST | `/admin/external-apis/{id}/sync` | Sync starten |
| POST | `/admin/external-apis/{id}/test` | Verbindung testen |
| GET | `/admin/external-apis/{id}/stats` | Sync-Statistiken |
| GET | `/admin/external-apis/{id}/records` | Sync-Records |
| GET | `/admin/external-apis/{id}/records/{rid}` | Record-Details |
| DELETE | `/admin/external-apis/{id}/records/{rid}` | Record loeschen |
| GET | `/admin/external-apis/types/available` | Verfuegbare API-Typen |

### Admin - Crawler (`/admin/crawler`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| POST | `/admin/crawler/start` | Crawl starten |
| GET | `/admin/crawler/status` | Status abrufen |
| GET | `/admin/crawler/stats` | Statistiken |
| GET | `/admin/crawler/running` | Laufende Jobs |
| GET | `/admin/crawler/jobs` | Job-Historie |
| GET | `/admin/crawler/jobs/{id}` | Job-Details |
| POST | `/admin/crawler/jobs/{id}/cancel` | Job abbrechen |
| GET | `/admin/crawler/ai-tasks` | KI-Tasks |
| POST | `/admin/crawler/documents/{id}/process` | Dokument verarbeiten |
| POST | `/admin/crawler/documents/{id}/analyze` | Dokument analysieren |

### Admin - Locations (`/admin/locations`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/admin/locations` | Alle Locations |
| POST | `/admin/locations` | Location erstellen |
| GET | `/admin/locations/{id}` | Location abrufen |
| PUT | `/admin/locations/{id}` | Location aktualisieren |
| DELETE | `/admin/locations/{id}` | Location loeschen |
| GET | `/admin/locations/countries` | Laender |
| GET | `/admin/locations/states` | Bundeslaender |

### Admin - Audit & Versionierung

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/admin/audit` | Audit-Log |
| GET | `/admin/audit/stats` | Audit-Statistiken |
| GET | `/admin/versions/{type}/{id}` | Versionshistorie |

### Admin - Benachrichtigungen (`/admin/notifications`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/admin/notifications/email-addresses` | E-Mail-Adressen |
| GET | `/admin/notifications/rules` | Regeln |
| POST | `/admin/notifications/rules` | Regel erstellen |
| GET | `/admin/notifications/notifications` | Benachrichtigungen |
| GET | `/admin/notifications/notifications/unread-count` | Ungelesene Anzahl |
| GET | `/admin/notifications/device-tokens` | Device Tokens |
| POST | `/admin/notifications/device-token` | Device Token hinzufuegen |
| DELETE | `/admin/notifications/device-token/{token}` | Device Token loeschen |
| POST | `/admin/notifications/device-token/{token}/deactivate` | Device Token deaktivieren |
| GET | `/admin/notifications/preferences` | Praeferenzen abrufen |
| PUT | `/admin/notifications/preferences` | Praeferenzen aktualisieren |
| GET | `/admin/notifications/event-types` | Event-Typen |
| GET | `/admin/notifications/channels` | Kanaele |

### Dashboard (`/v1/dashboard`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/dashboard/preferences` | Widget-Praeferenzen abrufen |
| PUT | `/v1/dashboard/preferences` | Widget-Praeferenzen aktualisieren |
| GET | `/v1/dashboard/stats` | Dashboard-Statistiken |
| GET | `/v1/dashboard/activity` | Activity Feed |
| GET | `/v1/dashboard/insights` | Benutzer-Insights |
| GET | `/v1/dashboard/charts/{type}` | Chart-Daten |

### Data API (`/v1/data`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/data` | Extraktionen |
| GET | `/v1/data/stats` | Statistiken |
| GET | `/v1/data/documents` | Dokumente |
| GET | `/v1/data/documents/{id}` | Dokument-Details |
| GET | `/v1/data/search` | Volltextsuche |
| GET | `/v1/data/municipalities` | Gemeinden |
| GET | `/v1/data/municipalities/{name}/report` | Gemeinde-Report |

### Export (`/v1/export`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/export/json` | JSON-Export |
| GET | `/v1/export/csv` | CSV-Export |
| POST | `/v1/export/async` | Async Export starten |
| GET | `/v1/export/async/{id}` | Export-Status |
| GET | `/v1/export/async/{id}/download` | Export herunterladen |

### Entity Types (`/v1/entity-types`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/entity-types` | Alle Entity-Typen |
| POST | `/v1/entity-types` | Entity-Typ erstellen |
| GET | `/v1/entity-types/{id}` | Entity-Typ abrufen |
| PUT | `/v1/entity-types/{id}` | Entity-Typ aktualisieren |
| DELETE | `/v1/entity-types/{id}` | Entity-Typ loeschen |

### Entities (`/v1/entities`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/entities` | Entities auflisten |
| POST | `/v1/entities` | Entity erstellen |
| GET | `/v1/entities/{id}` | Entity abrufen |
| PUT | `/v1/entities/{id}` | Entity aktualisieren |
| DELETE | `/v1/entities/{id}` | Entity loeschen |
| GET | `/v1/entities/{id}/documents` | Entity-Dokumente |
| GET | `/v1/entities/{id}/external-data` | Externe Daten |

### Entity Attachments (`/v1/entities/{id}/attachments`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/entities/{id}/attachments` | Attachments auflisten |
| POST | `/v1/entities/{id}/attachments` | Upload |
| GET | `/v1/entities/{id}/attachments/{aid}` | Attachment abrufen |
| GET | `/v1/entities/{id}/attachments/{aid}/download` | Download |
| GET | `/v1/entities/{id}/attachments/{aid}/thumbnail` | Thumbnail |
| POST | `/v1/entities/{id}/attachments/{aid}/analyze` | KI-Analyse |
| POST | `/v1/entities/{id}/attachments/{aid}/apply-facets` | Facets uebernehmen |
| DELETE | `/v1/entities/{id}/attachments/{aid}` | Loeschen |

### Facet Types (`/v1/facets/types`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/facets/types` | Facet-Typen |
| POST | `/v1/facets/types` | Facet-Typ erstellen |
| GET | `/v1/facets/types/{id}` | Facet-Typ abrufen |
| PUT | `/v1/facets/types/{id}` | Facet-Typ aktualisieren |
| DELETE | `/v1/facets/types/{id}` | Facet-Typ loeschen |
| POST | `/v1/facets/types/generate-schema` | Schema generieren |

### Facet Values (`/v1/facets/values`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/facets/values` | Facet-Werte |
| POST | `/v1/facets/values` | Facet-Wert erstellen |
| GET | `/v1/facets/values/{id}` | Facet-Wert abrufen |
| PUT | `/v1/facets/values/{id}` | Facet-Wert aktualisieren |
| PUT | `/v1/facets/values/{id}/verify` | Verifizieren |
| DELETE | `/v1/facets/values/{id}` | Loeschen |
| GET | `/v1/facets/search` | Volltextsuche |
| GET | `/v1/facets/entity/{id}/summary` | Entity-Zusammenfassung |

### Relations (`/v1/relations`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/relations/types` | Beziehungstypen |
| POST | `/v1/relations/types` | Beziehungstyp erstellen |
| GET | `/v1/relations` | Beziehungen |
| POST | `/v1/relations` | Beziehung erstellen |
| GET | `/v1/relations/{id}` | Beziehung abrufen |
| PUT | `/v1/relations/{id}` | Beziehung aktualisieren |
| DELETE | `/v1/relations/{id}` | Beziehung loeschen |
| GET | `/v1/relations/graph/{id}` | Beziehungsgraph |

### Entity Data Enrichment (`/v1/entity-data`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/entity-data/enrichment-sources` | Datenquellen |
| POST | `/v1/entity-data/analyze-for-facets` | Analyse starten |
| GET | `/v1/entity-data/analysis-preview` | Analyse-Vorschau |
| POST | `/v1/entity-data/apply-changes` | Aenderungen anwenden |

### KI-Assistant (`/v1/assistant`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| POST | `/v1/assistant/chat` | Chat-Nachricht |
| POST | `/v1/assistant/chat-stream` | Chat mit Streaming |
| POST | `/v1/assistant/execute-action` | Aktion ausfuehren |
| GET | `/v1/assistant/commands` | Verfuegbare Kommandos |
| GET | `/v1/assistant/suggestions` | Vorschlaege |
| POST | `/v1/assistant/upload` | Datei hochladen |
| POST | `/v1/assistant/save-to-entity-attachments` | Als Attachment speichern |
| GET | `/v1/assistant/insights` | Proaktive Insights |
| POST | `/v1/assistant/batch-action` | Batch-Aktion |
| GET | `/v1/assistant/wizards` | Verfuegbare Wizards |
| POST | `/v1/assistant/wizards/start` | Wizard starten |
| GET | `/v1/assistant/reminders` | Erinnerungen |
| POST | `/v1/assistant/reminders` | Erinnerung erstellen |

### Smart Query (`/v1/analysis`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| POST | `/v1/analysis/smart-query` | Natural Language Query |
| POST | `/v1/analysis/smart-write` | Natural Language Write |
| GET | `/v1/analysis/smart-query/examples` | Beispiele |
| GET | `/v1/analysis/templates` | Analyse-Templates |
| GET | `/v1/analysis/overview` | Analyse-Uebersicht |
| GET | `/v1/analysis/report/{id}` | Detailreport |
| GET | `/v1/analysis/stats` | Statistiken |

### PySis (`/admin/pysis`, `/v1/pysis-facets`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/admin/pysis/test-connection` | Verbindung testen |
| GET | `/admin/pysis/templates` | Templates |
| GET | `/admin/pysis/processes/{id}` | Prozess-Details |
| POST | `/admin/pysis/processes/{id}/sync/pull` | Von PySis laden |
| POST | `/admin/pysis/processes/{id}/sync/push` | Zu PySis senden |
| POST | `/v1/pysis-facets/analyze` | PySis-Analyse |
| POST | `/v1/pysis-facets/enrich` | Facets anreichern |
| GET | `/v1/pysis-facets/status` | PySis-Status |

### AI Tasks (`/v1/ai-tasks`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/ai-tasks/status` | Task-Status |

### Dashboard (`/v1/dashboard`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/dashboard/stats` | Dashboard-Statistiken |
| GET | `/v1/dashboard/preferences` | Benutzer-Praeferenzen |
| PUT | `/v1/dashboard/preferences` | Praeferenzen speichern |

### Favorites (`/v1/favorites`)

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/v1/favorites` | Favoritenliste |
| POST | `/v1/favorites` | Favorit hinzufuegen |
| GET | `/v1/favorites/check/{entity_id}` | Pruefen ob favorisiert |
| DELETE | `/v1/favorites/{id}` | Favorit entfernen |
| DELETE | `/v1/favorites/entity/{entity_id}` | Favorit per Entity-ID entfernen |

### System

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/` | API-Info |
| GET | `/health` | Health-Check |
| GET | `/config/features` | Feature-Flags |

---

## Authentifizierung

Alle geschuetzten Endpoints erfordern einen gueltigen JWT-Token:

```http
Authorization: Bearer <token>
```

**Token erhalten:**
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}
```

**Rollen:**
| Rolle | Berechtigung |
|-------|--------------|
| ADMIN | Vollzugriff |
| EDITOR | Lesen + Schreiben |
| VIEWER | Nur Lesen |

---

## Fehler-Responses

| Code | Bedeutung |
|------|-----------|
| 400 | Ungueltige Anfrage |
| 401 | Nicht authentifiziert |
| 403 | Zugriff verweigert |
| 404 | Nicht gefunden |
| 409 | Konflikt |
| 422 | Validierungsfehler |
| 429 | Rate Limit |
| 500 | Serverfehler |

---

## Rate Limiting

| Bereich | Limit |
|---------|-------|
| Login | 5/Min pro IP |
| Admin | 100/Min |
| Public API | 1000/Min |

---

**Letzte Aktualisierung:** 2025-12-21
