# Migration Guide v2.2.0

[Zurueck zur Uebersicht](./README.md)

Dieses Dokument beschreibt die Breaking Changes in Version 2.2.0 und wie Sie Ihren Code anpassen muessen.

---

## Uebersicht Breaking Changes

| Aenderung | Betroffene API | Migration |
|-----------|----------------|-----------|
| `is_active` → `scheduled_only` | Categories | Parameter umbenennen |
| `status` Feld entfernt | CrawlPresets | Feld aus Code entfernen |
| `category_id` jetzt required | CrawlPresetFilters | Immer `category_id` setzen |

---

## 1. Category API: is_active → scheduled_only

### Beschreibung
Der Query-Parameter `is_active` wurde entfernt. Verwenden Sie stattdessen `scheduled_only`, um Kategorien mit aktivem Crawl-Schedule zu filtern.

### Vorher (v2.1.x)
```http
GET /admin/categories?is_active=true
```

```typescript
// Frontend
const activeCategories = await api.get('/admin/categories', {
  params: { is_active: true }
});
```

### Nachher (v2.2.0)
```http
GET /admin/categories?scheduled_only=true
```

```typescript
// Frontend
const scheduledCategories = await api.get('/admin/categories', {
  params: { scheduled_only: true }
});
```

### Hinweis zur Semantik
- `is_active=true` filterte nach dem (nun entfernten) Feld `is_active`
- `scheduled_only=true` filtert nach Kategorien mit `schedule_enabled=true`

Falls Sie das alte `is_active` Feld in Responses verwendet haben, beachten Sie:
- Das Feld existiert nicht mehr in der Response
- Verwenden Sie stattdessen `schedule_enabled` fuer die gleiche Funktionalitaet

---

## 2. CrawlPreset API: status Feld entfernt

### Beschreibung
Das `status` Feld (mit Werten `ACTIVE`, `ARCHIVED`) wurde aus dem CrawlPreset-Schema entfernt. Presets werden jetzt ueber `schedule_enabled` gesteuert.

### Vorher (v2.1.x)
```json
{
  "id": "uuid",
  "name": "Mein Preset",
  "status": "ACTIVE",
  "schedule_enabled": true
}
```

```typescript
// Frontend
if (preset.status === 'ACTIVE') {
  // Preset aktiv
}
```

### Nachher (v2.2.0)
```json
{
  "id": "uuid",
  "name": "Mein Preset",
  "schedule_enabled": true
}
```

```typescript
// Frontend
if (preset.schedule_enabled) {
  // Preset aktiv
}
```

### Betroffene Endpoints
- `GET /admin/crawl-presets`
- `GET /admin/crawl-presets/{id}`
- `POST /admin/crawl-presets`
- `PUT /admin/crawl-presets/{id}`

---

## 3. CrawlPresetFilters: category_id jetzt required

### Beschreibung
Das Feld `category_id` in `CrawlPresetFilters` ist jetzt ein Pflichtfeld. Presets muessen immer einer Kategorie zugeordnet sein.

### Vorher (v2.1.x)
```typescript
// category_id war optional
const filters: CrawlPresetFilters = {
  entity_ids: ['uuid1', 'uuid2']
};
```

### Nachher (v2.2.0)
```typescript
// category_id ist jetzt required
const filters: CrawlPresetFilters = {
  category_id: 'category-uuid',  // Pflichtfeld
  entity_ids: ['uuid1', 'uuid2']
};
```

### Validierungsfehler
Requests ohne `category_id` erhalten jetzt:
```json
{
  "error": "Validation Error",
  "detail": "field required: category_id",
  "code": "VALIDATION_ERROR"
}
```

---

## Migrations-Checkliste

Verwenden Sie diese Checkliste, um sicherzustellen, dass Ihr Code kompatibel ist:

### API-Aufrufe
- [ ] `is_active` Parameter durch `scheduled_only` ersetzen
- [ ] Alle Referenzen auf `preset.status` entfernen
- [ ] `category_id` immer in CrawlPresetFilters setzen

### Frontend-Code
- [ ] TypeScript-Interfaces aktualisieren (status Feld entfernen)
- [ ] UI-Komponenten anpassen, die `is_active` oder `status` anzeigen
- [ ] Filter-Logik auf `schedule_enabled` umstellen

### Backend-Code (falls eigene Services)
- [ ] `is_active` aus Category-Queries entfernen
- [ ] `status` aus CrawlPreset-Verarbeitung entfernen
- [ ] Validierung fuer `category_id` in Filters hinzufuegen

---

## Neue Features in v2.2.0

Neben den Breaking Changes wurden folgende Features hinzugefuegt:

| Feature | Endpoint | Beschreibung |
|---------|----------|--------------|
| Attachment-Suche | `GET /v1/attachments/search` | Volltextsuche ueber Anhaenge |
| Extraction Rejection | `PUT /v1/data/extracted/{id}/reject` | Extraktionen ablehnen |
| Schedule Operations | Smart Query | Crawl-Schedules per natuerlicher Sprache aendern |
| Range-Filter | Entities | Min/Max Filter fuer numerische Attribute |

Siehe die jeweiligen API-Dokumentationen fuer Details.

---

## Support

Bei Fragen zur Migration wenden Sie sich an das Entwicklungsteam.
