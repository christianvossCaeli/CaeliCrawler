# Favorites API

Endpunkte fuer die Verwaltung von Favoriten. Benutzer koennen Entities als Favoriten speichern fuer schnellen Zugriff.

**Prefix:** `/api/v1/favorites`

**Authentifizierung:** Alle Endpunkte erfordern einen gueltigen Bearer-Token.

---

## Endpunkte

### Favoriten auflisten

```http
GET /api/v1/favorites
```

Listet alle Favoriten des aktuellen Benutzers mit Paginierung.

**Query Parameter:**

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `page` | int | Seitennummer (Standard: 1) |
| `per_page` | int | Eintraege pro Seite (1-100, Standard: 20) |
| `entity_type_slug` | string | Filter nach Entity-Typ |
| `search` | string | Suche im Entity-Namen |

**Response (200):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "123e4567-e89b-12d3-a456-426614174000",
      "entity_id": "789e0123-e45b-67c8-d901-234567890abc",
      "created_at": "2024-12-21T10:30:00Z",
      "entity": {
        "id": "789e0123-e45b-67c8-d901-234567890abc",
        "name": "Muenster",
        "slug": "muenster",
        "entity_type_id": "abc12345-def6-7890-ghij-klmnopqrstuv",
        "entity_type_slug": "municipality",
        "entity_type_name": "Gemeinde",
        "entity_type_icon": "mdi-city",
        "entity_type_color": "#4CAF50",
        "hierarchy_path": "/DE/Nordrhein-Westfalen/Muenster",
        "is_active": true
      }
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 20,
  "pages": 1
}
```

---

### Favorit hinzufuegen

```http
POST /api/v1/favorites
```

Fuegt eine Entity zu den Favoriten hinzu.

**Request Body:**

```json
{
  "entity_id": "789e0123-e45b-67c8-d901-234567890abc"
}
```

**Response (201):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "entity_id": "789e0123-e45b-67c8-d901-234567890abc",
  "created_at": "2024-12-21T10:30:00Z",
  "entity": {
    "id": "789e0123-e45b-67c8-d901-234567890abc",
    "name": "Muenster",
    "slug": "muenster",
    "entity_type_id": "abc12345-def6-7890-ghij-klmnopqrstuv",
    "entity_type_slug": "municipality",
    "entity_type_name": "Gemeinde",
    "entity_type_icon": "mdi-city",
    "entity_type_color": "#4CAF50",
    "hierarchy_path": "/DE/Nordrhein-Westfalen/Muenster",
    "is_active": true
  }
}
```

**Fehler:**

| Status | Beschreibung |
|--------|--------------|
| 404 | Entity nicht gefunden |
| 409 | Entity bereits favorisiert |

---

### Favorit-Status pruefen

```http
GET /api/v1/favorites/check/{entity_id}
```

Prueft, ob eine Entity in den Favoriten des Benutzers ist.

**Response (200):**

```json
{
  "entity_id": "789e0123-e45b-67c8-d901-234567890abc",
  "is_favorited": true,
  "favorite_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Wenn nicht favorisiert:

```json
{
  "entity_id": "789e0123-e45b-67c8-d901-234567890abc",
  "is_favorited": false,
  "favorite_id": null
}
```

---

### Favorit entfernen (per Favorite ID)

```http
DELETE /api/v1/favorites/{favorite_id}
```

Entfernt einen Favoriten anhand der Favorite-ID.

**Response (200):**

```json
{
  "message": "Favorite removed successfully"
}
```

**Fehler:**

| Status | Beschreibung |
|--------|--------------|
| 404 | Favorit nicht gefunden |

---

### Favorit entfernen (per Entity ID)

```http
DELETE /api/v1/favorites/entity/{entity_id}
```

Entfernt einen Favoriten anhand der Entity-ID. Praktisch, wenn die Favorite-ID nicht bekannt ist.

**Response (200):**

```json
{
  "message": "Favorite removed successfully"
}
```

**Fehler:**

| Status | Beschreibung |
|--------|--------------|
| 404 | Favorit nicht gefunden |

---

## Schemas

### FavoriteCreate

```json
{
  "entity_id": "string (UUID, required)"
}
```

### FavoriteResponse

```json
{
  "id": "string (UUID)",
  "user_id": "string (UUID)",
  "entity_id": "string (UUID)",
  "created_at": "string (ISO 8601 datetime)",
  "entity": "FavoriteEntityBrief"
}
```

### FavoriteEntityBrief

```json
{
  "id": "string (UUID)",
  "name": "string",
  "slug": "string",
  "entity_type_id": "string (UUID)",
  "entity_type_slug": "string | null",
  "entity_type_name": "string | null",
  "entity_type_icon": "string | null",
  "entity_type_color": "string | null",
  "hierarchy_path": "string | null",
  "is_active": "boolean"
}
```

### FavoriteListResponse

```json
{
  "items": "FavoriteResponse[]",
  "total": "integer",
  "page": "integer",
  "per_page": "integer",
  "pages": "integer"
}
```

### FavoriteCheckResponse

```json
{
  "entity_id": "string (UUID)",
  "is_favorited": "boolean",
  "favorite_id": "string (UUID) | null"
}
```

---

## Beispiele

### Favoriten mit Filter abrufen

```bash
curl -X GET "http://localhost:8000/api/v1/favorites?entity_type_slug=municipality&search=Muenster" \
  -H "Authorization: Bearer <token>"
```

### Entity zu Favoriten hinzufuegen

```bash
curl -X POST "http://localhost:8000/api/v1/favorites" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "789e0123-e45b-67c8-d901-234567890abc"}'
```

### Favorit-Status pruefen

```bash
curl -X GET "http://localhost:8000/api/v1/favorites/check/789e0123-e45b-67c8-d901-234567890abc" \
  -H "Authorization: Bearer <token>"
```

### Favorit entfernen

```bash
curl -X DELETE "http://localhost:8000/api/v1/favorites/entity/789e0123-e45b-67c8-d901-234567890abc" \
  -H "Authorization: Bearer <token>"
```
