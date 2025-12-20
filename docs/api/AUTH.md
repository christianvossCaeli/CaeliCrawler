# Authentifizierung & Benutzerverwaltung

[Zurueck zur Uebersicht](./README.md)

Die API verwendet JWT-basierte Authentifizierung. Alle geschuetzten Endpoints erfordern einen gueltigen Bearer-Token im Authorization-Header.

---

## Authentifizierung

### POST /auth/login
Benutzer authentifizieren und JWT-Token erhalten.

**Rate Limiting:** 5 Versuche pro Minute pro IP-Adresse. Nach 10 fehlgeschlagenen Versuchen innerhalb von 15 Minuten wird die IP temporaer blockiert.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response:**
```json
{
  "access_token": "<JWT_ACCESS_TOKEN>",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "<JWT_REFRESH_TOKEN>",
  "refresh_expires_in": 604800,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "Max Mustermann",
    "role": "ADMIN",
    "is_active": true,
    "is_superuser": false,
    "email_verified": true,
    "language": "de",
    "last_login": "2025-01-15T14:30:00Z",
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

**Fehler:**
- `401 Unauthorized` - Ungueltige E-Mail oder Passwort
- `403 Forbidden` - Benutzerkonto deaktiviert
- `429 Too Many Requests` - Rate Limit erreicht

### GET /auth/me
Profil des aktuell angemeldeten Benutzers abrufen.

**Header:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Max Mustermann",
  "role": "ADMIN",
  "is_active": true,
  "is_superuser": false,
  "email_verified": true,
  "language": "de",
  "last_login": "2025-01-15T14:30:00Z",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### POST /auth/change-password
Passwort des aktuellen Benutzers aendern.

**Rate Limiting:** 3 Versuche pro 5 Minuten.

**Request Body:**
```json
{
  "current_password": "oldPassword123",
  "new_password": "newSecurePassword456"
}
```

**Passwort-Anforderungen:**
- Minimum 8 Zeichen
- Mindestens ein Grossbuchstabe (A-Z)
- Mindestens ein Kleinbuchstabe (a-z)
- Mindestens eine Ziffer (0-9)

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

**Fehler:**
- `400 Bad Request` - Aktuelles Passwort falsch oder neues Passwort erfuellt Anforderungen nicht

### POST /auth/logout
Aktuellen Benutzer abmelden und Token invalidieren.

**Header:** `Authorization: Bearer <token>`

**Token-Blacklisting:** Der aktuelle JWT-Token wird auf eine Blacklist gesetzt und fuer alle zukuenftigen Anfragen abgelehnt.

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

### POST /auth/check-password-strength
Passwort-Staerke pruefen ohne es zu aendern (fuer Echtzeit-Feedback im UI).

**Request Body:**
```json
{
  "password": "testPassword123"
}
```

**Response:**
```json
{
  "is_valid": true,
  "score": 75,
  "errors": [],
  "suggestions": ["Sonderzeichen verwenden fuer mehr Sicherheit"],
  "requirements": "Minimum 8 Zeichen, Gross-/Kleinschreibung, Ziffern"
}
```

### PUT /auth/language
Spracheinstellung des Benutzers aktualisieren.

**Request Body:**
```json
{
  "language": "de"
}
```

**Gueltige Werte:** `de`, `en`

**Response:**
```json
{
  "message": "Sprache aktualisiert"
}
```

### POST /auth/refresh
Access-Token mittels Refresh-Token erneuern.

**Request Body:**
```json
{
  "refresh_token": "<REFRESH_TOKEN>"
}
```

**Response:**
```json
{
  "access_token": "<NEW_ACCESS_TOKEN>",
  "refresh_token": "<SAME_REFRESH_TOKEN>",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_expires_in": 604800,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "Max Mustermann",
    "role": "ADMIN"
  }
}
```

**Fehler:**
- `401 Unauthorized` - Ungueltiger oder abgelaufener Refresh-Token

**Sicherheitsfeatures:**
- Refresh-Token wird gegen gespeicherten Hash validiert
- Session muss aktiv und nicht abgelaufen sein
- Last-used Timestamp wird aktualisiert

---

## Session-Management

### GET /auth/sessions
Alle aktiven Sessions des aktuellen Benutzers auflisten.

**Response:**
```json
{
  "sessions": [
    {
      "id": "uuid",
      "device_type": "DESKTOP",
      "device_name": "Chrome on Windows",
      "ip_address": "192.168.1.1",
      "location": "Germany",
      "created_at": "2025-01-10T10:00:00Z",
      "last_used_at": "2025-01-15T14:30:00Z",
      "is_current": true
    }
  ],
  "total": 3,
  "max_sessions": 5
}
```

**Device-Typen:** `DESKTOP`, `MOBILE`, `TABLET`, `API`, `UNKNOWN`

> **Hinweis:** Das Feld `is_current` markiert die aktuelle Session des Benutzers.

### DELETE /auth/sessions/{session_id}
Spezifische Session widerrufen.

**Response:**
```json
{
  "message": "Session revoked successfully"
}
```

**Fehler:**
- `404 Not Found` - Session nicht gefunden
- `400 Bad Request` - Session bereits widerrufen

### DELETE /auth/sessions
Alle Sessions ausser der aktuellen widerrufen ("Ueberall abmelden").

**Response:**
```json
{
  "message": "Revoked 4 session(s)"
}
```

**Session-Management:**
- Maximum 5 gleichzeitige Sessions pro Benutzer
- Bei Ueberschreitung wird die aelteste Session automatisch widerrufen
- Widerrufene Sessions koennen nicht mehr fuer Token-Refresh verwendet werden

---

## E-Mail-Verifizierung

Endpoints zur Verwaltung der E-Mail-Verifizierung. Verifizierte E-Mail-Adressen sind Voraussetzung fuer bestimmte Funktionen wie Passwort-Zuruecksetzung.

### GET /auth/email-verification/status
Verifizierungsstatus der eigenen E-Mail-Adresse abrufen.

**Header:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "email": "user@example.com",
  "email_verified": true,
  "verification_sent_at": "2025-01-15T10:00:00Z"
}
```

**Hinweise:**
- `verification_sent_at` ist `null` wenn noch nie eine Verifizierungs-E-Mail gesendet wurde

### POST /auth/email-verification/request
Neue Verifizierungs-E-Mail anfordern.

**Rate Limiting:** 1 Anfrage pro 5 Minuten (um Spam zu verhindern).

**Header:** `Authorization: Bearer <token>`

**Response (Erfolg):**
```json
{
  "message": "Verifizierungs-E-Mail wurde gesendet"
}
```

**Response (bereits verifiziert):**
```json
{
  "message": "E-Mail-Adresse ist bereits verifiziert"
}
```

**Fehler:**
- `429 Too Many Requests` - Rate Limit erreicht (5 Minuten warten)

**Hinweise:**
- Die Verifizierungs-E-Mail enthaelt einen Link zum Frontend mit Token
- Token ist 24 Stunden gueltig
- Bei erneuter Anforderung wird ein neuer Token generiert (alter wird ungueltig)

### POST /auth/email-verification/confirm
E-Mail-Adresse mit Token verifizieren.

**Kein Authorization-Header erforderlich** (Token enthaelt Benutzer-Identifikation).

**Request Body:**
```json
{
  "token": "<VERIFICATION_TOKEN>"
}
```

**Response (Erfolg):**
```json
{
  "message": "E-Mail-Adresse erfolgreich verifiziert"
}
```

**Fehler:**
- `400 Bad Request` - Token ungueltig oder abgelaufen
- `400 Bad Request` - E-Mail bereits verifiziert

**Hinweise:**
- Nach erfolgreicher Verifizierung wird `email_verified` auf `true` gesetzt
- Token kann nur einmal verwendet werden

---

## Benutzerverwaltung (Admin)

Admin-Endpoints fuer Benutzerverwaltung. **Erfordert Admin-Rolle.**

### GET /admin/users
Alle Benutzer auflisten mit Pagination und Filterung.

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `page` | int | Seite (default: 1) |
| `per_page` | int | Eintraege pro Seite (1-100, default: 20) |
| `role` | string | Filter nach Rolle (ADMIN, EDITOR, VIEWER) |
| `is_active` | boolean | Nur aktive/inaktive Benutzer |
| `search` | string | Suche in E-Mail oder Name |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "Max Mustermann",
      "role": "ADMIN",
      "is_active": true,
      "is_superuser": false,
      "last_login": "2025-01-15T14:30:00Z",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-15T14:30:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20,
  "pages": 3
}
```

### POST /admin/users
Neuen Benutzer erstellen.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "securePassword123",
  "full_name": "Neuer Benutzer",
  "role": "EDITOR",
  "is_active": true,
  "is_superuser": false
}
```

**Response:** `201 Created` mit Benutzer-Objekt

**Fehler:**
- `409 Conflict` - E-Mail bereits vergeben
- `409 Conflict` - Passwort erfuellt Anforderungen nicht

### GET /admin/users/{user_id}
Einzelnen Benutzer abrufen.

### PUT /admin/users/{user_id}
Benutzer aktualisieren.

**Request Body:**
```json
{
  "email": "updated@example.com",
  "full_name": "Aktualisierter Name",
  "role": "ADMIN",
  "is_active": true
}
```

**Einschraenkungen:**
- Eigene Admin-Rolle kann nicht entfernt werden
- Eigenes Konto kann nicht deaktiviert werden

### DELETE /admin/users/{user_id}
Benutzer loeschen.

**Einschraenkungen:**
- Eigenes Konto kann nicht geloescht werden

**Response:**
```json
{
  "message": "User user@example.com deleted successfully"
}
```

### POST /admin/users/{user_id}/reset-password
Passwort eines Benutzers zuruecksetzen (Admin-Funktion).

**Request Body:**
```json
{
  "new_password": "newSecurePassword456"
}
```

**Response:**
```json
{
  "message": "Password for user@example.com reset successfully"
}
```

---

## Benutzerrollen

| Rolle | Beschreibung |
|-------|--------------|
| `ADMIN` | Vollzugriff auf alle Funktionen |
| `EDITOR` | Lese- und Schreibzugriff auf Daten |
| `VIEWER` | Nur Lesezugriff |

---

## Sicherheitshinweise

1. **Token-Lebensdauer:** Access-Tokens haben eine begrenzte Lebensdauer (Standard: 1 Stunde)
2. **Refresh-Tokens:** Koennen fuer die Token-Erneuerung verwendet werden (Standard: 7 Tage)
3. **Session-Limit:** Maximal 5 gleichzeitige Sessions pro Benutzer
4. **Passwort-Hashing:** Passwoerter werden mit bcrypt gehasht
5. **Rate Limiting:** Schutz vor Brute-Force-Angriffen
