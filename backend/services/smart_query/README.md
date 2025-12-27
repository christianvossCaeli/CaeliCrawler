# Smart Query Service

KI-gestützter Natural Language Query Service für das CaeliCrawler-System.

## Architektur

```
smart_query/
├── interpreters/              # KI-Query-Interpretation (refactored)
│   ├── __init__.py           # Re-Exports
│   ├── base.py               # Shared utilities, Cache, Sanitization
│   ├── read_interpreter.py   # Read-Query Interpretation
│   ├── write_interpreter.py  # Write-Command Interpretation
│   └── plan_interpreter.py   # Plan-Mode mit SSE Streaming
├── commands/                  # Command Pattern
│   ├── base.py               # BaseCommand, CommandResult
│   ├── registry.py           # CommandRegistry
│   ├── query_commands.py     # Read-Commands
│   ├── entity_commands.py    # Entity Write-Commands
│   ├── facet_commands.py     # Facet Write-Commands
│   └── api_sync_commands.py  # API Sync Commands
├── operations/               # Operations Pattern
│   ├── base.py               # WriteOperation, OperationResult
│   ├── entity_ops.py         # Entity CRUD
│   ├── facet_ops.py          # Facet CRUD
│   ├── batch_ops.py          # Batch-Operationen
│   └── ...
├── query_executor.py         # Read-Modus Ausführung
├── write_executor.py         # Write-Modus Ausführung
├── prompts.py                # Dynamische KI-Prompts
└── ...
```

## Modi

### Read-Modus
Natürlichsprachliche Abfragen für Datensuche und -filterung.

```python
from services.smart_query.interpreters import interpret_query

result = await interpret_query("Zeige alle Gemeinden in NRW", session)
```

### Write-Modus
Natürlichsprachliche Befehle für Datenmanipulation.

```python
from services.smart_query.interpreters import interpret_write_command

result = await interpret_write_command("Erstelle eine neue Person", session)
```

### Plan-Modus
Interaktiver Assistent zur Prompt-Formulierung mit SSE Streaming.

```python
from services.smart_query.interpreters import interpret_plan_query_stream

async for event in interpret_plan_query_stream("Hilf mir", session):
    print(event)
```

## Sicherheit

### Prompt Injection Protection
```python
from services.smart_query.interpreters import sanitize_user_input

safe_input = sanitize_user_input(user_input)
```

Erkannte Muster:
- OpenAI/ChatGPT Control Tokens
- Anthropic/Claude Control Tokens
- Role Injection Attempts
- Instruction Override Attempts

### TTL Caching
```python
from services.smart_query.interpreters import invalidate_types_cache

# Cache invalidieren nach Type-Änderungen
invalidate_types_cache()
```

## Tests

```bash
# Unit Tests für Interpreters
pytest tests/test_services/test_smart_query_interpreters.py -v

# Plan Mode Tests
pytest tests/test_services/test_plan_mode.py -v
```

## API Endpoints

| Endpoint | Method | Rate Limit | Beschreibung |
|----------|--------|------------|--------------|
| `/v1/analysis/smart-query` | POST | 30/min | Read/Plan Query |
| `/v1/analysis/smart-write` | POST | 15/min | Write Command |
| `/v1/analysis/smart-query/stream` | POST | 20/min | SSE Streaming |
| `/v1/analysis/smart-query/validate` | POST | 60/min | Prompt Validation |
