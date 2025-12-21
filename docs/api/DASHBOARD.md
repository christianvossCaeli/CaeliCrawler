# Dashboard API

[Zurueck zur Uebersicht](./README.md)

API-Endpoints fuer das Dashboard mit Statistiken, Aktivitaetsfeed, Insights und Charts.

---

## Benutzer-Praeferenzen

### GET /v1/dashboard/preferences
Dashboard-Widget-Praeferenzen des aktuellen Benutzers abrufen.

**Authentifizierung erforderlich:** Ja

**Response:**
```json
{
  "widgets": [
    {
      "id": "stats",
      "enabled": true,
      "position": 0,
      "size": "large"
    },
    {
      "id": "activity",
      "enabled": true,
      "position": 1,
      "size": "medium"
    }
  ],
  "layout": "grid",
  "theme": "auto"
}
```

---

### PUT /v1/dashboard/preferences
Dashboard-Widget-Praeferenzen aktualisieren.

**Authentifizierung erforderlich:** Ja

**Request Body:**
```json
{
  "widgets": [
    {
      "id": "stats",
      "enabled": true,
      "position": 0,
      "size": "large"
    }
  ],
  "layout": "grid",
  "theme": "dark"
}
```

**Response:** Aktualisierte Praeferenzen (wie GET Response)

---

## Statistiken

### GET /v1/dashboard/stats
Aggregierte Statistiken fuer das Dashboard.

**Authentifizierung erforderlich:** Ja

**Response:**
```json
{
  "entities": {
    "total": 1234,
    "by_type": {
      "municipality": 800,
      "person": 300,
      "organization": 134
    }
  },
  "facets": {
    "total": 5678,
    "verified": 2345,
    "verification_rate": 0.41
  },
  "documents": {
    "total": 3000,
    "processed": 2800,
    "pending": 200
  },
  "crawler": {
    "active_jobs": 3,
    "completed_today": 15,
    "documents_found_today": 45
  }
}
```

---

## Aktivitaetsfeed

### GET /v1/dashboard/activity
Letzte Aktivitaeten aus dem Audit-Log.

**Authentifizierung erforderlich:** Ja

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `limit` | int | Max. Eintraege (1-100, default: 20) |
| `offset` | int | Offset (default: 0) |

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "action": "CREATE",
      "entity_type": "FacetValue",
      "entity_id": "uuid",
      "entity_name": "Pain Point: Personalmangel",
      "user_email": "admin@example.com",
      "created_at": "2025-01-15T14:30:00Z",
      "changes": {
        "value": {"new": {"text": "Personalmangel"}}
      }
    }
  ],
  "total": 150,
  "has_more": true
}
```

---

## Personalisierte Insights

### GET /v1/dashboard/insights
Personalisierte Insights basierend auf Benutzeraktivitaet.

**Authentifizierung erforderlich:** Ja

**Query-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `period_days` | int | Analysezeitraum (1-30, default: 7) |

**Response:**
```json
{
  "insights": [
    {
      "type": "data_quality",
      "priority": "high",
      "title": "Unvollstaendige Daten",
      "message": "15 Gemeinden haben keine Kontaktperson",
      "suggested_action": {
        "label": "Anzeigen",
        "route": "/entities/municipality?filter=no_contact"
      }
    },
    {
      "type": "trend",
      "priority": "medium",
      "title": "Steigende Aktivitaet",
      "message": "23% mehr Pain Points diese Woche erfasst"
    }
  ],
  "summary": {
    "entities_created": 45,
    "facets_added": 120,
    "documents_processed": 89
  }
}
```

---

## Charts

### GET /v1/dashboard/charts/{chart_type}
Daten fuer einen spezifischen Chart-Typ.

**Authentifizierung erforderlich:** Ja

**Verfuegbare Chart-Typen:**
| Chart-Typ | Beschreibung |
|-----------|--------------|
| `entity-distribution` | Entity-Verteilung nach Typ (Pie Chart) |
| `facet-distribution` | Facet-Werte nach Typ (Bar Chart) |
| `crawler-trend` | Crawler-Jobs ueber Zeit (Line Chart) |

**Response (entity-distribution):**
```json
{
  "chart_type": "entity-distribution",
  "title": "Entities nach Typ",
  "data": [
    {"label": "Gemeinden", "value": 800, "color": "#4CAF50"},
    {"label": "Personen", "value": 300, "color": "#2196F3"},
    {"label": "Organisationen", "value": 134, "color": "#FF9800"}
  ]
}
```

**Response (facet-distribution):**
```json
{
  "chart_type": "facet-distribution",
  "title": "Facets nach Typ",
  "data": [
    {"label": "Pain Points", "value": 1500, "verified": 750},
    {"label": "Positive Signale", "value": 1200, "verified": 600},
    {"label": "Kontakte", "value": 800, "verified": 400}
  ]
}
```

**Response (crawler-trend):**
```json
{
  "chart_type": "crawler-trend",
  "title": "Crawler-Aktivitaet",
  "period": "7d",
  "data": [
    {"date": "2025-01-09", "jobs": 12, "documents": 45},
    {"date": "2025-01-10", "jobs": 15, "documents": 52},
    {"date": "2025-01-11", "jobs": 8, "documents": 28}
  ]
}
```

---

## Verwendung in der iOS-App

Die Dashboard-Endpoints werden verwendet fuer:

1. **Dashboard-Ansicht**: Anzeige von Widgets mit Statistiken
2. **Aktivitaetsfeed**: Letzte Aenderungen im System
3. **Insights**: Personalisierte Empfehlungen
4. **Charts**: Visualisierung von Trends

### Swift-Code-Beispiel

```swift
// Repository-Aufruf
let stats = try await DashboardRepository.shared.fetchStats()
let activity = try await DashboardRepository.shared.fetchActivity(limit: 20)
let insights = try await DashboardRepository.shared.fetchInsights(periodDays: 7)
let chartData = try await DashboardRepository.shared.fetchChart(type: "entity-distribution")
```
