# PostgreSQL Enum Convention

## Regel

Bei SQLAlchemy mit PostgreSQL-Enums müssen die **Python-Enum-Werte exakt mit den PostgreSQL-Enum-Labels übereinstimmen**.

## Konvention: Alle Werte in GROSSBUCHSTABEN

```python
# KORREKT ✓
class BudgetType(str, Enum):
    GLOBAL = "GLOBAL"
    CATEGORY = "CATEGORY"
    USER = "USER"

# FALSCH ✗
class BudgetType(str, Enum):
    GLOBAL = "global"  # Mismatch mit DB-Wert "GLOBAL"
    CATEGORY = "category"
    USER = "user"
```

## Warum?

PostgreSQL-Enums sind case-sensitive. Wenn Python `"user"` sendet, aber die DB `"USER"` erwartet, entsteht der Fehler:

```
asyncpg.exceptions.InvalidTextRepresentationError: invalid input value for enum budget_type: "user"
```

## Checkliste für neue Enums

1. Python-Enum mit `(str, Enum)` definieren
2. **Werte in GROSSBUCHSTABEN**: `VALUE = "VALUE"`
3. In Migration: `ALTER TYPE enum_name ADD VALUE 'VALUE'` (auch Großbuchstaben)
4. Prüfen mit: `SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'enum_name');`

## Betroffene Dateien (korrigiert 2026-01-04)

- `llm_budget.py`: BudgetType, LimitIncreaseRequestStatus
- `llm_usage.py`: LLMProvider, LLMTaskType
- `model_pricing.py`: PricingProvider, PricingSource
- `user_api_credentials.py`: LLMPurpose, LLMProvider
- `custom_summary.py`: SummaryStatus, SummaryTriggerType
- `summary_widget.py`: SummaryWidgetType
- `summary_execution.py`: ExecutionStatus
- `crawl_preset.py`: PresetStatus
- `smart_query_operation.py`: OperationType
- `reminder.py`: ReminderRepeat, ReminderStatus
- `device_token.py`: DevicePlatform
- `api_configuration.py`: AuthType, ImportMode, APIType, SyncStatus

## DB-Migrationen nachgeholt

```sql
ALTER TYPE budget_type ADD VALUE 'USER';
ALTER TYPE llm_provider ADD VALUE 'OPENAI';
ALTER TYPE api_credential_type ADD VALUE 'OPENAI';
ALTER TYPE source_type ADD VALUE 'SHAREPOINT';
ALTER TYPE notification_event_type ADD VALUE 'SUMMARY_UPDATED';
ALTER TYPE notification_event_type ADD VALUE 'SUMMARY_RELEVANT_CHANGES';
ALTER TYPE notification_event_type ADD VALUE 'LLM_BUDGET_WARNING';
ALTER TYPE notification_event_type ADD VALUE 'LLM_BUDGET_CRITICAL';
ALTER TYPE notification_event_type ADD VALUE 'LLM_BUDGET_BLOCKED';
ALTER TYPE notification_event_type ADD VALUE 'LLM_LIMIT_REQUEST_SUBMITTED';
ALTER TYPE notification_event_type ADD VALUE 'LLM_LIMIT_REQUEST_APPROVED';
ALTER TYPE notification_event_type ADD VALUE 'LLM_LIMIT_REQUEST_DENIED';
ALTER TYPE ai_task_type ADD VALUE 'ENTITY_DATA_ANALYSIS';
ALTER TYPE ai_task_type ADD VALUE 'ATTACHMENT_ANALYSIS';
ALTER TYPE facetvaluesourcetype ADD VALUE 'ATTACHMENT';
ALTER TYPE summary_widget_type_enum ADD VALUE 'CALENDAR';
```
