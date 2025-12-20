# Benachrichtigungen

[Zurueck zur Uebersicht](./README.md)

Endpoints fuer das Benachrichtigungssystem inkl. E-Mail, Webhooks und In-App-Benachrichtigungen.

---

## E-Mail-Adressen

### GET /admin/notifications/email-addresses
E-Mail-Adressen des aktuellen Benutzers auflisten.

**Response:**
```json
[
  {
    "id": "uuid",
    "email": "notification@example.com",
    "label": "Arbeit",
    "is_verified": true,
    "is_primary": false,
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

### POST /admin/notifications/email-addresses
Neue E-Mail-Adresse hinzufuegen.

**Request Body:**
```json
{
  "email": "new@example.com",
  "label": "Privat"
}
```

### DELETE /admin/notifications/email-addresses/{email_id}
E-Mail-Adresse loeschen.

### POST /admin/notifications/email-addresses/{email_id}/verify
E-Mail-Adresse verifizieren.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `token` | string | Verifizierungs-Token aus E-Mail |

### POST /admin/notifications/email-addresses/{email_id}/resend-verification
Verifizierungs-E-Mail erneut senden.

---

## Benachrichtigungsregeln

### GET /admin/notifications/rules
Benachrichtigungsregeln des Benutzers auflisten.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Neue Dokumente",
    "description": "Benachrichtigung bei neuen Dokumenten",
    "event_type": "NEW_DOCUMENT",
    "channel": "EMAIL",
    "conditions": {"category_id": "uuid"},
    "channel_config": {"email_id": "uuid"},
    "digest_enabled": true,
    "digest_frequency": "daily",
    "is_active": true,
    "trigger_count": 45,
    "last_triggered": "2025-01-15T10:00:00Z",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-15T10:00:00Z"
  }
]
```

### POST /admin/notifications/rules
Neue Benachrichtigungsregel erstellen.

**Request Body:**
```json
{
  "name": "Crawl-Fehler",
  "description": "Benachrichtigung bei Crawl-Fehlern",
  "event_type": "CRAWL_FAILED",
  "channel": "WEBHOOK",
  "conditions": {},
  "channel_config": {"url": "https://webhook.example.com"},
  "digest_enabled": false,
  "is_active": true
}
```

**Event-Typen:**
| Event | Beschreibung |
|-------|--------------|
| `NEW_DOCUMENT` | Neue Dokumente gefunden |
| `DOCUMENT_CHANGED` | Dokument geaendert |
| `DOCUMENT_REMOVED` | Dokument entfernt |
| `CRAWL_STARTED` | Crawl gestartet |
| `CRAWL_COMPLETED` | Crawl abgeschlossen |
| `CRAWL_FAILED` | Crawl fehlgeschlagen |
| `AI_ANALYSIS_COMPLETED` | KI-Analyse abgeschlossen |
| `HIGH_CONFIDENCE_RESULT` | Relevantes Ergebnis gefunden |
| `SOURCE_STATUS_CHANGED` | Quellenstatus geaendert |
| `SOURCE_ERROR` | Fehler bei Quelle |

**Kanaele:**
| Kanal | Beschreibung |
|-------|--------------|
| `EMAIL` | E-Mail-Benachrichtigung |
| `WEBHOOK` | HTTP-Webhook |
| `IN_APP` | In-App-Benachrichtigung |
| `MS_TEAMS` | Microsoft Teams (demnaechst) |

### GET /admin/notifications/rules/{rule_id}
Regel abrufen.

### PUT /admin/notifications/rules/{rule_id}
Regel aktualisieren.

### DELETE /admin/notifications/rules/{rule_id}
Regel loeschen.

---

## Benachrichtigungen

### GET /admin/notifications/notifications
Benachrichtigungen des Benutzers auflisten.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `status` | string | PENDING, SENT, DELIVERED, READ, FAILED |
| `channel` | string | EMAIL, WEBHOOK, IN_APP, MS_TEAMS |
| `event_type` | string | Event-Typ |
| `page` | int | Seite |
| `per_page` | int | Eintraege pro Seite |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "event_type": "NEW_DOCUMENT",
      "channel": "IN_APP",
      "title": "Neues Dokument gefunden",
      "body": "In Stadt Musterstadt wurde ein neues Dokument gefunden.",
      "status": "READ",
      "related_entity_type": "Document",
      "related_entity_id": "uuid",
      "sent_at": "2025-01-15T10:00:00Z",
      "read_at": "2025-01-15T10:05:00Z",
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

### GET /admin/notifications/notifications/unread-count
Anzahl ungelesener In-App-Benachrichtigungen.

**Response:**
```json
{
  "count": 5
}
```

### GET /admin/notifications/notifications/{notification_id}
Einzelne Benachrichtigung abrufen.

### POST /admin/notifications/notifications/{notification_id}/read
Benachrichtigung als gelesen markieren.

### POST /admin/notifications/notifications/read-all
Alle Benachrichtigungen als gelesen markieren.

---

## Webhook-Test

### POST /admin/notifications/test-webhook
Webhook-URL testen.

**Request Body:**
```json
{
  "url": "https://webhook.example.com/notify",
  "auth": {
    "type": "bearer",
    "token": "abc123"
  }
}
```

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "response": "OK"
}
```

---

## Benutzer-Einstellungen

### GET /admin/notifications/preferences
Benachrichtigungs-Einstellungen abrufen.

### PUT /admin/notifications/preferences
Benachrichtigungs-Einstellungen aktualisieren.

**Request Body:**
```json
{
  "notifications_enabled": true,
  "notification_digest_time": "09:00"
}
```

---

## Metadaten

### GET /admin/notifications/event-types
Verfuegbare Event-Typen abrufen.

### GET /admin/notifications/channels
Verfuegbare Kanaele abrufen.
