# LLM Per-User Budget Limits Feature (2026-01-03)

## Feature Summary

Implementierte benutzerbasierte LLM-Budget-Kontrolle mit:
- Hard Blocking bei Limit-Überschreitung (100%)
- Limit-Erhöhungsanträge durch User
- Status-Bar Anzeige im App-Header
- Admin-Verwaltung der User-Limits

## Implementierte Komponenten

### Backend (Python/FastAPI)

| Datei | Beschreibung |
|-------|--------------|
| `models/llm_budget.py` | BudgetType.USER, LimitIncreaseRequestStatus, LLMBudgetLimitRequest |
| `schemas/llm_budget.py` | UserBudgetStatusResponse, LimitIncreaseRequest DTOs |
| `services/llm_budget_service.py` | User Budget Methoden (get_user_budget_status, check_user_can_use_llm, etc.) |
| `api/v1/llm_usage.py` | User Endpoints (/me/llm/usage, /me/llm/limit-request) |
| `api/admin/llm_budget.py` | Admin Endpoints für Limit-Anträge |
| `core/deps.py` | `require_llm_budget` Dependency für Hard Blocking (HTTP 429) |
| `models/notification.py` | LLM_BUDGET_* Event Types hinzugefügt |

### Frontend (Vue 3/TypeScript)

| Datei | Beschreibung |
|-------|--------------|
| `components/common/LLMUsageStatusBar.vue` | Status-Chip im Header mit Tooltip |
| `components/common/LimitIncreaseDialog.vue` | Dialog für Limit-Erhöhungsanträge |
| `components/admin/LimitRequestsPanel.vue` | Admin-Panel für Antragsbearbeitung |
| `composables/useLLMFormatting.ts` | Shared Utilities (formatCurrency, getStatusColor, etc.) |
| `services/api/llm.ts` | API-Funktionen für User/Admin Endpoints |
| `types/llm-usage.ts` | TypeScript Types erweitert |
| `locales/de/llm.json` | Deutsche Übersetzungen |
| `locales/en/llm.json` | Englische Übersetzungen |

## Code Quality Verbesserungen (Audit)

### Memory Leak Fixes
- `useAsyncOperation.ts`: setTimeout mit onUnmounted Cleanup
- `useEntityFacets.ts`: entitySearchTimeout korrekt auf null gesetzt

### Reactivity Best Practices
- `useDocumentsView.ts`: Immutable Set-Updates für processingIds/analyzingIds
- Neue Helper: `addProcessingId()`, `removeProcessingId()`, etc.

### Konsistenz
- Status-Farbe `pending` vereinheitlicht auf `warning`
- Shared `useLLMFormatting` Composable für DRY

### TypeScript
- `VuetifyAlertType` Type für strikte Alert-Typisierung
- `align: 'end' as const` für Vuetify Headers

## Offene Punkte (Future Work)

1. **Notification Service Integration**: NotificationService in LLMBudgetService injizieren
2. **E-Mail Templates**: Templates für Budget-Warnungen erstellen
3. **Celery Task**: Budget-Check Task für User-Budgets erweitern
4. **Tests**: Unit Tests für neue Endpoints/Komponenten

## API Endpoints

### User Endpoints
- `GET /api/me/llm/usage` - Eigener Budget-Status
- `POST /api/me/llm/limit-request` - Erhöhung beantragen
- `GET /api/me/llm/limit-requests` - Eigene Anträge

### Admin Endpoints
- `GET /admin/llm-budget/limit-requests` - Alle Anträge
- `POST /admin/llm-budget/limit-requests/{id}/approve` - Genehmigen
- `POST /admin/llm-budget/limit-requests/{id}/deny` - Ablehnen

## Schwellwerte
- Warning: 80% Budget verbraucht
- Critical: 95% Budget verbraucht
- Blocked: 100% Budget verbraucht (Hard Block)
