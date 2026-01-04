# Smart Query Integration Audit - 2024-12-31

## Übersicht der Analyse

Umfassende Analyse der Smart Query Integration unter Betrachtung von:
1. Frontend-Backend Kommunikation
2. State Management
3. Error Handling
4. Mode Switching (Read/Write/Plan)
5. Context Passing
6. Results Handling
7. Integration mit Assistant

---

## 1. FRONTEND-BACKEND KOMMUNIKATION

### Kommunikationspfade

#### Read Mode Query
- Frontend: `SmartQueryView.vue` → `useSmartQueryCore.ts` → `/v1/analysis/smart-query`
- Backend: `analysis_api/smart_query.py` → `smart_query()` service
- Response: `SmartQueryResults` mit `visualization` und `items`

#### Write Mode Preview
- Frontend: `SmartQueryView.vue` → `useSmartQueryCore.ts` → `/v1/analysis/smart-write`
- Backend: `analysis_api/smart_query.py` → Preview-Generation
- Response: `SmartQueryPreview` mit Preview-Daten

#### Plan Mode Streaming
- Frontend: `usePlanModeSSE.ts` → `/v1/analysis/smart-query/stream`
- Backend: `plan_interpreter.py` → SSE-Stream mit Claude
- Response: Event-Stream (start, chunk, done, error)

### API Endpoints
1. `POST /v1/analysis/smart-query` - Read/Plan Mode (30/min rate limit)
2. `POST /v1/analysis/smart-query/stream` - Streaming Plan Mode
3. `POST /v1/analysis/smart-write` - Write Preview/Execution
4. `POST /v1/analysis/smart-query/validate` - Query Validation
5. `GET/POST /v1/smart-query-history/*` - History Management

---

## 2. STATE MANAGEMENT

### Frontend State (useSmartQueryCore.ts)
```typescript
Core State:
- question: ref<string>
- currentMode: ref<QueryMode> ('read' | 'write' | 'plan')
- loading: ref<boolean>
- error: ref<string | null>
- results: ref<SmartQueryResults | null>
- previewData: ref<SmartQueryPreview | null>
- fromAssistant: ref<boolean>
- currentStep: ref<number> (für AI-Generation Progress)
- loadingState: ref<LoadingState> (granular loading phases)

Composed Modules:
- useSmartQueryAttachments() - File uploads
- usePlanMode() - Plan Mode conversation
- useSpeechRecognition() - Voice input
```

### Context Store (queryContext.ts)
```typescript
- pendingContext: QueryContextData (from Assistant)
- lastResults: QueryResultData (to Assistant)
- returnToAssistant: boolean

Bidirektionale Kommunikation zwischen Assistant und Smart Query
```

### History Store (smartQueryHistory.ts)
```typescript
- history: SmartQueryOperation[]
- favoriteIds: Set<string>
- isLoading: boolean
- total/page/perPage: Pagination
- error: string | null
```

### Plan Mode State (usePlanModeCore.ts)
```typescript
- conversation: PlanMessage[]
- loading: boolean
- streaming: boolean
- error: string | null
- results: PlanModeResult | null
- validating: boolean
- validationResult: ValidationResult | null
```

---

## 3. ERROR HANDLING

### Frontend Error Handling

#### In executeQuery() - useSmartQueryCore.ts
```typescript
try {
  setLoadingPhase('validating')
  error.value = null
  // ... execution phases ...
} catch (e: unknown) {
  error.value = getErrorDetail(e) || t('smartQueryView.errors.queryError')
} finally {
  setLoadingPhase('idle')
}
```

#### Error Sources
1. **Validation Phase**: Query length, format validation
2. **Interpretation Phase**: AI fails to parse query
3. **Execution Phase**: Query execution fails
4. **Network Phase**: HTTP errors

#### Error Display
- SmartQueryResults.vue shows error alert with closable option
- Speech recognition errors also mapped to error.value
- Plan Mode errors from usePlanModeSSE with granular handling

### Backend Error Handling

#### In smart_query.py endpoint
```python
except ValueError as e:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(e),
    )
```

#### In plan_interpreter.py (SSE Streaming)
- **ConnectTimeout**: "Connection timeout - server unreachable"
- **ReadTimeout**: "Read timeout - response incomplete" (mit partial flag)
- **TimeoutException**: "Request timed out"
- **HTTPStatusError**: "HTTP error: {status_code}"
- **General Exception**: logs full error with exc_info

#### Timeout Configuration (plan_interpreter.py)
```python
timeout_config = httpx.Timeout(
    connect=STREAMING_CONNECT_TIMEOUT,  # 10 seconds
    read=STREAMING_READ_TIMEOUT,         # 30 seconds
    write=10.0,
    pool=5.0,
)
```

#### Backend Sanitization/Security
- `validate_and_sanitize_query()` in base.py
- `PROMPT_INJECTION_PATTERNS` constants
- `sanitize_conversation_messages()` für Plan Mode
- `sanitize_user_input()` vor API calls

---

## 4. MODE SWITCHING (Read/Write/Plan)

### Mode Detection Flow

#### Frontend Mode Switching
```typescript
// Toggle Mode (in SmartQueryToolbar)
v-model:mode="currentMode"  // 'read' | 'write' | 'plan'

// Mode Hints
modeHint.value = computed(() => {
  if (currentMode.value === 'plan') return planHint
  if (currentMode.value === 'write') return writeHint
  return readHint
})

// URL-based Initialization
initializeFromContext() {
  const urlMode = route.query.mode as string
  if (urlMode === 'write') currentMode.value = 'write'
  if (urlMode === 'plan') currentMode.value = 'plan'
}
```

#### Read Mode Execution
```typescript
async function executeReadQuery() {
  const response = await api.post('/v1/analysis/smart-query', {
    question: question.value,
    allow_write: false,  // WICHTIG: Lock für Read Mode
  })
  results.value = response.data
}
```

#### Write Mode Execution
```typescript
async function executeWritePreview() {
  const response = await api.post('/v1/analysis/smart-write', {
    question: question.value,
    preview_only: true,     // WICHTIG: Two-step confirmation
    confirmed: false,
  })
  if (response.data.mode === 'preview' && response.data.success) {
    previewData.value = response.data
  }
}

async function confirmWrite() {
  const response = await api.post('/v1/analysis/smart-write', {
    question: question.value,
    preview_only: false,
    confirmed: true,        // WICHTIG: Erst nach Bestätigung
  })
  results.value = response.data
  previewData.value = null
}
```

#### Plan Mode Execution
```typescript
async function executePlanQuery() {
  if (!question.value.trim()) return
  const currentQuestion = question.value
  question.value = ''
  
  const success = await planMode.executePlanQueryStream(currentQuestion)
  if (!success && planMode.error.value) {
    error.value = planMode.error.value
  }
}
```

### Backend Mode Handling (smart_query.py)
```python
result = await smart_query(
    session,
    query_request.question,
    allow_write=query_request.allow_write,  # Mode Lock
    mode=query_request.mode,                # 'plan', 'read', None
    conversation_history=conversation_history,
)
```

---

## 5. CONTEXT PASSING

### Assistant → Smart Query Context
```typescript
// In queryContext.ts
setFromAssistant(
  query: string,
  mode: 'read' | 'write',
  entityContext?: {
    entityId?: string
    entityType?: string
    entityName?: string
  },
  conversationId?: string
)

// In SmartQueryView.ts - onMounted
const hasContext = initializeFromContext()
if (hasContext && fromAssistant.value && question.value.trim()) {
  executeQuery()  // Auto-execute
}
```

### Smart Query → Assistant Context
```typescript
// In useSmartQueryCore.ts
function sendResultsToAssistant() {
  queryContextStore.setResults({
    summary,
    total,
    items: results.value.items?.slice(0, 5),
    interpretation: results.value.query_interpretation,
    success: results.value.success,
    mode: isWriteMode ? 'write' : 'read',
  })
  router.back()
}
```

### URL-basierter Context
```typescript
// In SmartQueryView.ts
const urlQuery = route.query.q as string
const urlMode = route.query.mode as string
const urlFrom = route.query.from as string

// Initialization
if (urlQuery) {
  question.value = urlQuery
  fromAssistant.value = urlFrom === 'assistant'
}
```

### Attachment Context (für Assistant)
```typescript
// In useSmartQueryCore.ts executeWithAttachments()
const response = await assistantApi.chat({
  message: question.value.trim() || 'Analysiere das Bild',
  context: {
    current_route: '/smart-query',
    current_entity_id: null,
    // ... entity context ...
  },
  attachment_ids: attachmentIds,
})
```

---

## 6. RESULTS HANDLING

### Read Mode Results (SmartQueryResults.vue)

#### Single Query (mit Visualization)
```typescript
interface SmartQueryResults {
  mode: 'read'
  success: boolean
  message?: string
  total?: number
  items?: Record<string, unknown>[]
  visualization?: SmartQueryVisualization
  interpretation?: SmartQueryInterpretation
  explanation?: string
  suggested_actions?: SmartQueryAction[]
}

// 9 Visualisierungstypen:
// 'table' | 'bar_chart' | 'line_chart' | 'pie_chart' | 'stat_card' |
// 'text' | 'comparison' | 'map' | 'calendar'
```

#### Compound Query (mehrere Visualisierungen)
```typescript
if (results?.is_compound) {
  // SmartQueryResults.vue rendert CompoundQueryResult
  compoundVisualizations: SmartQueryVisualization[]
  explanation: string
  suggested_actions: SmartQueryAction[]
}
```

### Write Mode Results

#### Preview Phase
```typescript
interface SmartQueryPreview {
  mode: 'preview'
  success: boolean
  preview: Record<string, unknown>  // Vorschau der zu erstellenden Objekte
  interpretation: SmartQueryInterpretation
  message?: string
}

// SmartQueryPreview.vue zeigt Preview + Confirm Button
```

#### Execution Phase
```typescript
interface SmartQueryResults {
  mode: 'write'
  success: boolean
  message?: string
  created_items?: CreatedItem[]
  created_items[].id
  created_items[].name
  created_items[].type
  created_items[].entity_type
}

// SmartQueryWriteResults.vue zeigt Ergebnisse
```

### Plan Mode Results

```typescript
interface PlanModeResult {
  success: boolean
  message: string
  has_generated_prompt?: boolean
  generated_prompt?: string
  suggested_mode?: 'read' | 'write'
  mode: 'plan'
}

// usePlanModeSSE analysiert Response nach "**Fertiger Prompt:**"
```

### Results Display Flow
```
SmartQueryResults.vue
├── Error Alert (wenn error vorhanden)
├── Loading State (Read Mode)
├── AI Generation Progress (Write Mode)
├── Preview (Write Mode - vor Bestätigung)
├── Write Results (Write Mode - nach Bestätigung)
├── Compound Results (Read Mode - mehrere Visualisierungen)
└── Single Result + Actions (Read Mode - einzelne Abfrage)
```

---

## 7. INTEGRATION MIT ASSISTANT

### Chat → Smart Query Übergabe

#### Flow
```
AssistantService.chat()
  ├─ Erkennt "/create" Slash-Command
  ├─ oder user_intent === 'complex_operation'
  ├─ Setzt queryContextStore.setFromAssistant()
  └─ Gibt redirect_to_smart_query response
    └─ Frontend navigiert zu /smart-query
      └─ SmartQueryView.vue initialisiert mit Kontext
        └─ Auto-executes query
```

#### Assistant Detection
In assistant.py - chat endpoint prüft:
- Slash Commands: `/create`, `/search`, `/navigate`
- Komplexe Operationen (redirect_to_smart_query)
- Attachment Analysis (delegiert an Assistant API)

### Smart Query → Assistant Übergabe

#### Flow
```
SmartQueryView.vue
  └─ "Zurück zum Assistant" Button
    └─ sendResultsToAssistant()
      ├─ Formatiert Results als QueryResultData
      ├─ queryContextStore.setResults()
      └─ router.back()
        └─ Assistant liest Results via consumeResults()
```

#### Result Processing
```typescript
const summary = isWriteMode
  ? `${results.created_items?.length} Elemente erstellt`
  : `${results.total} Ergebnisse gefunden`

queryContextStore.setResults({
  summary,
  total: results.value.total || results.value.created_items?.length || 0,
  items: results.value.items?.slice(0, 5) || [],
  interpretation: results.value.query_interpretation,
  success: results.value.success !== false,
  mode: isWriteMode ? 'write' : 'read',
})
```

### Bidirektionale Context-Nutzung
```typescript
// In SmartQueryView.ts
const {
  // ...
  sendResultsToAssistant,
  initializeFromContext,
} = useSmartQuery()

@click="sendResultsToAssistant"  // Ergebnis zurück

fromAssistant.value === true      // Gekennzeichnet wenn vom Assistant
```

---

## ERKANNTE LÜCKEN UND INKONSISTENZEN

### 1. ERROR HANDLING - Fehlende Szenarien

#### Problem: Attachment Upload Fehler nicht vollständig behandelt
```typescript
// useSmartQueryAttachments.ts - Zeile 79-80
catch (e: unknown) {
  error.value = getErrorDetail(e) || t('assistant.attachmentError')
  // LÜCKE: isUploading wird nicht auf false gesetzt!
  // Komponente könnte in Loading-State stecken bleiben
}
```

**Status**: KRITISCH
**Fix**: `isUploading.value = false` hinzufügen

#### Problem: Keine Timeout-Behandlung auf Frontend für Streaming
```typescript
// usePlanModeSSE.ts - executePlanQueryStream()
// Backend setzt STREAMING_TOTAL_TIMEOUT = 120 Sekunden
// Frontend hat keinen entsprechenden Timeout!

// Backend: Wirft error nach 120s
// Frontend: Wartet potentiell länger oder unbegrenzt
```

**Status**: HOCH
**Fix**: Frontend-seitiger Abort-Timeout nach 130s

#### Problem: Validierungsfehler unterscheiden sich zwischen Read/Write
```typescript
// Read Mode: allow_write=false
// Write Mode: preview_only=true/false + confirmed=true/false

// Aber:
- Keine explizite Validierung der Mode-Konsistenz
- Keine Prüfung auf Widersprüche (z.B. write in read mode)
```

**Status**: MITTEL
**Fix**: Mode-Validierung in executeQuery()

### 2. STATE MANAGEMENT - Race Conditions

#### Problem: Concurrent executions nicht verhindert
```typescript
async function executeQuery() {
  if (currentMode.value === 'plan') {
    return executePlanQuery()
  }
  
  // LÜCKE: loading könnte bei schneller Klickfolge verwirrend werden
  if (!question.value.trim() && !attachments.hasAttachments()) return
  
  setLoadingPhase('validating')
  // Wenn user erneut klickt vor Abschluss → Race condition
}
```

**Status**: MITTEL
**Fix**: AbortController für alle query modes

#### Problem: Plan Mode Conversation Trimming redundant
```typescript
// usePlanModeSSE.ts - trimConversation()
function trimConversation(): void {
  if (conversation.value.length > TRIM_THRESHOLD) {
    // Trimmt auf TRIM_TARGET Nachrichten
  }
}

// usePlanModeCore.ts - ebenfalls trimConversation()
function trimConversation(): void {
  // DUPLIZIERT - gleiche Logik zweimal
}
```

**Status**: LOW
**Fix**: Logik zentralisieren in usePlanModeSSE

### 3. MODE SWITCHING - Zustandsübergänge unklar

#### Problem: Mode-Wechsel-Validierung fehlt
```typescript
// SmartQueryToolbar - Mode-Wechsel
v-model:mode="currentMode"

// LÜCKE: Keine Validierung
// - Wenn Daten in Preview vorhanden → Wechsel löscht Preview (ok)
// - Wenn Plan Mode läuft → Wechsel bricht Streaming ab? (nicht getestet)
// - Wenn Write läuft → Kann zu Read gewechselt werden? (sollte nicht erlaubt sein)

// Result: Zustand könnte inkonsistent werden
```

**Status**: HOCH
**Fix**: Mode-Wechsel-Guards implementieren

#### Problem: Plan Mode generatedPrompt wird ignoriert
```typescript
// In usePlanModeSSE.ts - analyzeResponseForPrompt()
results.value = {
  success: true,
  message: responseText,
  has_generated_prompt: true,
  generated_prompt: generatedPromptText,
  suggested_mode: suggestedMode,
  mode: 'plan',
}

// Aber in SmartQueryView.vue:
@adopt-prompt="adoptPrompt"  // Component emits this

// LÜCKE: SmartQueryInput.vue rendert generatedPrompt
// aber Adoption zur Execution Transition unklar
```

**Status**: MITTEL
**Fix**: Dokumentieren adoptPrompt Flow

### 4. CONTEXT PASSING - Daten-Verlust Risiken

#### Problem: Entity Context wird bei Attachment Analyse nicht bewahrt
```typescript
// In useSmartQueryCore.ts - executeWithAttachments()
const response = await assistantApi.chat({
  message: question.value.trim() || 'Analysiere das Bild',
  context: {
    current_route: '/smart-query',
    current_entity_id: null,       // LÜCKE: Immer null!
    current_entity_type: null,     // LÜCKE: Immer null!
    current_entity_name: null,     // LÜCKE: Immer null!
    view_mode: 'unknown',
    available_actions: [],
  },
  // ...
})

// Falls User von EntityDetail zu Smart Query wechselt mit Attachment
// → Entity Context geht verloren
```

**Status**: MITTEL
**Fix**: Entity Context aus URL-Parametern initialisieren

#### Problem: Results werden nicht bei Mode-Wechsel gelöscht
```typescript
// In handleVisualizationAction()
function handleVisualizationAction(action: string, params) {
  switch (action) {
    case 'setup_sync':
      currentMode.value = 'write'  // Mode wechselt
      question.value = '...'        // Question setzt
      // LÜCKE: results.value wird nicht gelöscht!
      // Alte Ergebnisse bleiben sichtbar während neue Query lädt
      break
  }
}
```

**Status**: LOW
**Fix**: `results.value = null` vor Mode-Wechsel setzen

### 5. RESULTS HANDLING - Typisierungsprobleme

#### Problem: results.data vs results.items Inkonsistenz
```typescript
interface SmartQueryResults {
  items?: Record<string, unknown>[]  // Primary
  data?: Record<string, unknown>[]   // Legacy field
}

// In verschiedenen Code-Pfaden:
results.value.items || results.value.data  // Notwendig zur Fallback-Handling
// Aber: Data-Type nicht klar dokumentiert
```

**Status**: LOW
**Fix**: Legacy data field deprecieren/dokumentieren

#### Problem: visualization[s] Plural inconsistent
```typescript
interface SmartQueryResults {
  visualization?: SmartQueryVisualization   // Single
  visualizations?: SmartQueryVisualization[] // Multiple
}

// In SmartQueryResults.vue:
v-else-if="results?.visualization && !results?.is_compound"  // Single
v-if="results?.is_compound"  // Uses compoundVisualizations computed

// LÜCKE: Unklar wann visualization vs visualizations verwendet wird
// Depends on is_compound flag
```

**Status**: MITTEL
**Fix**: Klarer in Types dokumentieren (single query → visualization, compound → visualizations)

### 6. INTEGRATION MIT ASSISTANT - Bidirektionalität fragil

#### Problem: context consuming ist nicht-atomisch
```typescript
// In queryContext.ts
function consumeContext(): QueryContextData | null {
  const context = pendingContext.value
  pendingContext.value = null  // Sofort gelöscht
  return context
}

// LÜCKE: Falls initializeFromContext() Fehler wirft
// → Context ist bereits gelöscht
// → Retry nicht möglich

// Szenario:
// 1. Assistant setzt Context
// 2. SmartQueryView mounted
// 3. initializeFromContext() ruft consumeContext() auf
// 4. executeQuery() Fehler → User kann nicht retry mit gleichen Daten
```

**Status**: MITTEL
**Fix**: Soft-delete Pattern oder Flag für "processed"

#### Problem: returnToAssistant Flag management unklar
```typescript
// In queryContext.ts
return returnToAssistant.value  // Getter

clearReturnFlag()  // Setter

// LÜCKE: Keine klare Stelle wo Flag gesetzt/gelöscht wird
// Wer ruft clearReturnFlag() auf?
// Smart Query? Assistant? Wann?

// Suche: Nur setFromAssistant() setzt es auf true
// Keine Stelle wo es wieder auf false gesetzt wird (außer clearAll)
```

**Status**: HOCH - Logik-Fehler
**Fix**: Flag clearing Logik nach router.back() hinzufügen

#### Problem: Results Format unterscheidet sich zwischen Modi
```typescript
// Read Mode Results:
{
  mode: 'read',
  items: [...],
  total: number,
  visualization: {...}
}

// Write Mode Results:
{
  mode: 'write',
  created_items: [...],
  message: string
}

// Assistant muss beide Formate verarbeiten
// queryContextStore.setResults() konvertiert aber:
items: results.value.items?.slice(0, 5) || 
       results.value.created_items?.slice(0, 5) || []

// LÜCKE: Semantischer Unterschied zwischen
// "items queried" vs "items created" ist verloren
```

**Status**: LOW
**Fix**: In QueryResultData type field for 'read' vs 'write' unterscheiden

---

## FEHLENDE TESTS

### Frontend Unit Tests
- useSmartQueryCore.ts - keine Tests (großes Composable)
- usePlanModeCore.ts - hat tests aber incomplete coverage
- useSmartQueryAttachments.ts - keine Tests für error paths

### Frontend Integration Tests
- Context Passing (Assistant ↔ SmartQuery)
- Mode Switching während Query lädt
- Attachment Upload Error → Recovery
- Plan Mode Streaming Timeout

### Backend Unit Tests
- interpret_plan_query_stream() Timeout handling
- Conversation sanitization edge cases
- Prompt injection patterns

---

## QUALITÄTS-METRIKEN

### Code Organization: ⭐⭐⭐⭐⭐
- Frontend modulare Struktur (smartquery/, planmode/)
- Backend interpreters/ aufgeteilt
- Backward compatibility erhalten

### Type Safety: ⭐⭐⭐⭐
- Gute TypeScript Types
- Aber: visualization/visualizations plural inconsistent
- SmartQueryResults hat legacy fields

### Error Handling: ⭐⭐⭐
- Gute backend Fehler-Meldungen
- Frontend: Attachment error handling incomplete
- Keine Streaming-Timeout auf Frontend

### Performance: ⭐⭐⭐⭐
- TTL Caching für Typen (5 min)
- Rate Limiting (30/min für AI)
- Lazy Komponenten-Loading

### Security: ⭐⭐⭐⭐⭐
- Prompt Injection Protection
- Query Sanitization
- Conversation History Trimming
- No hardcoded credentials

---

## RECOMMENDATIONS (PRIORITÄT)

### KRITISCH
1. [ ] Attachment Upload Error: `isUploading.value = false` hinzufügen
2. [ ] returnToAssistant Flag Cleanup nach Navigation
3. [ ] Mode-Wechsel Guards implementieren

### HOCH
4. [ ] Frontend Streaming Timeout nach 130s
5. [ ] Race Condition Prevention mit AbortController für alle modes
6. [ ] Entity Context Preservation bei Attachment Analysis

### MITTEL
7. [ ] Soft-delete Pattern für Context Consuming
8. [ ] Plan Mode adoptPrompt Flow dokumentieren
9. [ ] visualization vs visualizations dokumentieren

### LOW
10. [ ] Conversation Trimming Logic zentralisieren
11. [ ] Legacy data field deprecieren
12. [ ] Results clearing bei Mode-Wechsel (cosmetic)
