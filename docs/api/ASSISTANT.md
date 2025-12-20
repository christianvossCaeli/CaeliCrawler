# KI-Assistant

[Zurueck zur Uebersicht](./README.md)

Interaktiver KI-Assistant fuer natuerlichsprachliche Interaktionen mit dem System.

---

## Uebersicht

Der KI-Assistant ermoeglicht:
- Natuerlichsprachliche Abfragen und Datensuche
- Inline-Bearbeitung mit Preview und Bestaetigung
- Batch-Operationen auf mehrere Entities
- Gefuehrte Wizards fuer komplexe Aufgaben
- Erinnerungen mit Entity-Bezug
- Bildanalyse mit Vision-API
- Proaktive Insights basierend auf Kontext

---

## Chat Endpoints

### POST /v1/assistant/chat
Nachricht an den KI-Assistant senden.

**Request Body:**
```json
{
  "message": "Zeige mir alle Buergermeister in NRW",
  "context": {
    "current_route": "/entities/municipality",
    "current_entity_id": null,
    "current_entity_type": "municipality",
    "view_mode": "list",
    "available_actions": ["filter", "search", "navigate"]
  },
  "conversation_history": [
    {
      "role": "user",
      "content": "Vorherige Nachricht",
      "timestamp": "2025-01-15T14:25:00Z"
    },
    {
      "role": "assistant",
      "content": "Vorherige Antwort",
      "timestamp": "2025-01-15T14:25:05Z"
    }
  ],
  "mode": "read",
  "language": "de",
  "attachment_ids": ["uuid1", "uuid2"]
}
```

**Modi:**
| Modus | Beschreibung |
|-------|--------------|
| `read` | Nur Abfragen und Navigation (Standard) |
| `write` | Erlaubt Inline-Bearbeitungen mit Preview/Bestaetigung |

**Slash-Kommandos:**
| Kommando | Beschreibung |
|----------|--------------|
| `/help [topic]` | Hilfe anzeigen |
| `/search <query>` | Entities suchen |
| `/create <details>` | Neuen Datensatz erstellen (Weiterleitung zu Smart Query) |
| `/summary` | Aktuelle Entity zusammenfassen |
| `/navigate <entity>` | Zu einer Entity navigieren |

### Response-Typen

**1. Query Result:**
```json
{
  "success": true,
  "response_type": "query_result",
  "response": {
    "results": [...],
    "summary": "Gefunden: 15 Buergermeister in NRW",
    "follow_up_suggestions": ["Nach Alter filtern", "Nur aktive zeigen"]
  },
  "suggested_actions": [
    {"label": "Ergebnisse filtern", "action": "query", "value": "..."},
    {"label": "Details anzeigen", "action": "navigate", "value": "/..."}
  ]
}
```

**2. Action Preview (im Write-Modus):**
```json
{
  "success": true,
  "response_type": "action_preview",
  "response": {
    "action_type": "update_entity",
    "entity_id": "uuid",
    "changes": {"position": {"old": "Buergermeister", "new": "Oberbuergermeister"}},
    "confirmation_required": true,
    "confirmation_message": "Position von Max Mueller aendern?"
  }
}
```

**3. Navigation:**
```json
{
  "success": true,
  "response_type": "navigation",
  "response": {
    "target_route": "/entities/person/max-mueller",
    "target_entity_id": "uuid",
    "message": "Navigiere zu Max Mueller"
  }
}
```

**4. Image Analysis (bei vorhandenen Attachments):**
```json
{
  "success": true,
  "response_type": "image_analysis",
  "response": {
    "type": "image_analysis",
    "message": "Das Bild zeigt ein Protokoll einer Gemeinderatssitzung vom 15.01.2025...",
    "data": {
      "items": [{
        "attachment_ids": ["uuid1"],
        "entity_id": "uuid"
      }],
      "total": 1,
      "query_interpretation": {
        "query": "Analysiere das Bild",
        "attachment_ids": ["uuid1"]
      }
    }
  },
  "suggested_actions": [
    {"label": "Als Attachment speichern", "action": "save_attachment", "value": "{...}"},
    {"label": "Als Pain Point speichern", "action": "create_facet", "value": "pain_point"},
    {"label": "Als Notiz speichern", "action": "create_facet", "value": "summary"}
  ]
}
```

---

### POST /v1/assistant/chat-stream
Streaming-Response vom KI-Assistant via Server-Sent Events (SSE).

**Request Body:** Identisch mit `/chat`

**Response:** Server-Sent Events Stream

**Event-Typen:**
| Event-Typ | Beschreibung |
|-----------|--------------|
| `status` | Verarbeitungsstatus (z.B. "Searching...", "Analyzing...") |
| `intent` | Erkannte Absicht |
| `token` | Einzelne Tokens fuer Echtzeit-Textanzeige |
| `item` | Einzelne Ergebnis-Items (gestreamt) |
| `complete` | Finale Response-Daten |
| `error` | Fehlerinformationen |

**Beispiel:**
```
data: {"type": "status", "message": "Suche..."}

data: {"type": "intent", "intent": "search_entities"}

data: {"type": "token", "content": "Ich "}

data: {"type": "complete", "data": {...}}

data: [DONE]
```

---

## Attachment Endpoints

### POST /v1/assistant/upload
Datei-Attachment fuer Chat hochladen.

**Request:** `multipart/form-data`

**Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `file` | File | Datei (max. 10MB) |

**Unterstuetzte Dateitypen:**
- Bilder: PNG, JPEG, GIF, WebP
- Dokumente: PDF

**Response:**
```json
{
  "success": true,
  "attachment": {
    "attachment_id": "uuid",
    "filename": "dokument.pdf",
    "content_type": "application/pdf",
    "size": 1234567
  }
}
```

**Hinweis:** Attachments werden automatisch nach 1 Stunde geloescht.

---

### DELETE /v1/assistant/upload/{attachment_id}
Attachment loeschen.

**Response:**
```json
{
  "success": true,
  "message": "Attachment geloescht"
}
```

---

### POST /v1/assistant/save-to-entity-attachments
Temporaere Chat-Attachments als permanente Entity-Attachments speichern.

> **NEU:** Dieser Endpoint ermoeglicht es, nach einer Bildanalyse im Chat die analysierten Bilder/PDFs als dauerhafte Attachments bei einer Entity zu speichern.

**Request Body:**
```json
{
  "entity_id": "uuid",
  "attachment_ids": ["temp-uuid-1", "temp-uuid-2"]
}
```

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `entity_id` | string | UUID der Ziel-Entity |
| `attachment_ids` | string[] | Liste temporaerer Attachment-IDs |

**Voraussetzungen:**
- Benutzer muss authentifiziert sein
- Entity muss existieren
- Temporaere Attachments muessen noch vorhanden sein (max. 1 Stunde)

**Response:**
```json
{
  "success": true,
  "saved_count": 2,
  "attachment_ids": ["perm-uuid-1", "perm-uuid-2"],
  "errors": null,
  "message": "2 Attachment(s) gespeichert"
}
```

**Bei teilweisem Erfolg:**
```json
{
  "success": true,
  "saved_count": 1,
  "attachment_ids": ["perm-uuid-1"],
  "errors": ["Attachment temp-uuid-2 nicht gefunden oder abgelaufen"],
  "message": "1 Attachment(s) gespeichert, 1 Fehler"
}
```

**Fehler:**
- `400 Bad Request` - Ungueltige Entity-ID
- `401 Unauthorized` - Nicht authentifiziert

**Workflow:**
1. Benutzer laedt Bild im Chat hoch (`POST /v1/assistant/upload`)
2. Bild wird analysiert (Chat-Anfrage mit `attachment_ids`)
3. Nach Analyse wird "Als Attachment speichern" als SuggestedAction angeboten
4. Frontend ruft diesen Endpoint auf mit Entity-ID und temp Attachment-IDs
5. Temp Attachments werden zu permanenten EntityAttachments konvertiert

---

## Action Endpoints

### POST /v1/assistant/execute-action
Bestaetigte Aktion ausfuehren.

**Request Body:**
```json
{
  "action": {
    "action_type": "update_entity",
    "entity_id": "uuid",
    "changes": {"position": "Oberbuergermeister"}
  },
  "context": {
    "current_route": "/entities/person/max-mueller"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Position von Max Mueller wurde aktualisiert",
  "affected_entity_id": "uuid",
  "affected_entity_name": "Max Mueller",
  "refresh_required": true
}
```

---

### GET /v1/assistant/commands
Liste verfuegbarer Slash-Kommandos abrufen.

**Response:**
```json
[
  {
    "command": "/help",
    "description": "Hilfe anzeigen",
    "usage": "/help [topic]",
    "examples": ["/help", "/help suche"]
  },
  {
    "command": "/search",
    "description": "Entities suchen",
    "usage": "/search <suchbegriff>",
    "examples": ["/search Gummersbach", "/search Buergermeister"]
  }
]
```

---

### GET /v1/assistant/suggestions
Kontextbezogene Vorschlaege basierend auf aktuellem Standort.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `route` | string | Aktuelle Route |
| `entity_type` | string | Aktueller Entity-Typ |
| `entity_id` | string | Aktuelle Entity-ID |

**Response:**
```json
{
  "suggestions": [
    {"label": "Zusammenfassung", "query": "/summary"},
    {"label": "Pain Points", "query": "Zeige Pain Points"},
    {"label": "Relationen", "query": "Zeige alle Relationen"}
  ],
  "available_facet_types": [
    {"slug": "pain_point", "name": "Pain Point", "name_plural": "Pain Points", "icon": "mdi-alert-circle"}
  ]
}
```

---

### GET /v1/assistant/insights
Proaktive Insights basierend auf Kontext abrufen.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `route` | string | Aktuelle Route (required) |
| `view_mode` | string | Ansichtsmodus (dashboard, list, detail) |
| `entity_type` | string | Entity-Typ |
| `entity_id` | string | Entity-ID |

**Response:**
```json
{
  "insights": [
    {
      "type": "data_quality",
      "priority": "medium",
      "title": "Unvollstaendige Daten",
      "message": "5 Gemeinden ohne Kontaktperson",
      "suggested_action": {"label": "Anzeigen", "route": "/entities/municipality?filter=no_contact"}
    }
  ]
}
```

---

## Batch Operations

### POST /v1/assistant/batch-action
Batch-Aktion auf mehrere Entities ausfuehren oder Vorschau anzeigen.

**Berechtigung:** EDITOR oder ADMIN

**Request Body:**
```json
{
  "action_type": "add_facet",
  "target_filter": {
    "entity_type": "municipality",
    "location.admin_level_1": "Nordrhein-Westfalen"
  },
  "action_data": {
    "facet_type_slug": "pain_point",
    "value": {"title": "Personalmangel", "category": "Personal"}
  },
  "dry_run": true
}
```

**Action-Typen:**
| Action | Beschreibung |
|--------|--------------|
| `add_facet` | Facet zu Entities hinzufuegen |
| `update_field` | Feld bei Entities aktualisieren |
| `add_relation` | Relation zu Entities hinzufuegen |
| `remove_facet` | Facet von Entities entfernen |

**Response (dry_run=true):**
```json
{
  "success": true,
  "affected_count": 25,
  "preview": [
    {"entity_id": "uuid", "entity_name": "Koeln", "action": "add_facet"}
  ],
  "message": "25 Entities wuerden betroffen sein"
}
```

---

### GET /v1/assistant/batch-action/{batch_id}/status
Status einer laufenden Batch-Operation abrufen.

**Response:**
```json
{
  "batch_id": "batch_123",
  "status": "running",
  "processed": 15,
  "total": 25,
  "errors": [],
  "message": "60% abgeschlossen"
}
```

**Status-Werte:** `pending`, `running`, `completed`, `failed`, `cancelled`

---

### POST /v1/assistant/batch-action/{batch_id}/cancel
Laufende Batch-Operation abbrechen.

---

## Wizards

### GET /v1/assistant/wizards
Verfuegbare Wizard-Typen auflisten.

**Response:**
```json
{
  "wizards": [
    {
      "wizard_type": "create_entity",
      "name": "Entity erstellen",
      "description": "Neue Entity mit gefuehrter Eingabe erstellen",
      "icon": "mdi-plus-circle"
    }
  ]
}
```

---

### POST /v1/assistant/wizards/start
Neuen Wizard starten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `wizard_type` | string | Wizard-Typ (required) |

**Response:**
```json
{
  "wizard_id": "wizard_abc123",
  "wizard_type": "create_entity",
  "current_step": {
    "step_id": "select_type",
    "step_index": 0,
    "total_steps": 3,
    "question": "Welchen Entity-Typ moechten Sie erstellen?",
    "input_type": "select",
    "options": [
      {"value": "person", "label": "Person"},
      {"value": "municipality", "label": "Gemeinde"}
    ]
  },
  "can_go_back": false,
  "progress": 0
}
```

---

### POST /v1/assistant/wizards/{wizard_id}/respond
Antwort fuer aktuellen Wizard-Schritt senden.

---

### POST /v1/assistant/wizards/{wizard_id}/back
Zum vorherigen Wizard-Schritt zurueckkehren.

---

### POST /v1/assistant/wizards/{wizard_id}/cancel
Wizard abbrechen.

---

## Reminders

### GET /v1/assistant/reminders
Erinnerungen des aktuellen Benutzers auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `status` | string | Filter: pending, sent, dismissed |
| `include_past` | boolean | Vergangene Erinnerungen einschliessen (default: false) |
| `limit` | int | Maximum (1-100, default: 50) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "message": "Kontakt mit Buergermeister aufnehmen",
      "title": "Follow-up",
      "remind_at": "2025-01-20T10:00:00Z",
      "repeat": "none",
      "status": "pending",
      "entity_id": "uuid",
      "entity_type": "person",
      "entity_name": "Max Mueller",
      "created_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 5
}
```

---

### POST /v1/assistant/reminders
Neue Erinnerung erstellen.

**Request Body:**
```json
{
  "message": "Kontakt mit Buergermeister aufnehmen",
  "remind_at": "2025-01-20T10:00:00Z",
  "title": "Follow-up",
  "entity_id": "uuid",
  "entity_type": "person",
  "repeat": "none"
}
```

**Repeat-Werte:** `none`, `daily`, `weekly`, `monthly`

---

### DELETE /v1/assistant/reminders/{reminder_id}
Erinnerung loeschen.

---

### POST /v1/assistant/reminders/{reminder_id}/dismiss
Erinnerung als bestaetigt markieren.

---

### POST /v1/assistant/reminders/{reminder_id}/snooze
Erinnerung verschieben.

**Request Body:**
```json
{
  "remind_at": "2025-01-21T10:00:00Z"
}
```

---

### GET /v1/assistant/reminders/due
Alle faelligen Erinnerungen abrufen (fuer UI-Benachrichtigungen).

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "message": "Follow-up mit Max Mueller",
      "title": "Erinnerung",
      "remind_at": "2025-01-15T10:00:00Z",
      "entity_id": "uuid",
      "entity_name": "Max Mueller"
    }
  ],
  "count": 2
}
```

---

## Facet-Management

### POST /v1/assistant/create-facet-type
Neuen Facet-Typ ueber den KI-Assistant erstellen.

**Berechtigung:** EDITOR oder ADMIN

**Request Body:**
```json
{
  "name": "Budget",
  "name_plural": "Budgets",
  "slug": "budget",
  "description": "Haushaltsinformationen einer Gemeinde",
  "value_type": "structured",
  "icon": "mdi-currency-eur",
  "color": "#4CAF50",
  "applicable_entity_type_slugs": ["municipality"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Facet-Typ 'Budget' wurde erstellt",
  "facet_type": {
    "id": "uuid",
    "name": "Budget",
    "slug": "budget"
  }
}
```

---

## Suggested Actions

Suggested Actions werden in Chat-Responses zurueckgegeben und koennen vom Frontend verarbeitet werden:

| Action | Beschreibung | Value |
|--------|--------------|-------|
| `navigate` | Zu Route navigieren | Route-Pfad |
| `redirect` | Zu Route weiterleiten | Route-Pfad |
| `query` | Neue Chat-Anfrage | Query-Text |
| `edit` | In Write-Modus wechseln | Query-Text |
| `create_facet` | Facet erstellen | Facet-Typ Slug |
| `save_attachment` | Attachments speichern | JSON mit entity_id und attachment_ids |

**save_attachment Action:**
```json
{
  "label": "Als Attachment speichern",
  "action": "save_attachment",
  "value": "{\"entity_id\": \"uuid\", \"attachment_ids\": [\"temp-uuid\"]}"
}
```

Das Frontend parst den `value` und ruft `POST /v1/assistant/save-to-entity-attachments` auf.
