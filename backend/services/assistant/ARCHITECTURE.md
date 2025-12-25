# Assistant Service - Architektur-Dokumentation

## Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                     assistant_service.py                         │
│                   (Orchestration Layer - 553 LOC)                │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         AssistantService (Main Class)                    │   │
│  │  • process_message()      - Main entry point            │   │
│  │  • _classify_intent()     - LLM intent classification   │   │
│  │  • _route_intent()        - Route to handlers           │   │
│  │  • execute_action()       - Public API                  │   │
│  │  • execute_batch_action() - Public API                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│                      ┌──────────────┐                           │
│                      │ Intent Router│                           │
│                      └──────────────┘                           │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                              │
        ▼                                              ▼
┌───────────────────┐                        ┌──────────────────┐
│  Security Layer   │                        │  Common Layer    │
│  (Input Filter)   │                        │   common.py      │
├───────────────────┤                        ├──────────────────┤
│ • Input sanitize  │                        │ • OpenAI Client  │
│ • Length validate │                        │ • Entity Validate│
│ • Injection check │                        │ • Suggestions    │
└───────────────────┘                        └──────────────────┘
                               │
        ┌──────────────────────┴──────────────────────────────────┐
        │                      │                  │                │
        ▼                      ▼                  ▼                ▼
┌──────────────┐    ┌──────────────┐   ┌──────────────┐  ┌──────────────┐
│ Query Handler│    │Context Builder│   │Action Executor│  │Response Fmt  │
│ query_handler│    │context_builder│   │action_executor│  │response_fmt  │
├──────────────┤    ├──────────────┤   ├──────────────┤  ├──────────────┤
│ • DB Queries │    │• Entity Data │   │• Single Edits│  │• Help Resp   │
│ • Context Q  │    │• Facet Data  │   │• Batch Ops   │  │• Navigation  │
│ • Corrections│    │• PySIS Data  │   │• Preview     │  │• Summaries   │
│ • Suggestions│    │• Relations   │   │• Execute     │  │• Images      │
│              │    │• App Stats   │   │              │  │• Discussion  │
└──────────────┘    └──────────────┘   └──────────────┘  └──────────────┘
        │                   │                  │                 │
        └───────────────────┴──────────────────┴─────────────────┘
                                  │
        ┌─────────────────────────┴────────────────────┐
        │                         │                     │
        ▼                         ▼                     ▼
┌──────────────┐        ┌──────────────┐     ┌──────────────┐
│Context Actions│        │Facet Mgmt    │     │ Utilities    │
│context_actions│        │facet_mgmt    │     │ utils.py     │
├──────────────┤        ├──────────────┤     ├──────────────┤
│• PySIS Status│        │• List Types  │     │• Format Link │
│• Analyze     │        │• Create Type │     │• JSON Parse  │
│• Enrich      │        │• Assign Type │     │• Truncate    │
│• Create Facet│        │• AI Suggest  │     │• Safe Parse  │
│• History     │        │              │     │              │
└──────────────┘        └──────────────┘     └──────────────┘
```

## Datenfluss

### 1. Message Processing Flow

```
User Message
     │
     ▼
[Security Check] ─────────── FAIL ───→ [Error Response]
     │ PASS
     ▼
[Slash Command?] ── YES ───→ [Handle Command] ───→ [Response]
     │ NO
     ▼
[Intent Classification via LLM]
     │
     ▼
[Intent Router]
     │
     ├─→ QUERY ────────────→ [query_handler.handle_query()]
     ├─→ CONTEXT_QUERY ────→ [query_handler.handle_context_query()]
     ├─→ INLINE_EDIT ──────→ [action_executor.preview_inline_edit()]
     ├─→ BATCH_ACTION ─────→ [action_executor.handle_batch_action_intent()]
     ├─→ NAVIGATION ───────→ [response_formatter.handle_navigation()]
     ├─→ SUMMARIZE ────────→ [response_formatter.handle_summarize()]
     ├─→ HELP ─────────────→ [response_formatter.generate_help_response()]
     ├─→ FACET_MANAGEMENT ─→ [facet_management.handle_facet_management_request()]
     ├─→ CONTEXT_ACTION ───→ [context_actions.handle_context_action()]
     └─→ DISCUSSION ───────→ [response_formatter.handle_discussion()]
     │
     ▼
[Format Response]
     │
     ▼
[Return to User]
```

### 2. Context Building Flow

```
Entity ID
     │
     ▼
[validate_entity_context()] ───→ Load Entity from DB
     │
     ▼
[build_entity_context()]
     │
     ├─→ [build_facet_summary()] ────→ Group Facets by Type
     ├─→ [build_pysis_context()] ────→ Extract PySIS Fields
     └─→ [count_entity_relations()] ─→ Count Relations
     │
     ▼
[prepare_entity_data_for_ai()] ──→ JSON Format for LLM
     │
     ▼
[AI Processing]
```

### 3. Query Processing Flow

```
User Query
     │
     ▼
[handle_query()]
     │
     ▼
[SmartQueryService.smart_query()] ──→ Execute DB Query
     │
     ▼
[Check Results]
     │
     ├─→ No Results ──→ [suggest_corrections()] ──→ Fuzzy Match
     └─→ Has Results ─→ [format_query_result_message()]
     │
     ▼
[build_query_suggestions()] ──→ Generate Follow-up Actions
     │
     ▼
[Return QueryResponse]
```

### 4. Action Execution Flow

```
User Action Request
     │
     ▼
[Check Mode: Read/Write]
     │
     ├─→ Write Action in Read Mode ──→ [Error: Write Mode Required]
     └─→ Allowed ───────────────────→ Continue
     │
     ▼
[preview_inline_edit() / handle_batch_action_intent()]
     │
     ▼
[execute_batch_action(dry_run=True)] ──→ Preview Changes
     │
     ▼
[Return Preview to User for Confirmation]
     │
     ▼
[User Confirms]
     │
     ▼
[execute_action() / execute_batch_action(dry_run=False)]
     │
     ▼
[Apply Changes to DB]
     │
     ▼
[Return Success Response]
```

## Modul-Abhängigkeiten

```
assistant_service.py
    ├── common.py
    ├── query_handler.py
    │   ├── common.py
    │   ├── context_builder.py
    │   └── utils.py
    ├── action_executor.py
    │   └── common.py
    ├── response_formatter.py
    │   ├── common.py
    │   ├── context_builder.py
    │   └── utils.py
    ├── context_actions.py (existing)
    ├── facet_management.py
    │   └── common.py
    ├── prompts.py (existing)
    └── utils.py (existing)
```

## Intent-Typen und Handler-Mapping

| Intent Type | Handler Module | Main Function |
|-------------|----------------|---------------|
| QUERY | query_handler | `handle_query()` |
| CONTEXT_QUERY | query_handler | `handle_context_query()` |
| INLINE_EDIT | action_executor | `preview_inline_edit()` |
| BATCH_ACTION | action_executor | `handle_batch_action_intent()` |
| COMPLEX_WRITE | response_formatter | `suggest_smart_query_redirect()` |
| NAVIGATION | response_formatter | `handle_navigation()` |
| SUMMARIZE | response_formatter | `handle_summarize()` |
| HELP | response_formatter | `generate_help_response()` |
| FACET_MANAGEMENT | facet_management | `handle_facet_management_request()` |
| CONTEXT_ACTION | context_actions | `handle_context_action()` |
| DISCUSSION | response_formatter | `handle_discussion()` |

## Externe Abhängigkeiten

### AI Services
- **Azure OpenAI**: Intent Classification, Context Queries, Image Analysis, Discussion Analysis
- **SmartQueryService**: Database Queries

### Database Models
- **Entity**: Core entity data
- **FacetType / FacetValue**: Facet management
- **EntityRelation**: Relations between entities
- **PySisProcess**: PySIS integration data

### Utility Services
- **Translator**: Multi-language support (de/en)
- **Security Utils**: Input sanitization, injection detection
- **Geographic Utils**: Fuzzy matching for locations

## Error Handling Strategie

1. **Input Validation Layer** (assistant_service.py)
   - Length validation
   - Injection detection
   - Sanitization

2. **Business Logic Layer** (Handler Modules)
   - Try-Catch blocks in all handlers
   - Structured logging via structlog
   - Graceful degradation

3. **Response Layer**
   - Consistent ErrorResponseData format
   - User-friendly error messages
   - Suggested recovery actions

## Performance Considerations

### Caching
- Facet Types cached per session (`_facet_types_cache`)
- Consider: Entity context caching for repeated queries

### Lazy Loading
- OpenAI client lazily initialized
- Database queries optimized with selectinload

### Batch Operations
- Preview mode (dry_run) prevents unnecessary DB writes
- Batch executor uses Smart Query's optimized batch logic

## Security Features

1. **Input Sanitization**
   - Prompt injection detection
   - Length limits (SecurityConstants.MAX_MESSAGE_LENGTH)
   - Risk level assessment

2. **Mode Enforcement**
   - Read-only operations in read mode
   - Write operations require explicit write mode

3. **Entity Validation**
   - UUID format validation
   - Existence checks before operations
   - Permission checks (to be implemented)

## Testing Strategy

### Unit Tests
- Each module testable independently
- Mock database sessions
- Mock OpenAI client

### Integration Tests
- Full flow through AssistantService
- Real database (test DB)
- Mocked OpenAI responses

### E2E Tests
- API endpoint tests
- Real conversations
- Multi-turn interactions
