# System & Konfiguration

[Zurueck zur Uebersicht](./README.md)

System-Endpoints, Health-Checks, Konfiguration, Sicherheit und Rate Limiting.

---

## System Endpoints

### GET /
Root-Endpoint.

**Response:**
```json
{
  "name": "CaeliCrawler API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

### GET /health
Health-Check.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery_workers": 4
}
```

---

## Konfiguration

### GET /api/config/features
Feature-Flags fuer das Frontend abrufen.

**Response:**
```json
{
  "entityLevelFacets": true,
  "pysisFieldTemplates": false,
  "entityHierarchyEnabled": true
}
```

**Feature-Flags:**
| Flag | Default | Beschreibung |
|------|---------|--------------|
| `entityLevelFacets` | `true` | Wenn `true`, koennen Facets einzelnen Entities zugewiesen werden (nicht nur ueber Entity-Typ) |
| `pysisFieldTemplates` | `false` | Aktiviert PySis Field Templates Funktionalitaet |
| `entityHierarchyEnabled` | `true` | Aktiviert Parent-Child-Beziehungen zwischen Entities |

---

## Fehler-Responses

Alle Endpunkte koennen folgende Fehler zurueckgeben:

### 400 Bad Request
```json
{
  "detail": "Validation error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded. Retry in 45 seconds.",
  "retry_after": 45
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

### 500 Configuration Error (NEU in v2.2.0)
```json
{
  "error": "Configuration Error",
  "detail": "KI-Service nicht konfiguriert. Bitte API-Credentials unter Admin > API Credentials einrichten.",
  "code": "CONFIGURATION_ERROR"
}
```

Dieser Fehler tritt auf, wenn eine erforderliche Konfiguration fehlt oder ungueltig ist, z.B.:
- Fehlende KI-API-Credentials (konfiguriert ueber Admin > API Credentials)
- Ungueltige Datenbankverbindung
- Fehlende Umgebungsvariablen fuer Infrastruktur (DATABASE_URL, REDIS_URL)

---

## Rate Limiting

Die API implementiert Rate Limiting ueber Redis:

| Endpoint | Limit | Beschreibung |
|----------|-------|--------------|
| `POST /auth/login` | 5/Minute | Login-Versuche pro IP |
| `POST /auth/login` | 10/15Min | Nach 10 Fehlversuchen temporaere Sperre |
| `POST /auth/change-password` | 3/5Min | Passwortaenderungen |
| `/admin/*` | 100/Minute | Admin-Endpoints |
| `/api/v1/*` | 1000/Minute | Public API Endpoints |

**Response bei Ueberschreitung:**
```json
{
  "detail": "Rate limit exceeded. Retry in 45 seconds.",
  "retry_after": 45
}
```

**HTTP Status:** `429 Too Many Requests`

**Header:**
- `X-RateLimit-Limit`: Maximale Anzahl Requests
- `X-RateLimit-Remaining`: Verbleibende Requests
- `X-RateLimit-Reset`: Unix-Timestamp des Reset-Zeitpunkts

---

## Authentifizierung & Sicherheit

Die API verwendet JWT-basierte Authentifizierung mit folgenden Sicherheitsfunktionen:

### JWT Token
- **Token-Typ:** Bearer Token
- **Header:** `Authorization: Bearer <token>`
- **Lebensdauer:** 24 Stunden (konfigurierbar)
- **Signatur:** HS256

### Token Blacklist
Bei Logout wird der Token auf eine Redis-basierte Blacklist gesetzt und sofort invalidiert.

### Passwort-Policy
- Minimum 8 Zeichen
- Mindestens ein Grossbuchstabe (A-Z)
- Mindestens ein Kleinbuchstabe (a-z)
- Mindestens eine Ziffer (0-9)

### Rollen
| Rolle | Beschreibung |
|-------|--------------|
| `ADMIN` | Vollzugriff auf alle Funktionen |
| `EDITOR` | Lese- und Schreibzugriff auf Daten |
| `VIEWER` | Nur Lesezugriff |

### Security Headers (Production)
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

### Audit Logging
Alle Aenderungen werden im Audit-Log protokolliert:
- Benutzer-ID
- Aktion (CREATE, UPDATE, DELETE)
- Entity-Typ und ID
- Aenderungen (Diff)
- IP-Adresse
- Zeitstempel

---

## CORS (Cross-Origin Resource Sharing)

Die API erlaubt CORS fuer konfigurierte Domains:

**Development:**
- `http://localhost:3000`
- `http://localhost:5173`

**Production:**
- Konfiguriert ueber `CORS_ORIGINS` Umgebungsvariable

### Erlaubte Methoden
- GET, POST, PUT, PATCH, DELETE, OPTIONS

### Erlaubte Header
- Authorization
- Content-Type
- X-Request-ID
