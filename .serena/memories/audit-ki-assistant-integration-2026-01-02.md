# KI Assistant Integration Audit (2026-01-02)

## Executive Summary

**Overall Rating: 4.5/5 Stars** - Well-architected with modular composables, but several integration issues and code duplication require attention.

### Key Findings

1. **Duplicate Code**: `escapeHtml()` function duplicated across 4 components
2. **Missing Imports**: `ChatAssistant.vue` defines local `formatMessage()` instead of using shared utility
3. **Inconsistent Error Handling**: Not all sub-composables properly propagate errors
4. **Resource Cleanup**: Batch polling interval not cleaned up in all exit paths
5. **Streaming Timeout**: No timeout mechanism for SSE streams
6. **State Pollution**: Two chat components (ChatAssistant vs ChatWindow) with overlapping functionality

---

## 1. CHAT COMPONENTS ARCHITECTURE

### 1.1 ChatAssistant.vue vs ChatWindow.vue - DUPLICATION DETECTED

**Location**: `/frontend/src/components/assistant/`

#### ChatAssistant.vue (27KB)
- Standalone FAB-based chat interface
- Self-contained UI with full styling
- ~460 lines of template + 170 lines of script
- Used in `App.vue` as global chat
- **Issues**:
  - Defines local `formatMessage()` function (lines 430-432)
  - Does NOT import from `@/utils/messageFormatting`
  - Only uses `formatMessageTime()` from utility
  - Inline styles (~580 lines of scoped CSS)

#### ChatWindow.vue (23KB)
- Dialog/window-based chat component
- Accepts props, emits events
- ~335 lines of template + 280 lines of script
- **Issues**:
  - Fully props-driven (no direct composable usage)
  - Uses Vuetify components (v-textarea, v-chip, etc.)
  - NOT using shared `formatMessage()` utility
  - Imports ChatMessage sub-component which HAS DOMPurify

#### Overlap Analysis
```
Feature          ChatAssistant    ChatWindow
─────────────────────────────────────────────────
Message render       ✓               (ChatMessage)
Quick actions        ✓               QuickActionsPanel
Mode toggle          ✓               ✓
History panel        ✗               QueryHistoryPanel
Attachment upload    ✓               ✓
Voice input          ✗               ✓ (useSpeechRecognition)
Wizard support       ✗               ✓ (WizardStep)
Batch operations     ✗               ✓
Insights display     ✗               ✓ (on welcome)
```

**Problem**: Two parallel implementations that could confuse developers about which to use.

---

## 2. MESSAGE RENDERING CONSISTENCY ISSUES

### 2.1 Multiple `formatMessage()` Definitions

**Found 4 implementations** (should be 1):

1. **`/utils/messageFormatting.ts`** (CANONICAL - 48 lines)
   - Exports: `escapeHtml()`, `formatMessage()`, `formatMessageTime()`, `formatRelativeTime()`
   - Uses: DOMPurify sanitization
   - ALLOWED_TAGS: `['strong', 'code', 'br', 'span']`
   - ALLOWED_ATTR: `['class']`

2. **`ChatMessage.vue`** (244-268 lines) - LOCAL DUPLICATE
   - Defines: `escapeHtml()` (233-242)
   - Defines: `formatMessage()` (244-268)
   - ALLOWED_TAGS: `['strong', 'code', 'br', 'span']`
   - ALLOWED_ATTR: `['class', 'data-type', 'data-slug', 'role', 'tabindex']`
   - ✓ Imports DOMPurify from 'dompurify'

3. **`ChatAssistant.vue`** - MISSING/INDIRECT
   - Imports: `formatMessage, formatMessageTime` from `@/utils/messageFormatting`
   - But line 142 comment says "Content is sanitized via DOMPurify in formatMessage"
   - Actually uses the utility correctly

4. **`InputHints.vue`** (234-242 lines) - LOCAL DUPLICATE
   - Defines: `escapeHtml(str)` locally
   - Purpose: For hint text escaping

5. **`WizardStep.vue`** (383-391 lines) - LOCAL DUPLICATE
   - Defines: `escapeHtml(text)` locally
   - Purpose: For question text escaping

6. **`PlanModeChat.vue`** (smartquery) - LOCAL DUPLICATE
   - Defines: `escapeHtml(text)` locally

### 2.2 XSS Protection Variance

**Issue**: ALLOWED_ATTR differ between implementations

- **Utility** (`messageFormatting.ts`): `['class']`
- **ChatMessage.vue**: `['class', 'data-type', 'data-slug', 'role', 'tabindex']`

**Impact**: ChatMessage component allows additional attributes needed for entity-chip functionality, but this is inconsistent with the "canonical" utility.

**Better Approach**: The utility should include all necessary attributes:
```typescript
ALLOWED_ATTR: ['class', 'data-type', 'data-slug', 'role', 'tabindex']
```

---

## 3. STREAMING RESPONSE HANDLING

### 3.1 Streaming Implementation (GOOD)

**Location**: `useAssistant/index.ts` lines 246-428

**Strengths**:
- ✓ Uses AbortController for cancellation (line 268)
- ✓ Proper SSE parsing with TextDecoder (lines 311-392)
- ✓ Handles multiple data types: status, intent, token, item, complete, error (lines 339-386)
- ✓ Graceful AbortError handling (line 408)
- ✓ Cleanup in finally block (lines 420-427)

**Weaknesses**:

1. **No Timeout for Stalled Streams**
   ```typescript
   // Missing: timeout after X seconds of no data
   const timeoutId = setTimeout(() => {
     streamingAbortController.value?.abort()
   }, 30000) // 30 second timeout
   ```

2. **No Retry Mechanism**
   - Network failures cause immediate failure
   - No exponential backoff for transient errors
   - Could benefit from retry on HTTP 5xx errors

3. **Incomplete Error Context**
   ```typescript
   // Line 407-419: Only captures error.name and error.message
   // Missing: distinguish between:
   // - Network timeout vs AbortError vs parse error vs server error
   ```

4. **SSE [DONE] Marker Handling**
   ```typescript
   // Line 332: Just continues without processing
   if (dataStr === '[DONE]') {
     continue  // ← Could be more explicit
   }
   ```

### 3.2 SSE Error Recovery

**Current Behavior**:
- If reader fails → AbortError handler (line 408)
- If JSON parse fails → Logs error, continues (line 387-389)
- If network drops → Fetch error → Generic error message

**Missing**: 
- Retry logic for network errors
- Timeout handling for slow/stalled streams
- Partial result recovery

---

## 4. COMPOSABLES ARCHITECTURE

### 4.1 Modular Design (EXCELLENT)

**Structure**: `useAssistant` (main) delegates to 6 sub-composables

```
useAssistant (index.ts - 807 lines)
├── useAssistantHistory
│   ├── loadHistory()
│   ├── saveHistory()
│   ├── loadQueryHistory()
│   ├── saveQueryHistory()
│   ├── addQueryToHistory()
│   ├── toggleQueryFavorite()
│   ├── removeQueryFromHistory()
│   └── clearQueryHistory()
├── useAssistantAttachments
│   ├── uploadAttachment()
│   ├── removeAttachment()
│   ├── clearAttachments()
│   ├── getAttachmentIcon()
│   ├── formatFileSize()
│   └── saveAttachmentsToEntity()
├── useAssistantBatch
│   ├── executeBatchAction()
│   ├── confirmBatchAction()
│   ├── cancelBatchAction()
│   ├── closeBatchProgress()
│   └── [Polling: 2-second intervals]
├── useAssistantWizard
│   ├── startWizard()
│   ├── submitWizardResponse()
│   ├── wizardGoBack()
│   └── cancelWizard()
├── useAssistantReminders
│   ├── loadReminders()
│   ├── loadDueReminders()
│   ├── createReminder()
│   ├── dismissReminder()
│   ├── deleteReminder()
│   ├── snoozeReminder()
│   └── [Polling: reminder checks]
└── useAssistantInsights
    ├── loadSlashCommands()
    ├── loadSuggestions()
    ├── loadInsights()
    └── handleInsightAction()
```

**Strengths**:
- ✓ Separation of concerns
- ✓ Each sub-composable focused on single domain
- ✓ Shared state passed as options
- ✓ Consistent error handling pattern

### 4.2 State Management Issues

**Problem 1: Shared State Mutation**
```typescript
// Line 117-122: Sub-composables receive refs to parent state
const history = useAssistantHistory({ messages })
const attachments = useAssistantAttachments({ messages, error, saveHistory })
```

**Risk**: Any sub-composable can mutate parent state indirectly
**Mitigation**: Currently acceptable as sub-composables are internal only

**Problem 2: Cross-Sub-Composable Dependencies**
```typescript
// Line 562-567: Wizard depends on history.saveHistory
const wizard = useAssistantWizard({
  messages,
  error,
  currentContext,
  saveHistory: history.saveHistory,  // ← Tight coupling
})
```

**Impact**: Can't test wizard independently, saveHistory must exist from history composable

---

## 5. FEATURES INTEGRATION

### 5.1 Batch Operations

**Status**: FUNCTIONAL with polling cleanup issue

**Location**: `useAssistantBatch.ts`

**Polling Implementation** (lines 56-91):
```typescript
batchPollInterval = setInterval(async () => {
  // Poll every 2 seconds
  // Stop when status in ['completed', 'failed', 'cancelled']
}, 2000)
```

**Cleanup Issue**: 
- ✓ `stopBatchPolling()` called on completion (line 75)
- ✓ `cleanup()` exposed and called on unmount (App.vue)
- ✗ But if batch remains active and component unmounts → memory leak
  - `batchPollInterval` continues polling
  - No check in `onUnmounted` of main composable

### 5.2 Wizards

**Status**: INTEGRATED but no timeout

**Features**:
- Multi-step forms with validation
- Back/forward navigation
- Progress indication
- Async response handling

**Issue**: No step timeout
- User could leave wizard step idle indefinitely
- Server maintains wizard session
- No auto-cancel after inactivity

### 5.3 Reminders

**Status**: POLLING-BASED, not reactive

**Implementation** (useAssistantReminders):
```typescript
function startReminderPolling() {
  interval = setInterval(async () => {
    const reminders = await assistantApi.getDueReminders()
    // Update due reminders
  }, 30000)  // 30 second poll
}
```

**Problems**:
1. 30-second latency for reminder notifications
2. No server-sent events or websocket support
3. Polling continues even when chat closed
4. No cleanup verification

**Better Approach**: Use WebSocket or Server-Sent Events for real-time updates

### 5.4 Insights

**Status**: STATIC, loaded on mount

**Issues**:
- Loaded once on `onMounted`
- Reloaded only on route change (line 711-714)
- No real-time updates
- No refresh trigger in UI

### 5.5 File Attachments

**Status**: WELL-IMPLEMENTED

**Location**: `useAssistantAttachments.ts`

**Features**:
- ✓ File type validation (PNG, JPEG, GIF, WebP, PDF)
- ✓ Size limit enforcement (10MB max)
- ✓ Image preview generation
- ✓ Graceful error handling
- ✓ Cleanup on send or manual remove

**Improvement**: Could support more file types (DOC, XLS, CSV)

---

## 6. CONTEXT HANDLING

### 6.1 Route-Based Context Detection

**Location**: `useAssistant/index.ts` lines 76-114

**Implementation**:
```typescript
function detectViewMode(): AssistantContext['view_mode'] {
  const path = route.path
  
  if (path === '/' || path.includes('dashboard')) return 'dashboard'
  if (route.params.entitySlug) return 'detail'
  if (path.includes('/entities') || path.includes('/sources') || path.includes('/categories')) return 'list'
  return 'unknown'
}

function getAvailableActions(): string[] {
  const actions: string[] = ['search', 'help']
  
  if (route.params.entitySlug) {
    actions.push('view_details', 'edit', 'summarize')
  }
  if (route.params.typeSlug) {
    actions.push('filter', 'create')
  }
  
  return actions
}
```

**Issues**:

1. **Fragile Path Detection**
   - Uses string matching instead of route names
   - Won't work if routes change
   - No validation of params existence

2. **Hard-coded View Modes**
   - Missing 'edit' path detection
   - No 'settings' or 'admin' modes
   - Doesn't account for query parameters

3. **Action Detection Too Simplistic**
   - entitySlug might exist but be invalid
   - No permission checks
   - Hard-coded action lists

**Better Approach**:
```typescript
// Use route.name instead of path
// Validate params before assuming they exist
// Use permission checks from authStore
```

### 6.2 Entity Context

**Current Implementation**:
```typescript
current_entity_id: entityStore.selectedEntity?.id || null
current_entity_type: route.params.typeSlug as string || null
current_entity_name: entityStore.selectedEntity?.name || null
```

**Issues**:
- Falls back to route.params.typeSlug without validation
- selectedEntity might be null when navigating
- No sync between route params and entity store

### 6.3 Smart Query Integration

**Location**: Lines 589-656

**Features**:
- ✓ Context store integration (`queryContextStore.setFromAssistant()`)
- ✓ Query redirect to Smart Query with context
- ✓ Result consumption on return
- ✓ Bidirectional message flow

**Issues**:
- Context store used as simple prop passing mechanism
- No validation of Smart Query results format
- No error handling if results malformed

---

## 7. ERROR HANDLING

### 7.1 Network Errors

**Current Handling**:
```typescript
// Line 223-231: sendMessage()
catch (e: unknown) {
  error.value = extractErrorMessage(e)
  const errorMessage: ConversationMessage = {
    role: 'assistant',
    content: `Fehler: ${error.value}`,
    timestamp: new Date(),
    response_type: 'error'
  }
  messages.value.push(errorMessage)
}
```

**Issues**:
1. **No Error Classification**
   - Treats network timeout same as "invalid request"
   - No recovery suggestions to user

2. **No Retry Logic**
   - Immediate failure for any error
   - No exponential backoff
   - No "try again" button offered

3. **Error Messages to User**
   - Generic messages (just the HTTP error)
   - No helpful context
   - Not i18n-friendly (hardcoded "Fehler:")

### 7.2 Streaming Failures

**Location**: Lines 405-419

**Current Handling**:
```typescript
catch (e: unknown) {
  const err = e as { name?: string; message?: string }
  if (err.name === 'AbortError') {
    logger.info('Streaming request was cancelled')
    // Show cancellation message
  } else {
    error.value = err.message || 'Fehler bei der Streaming-Kommunikation'
    // Show error message
  }
}
```

**Missing Handlers**:
- ✗ Timeout errors
- ✗ Partial stream recovery (if got 50% of response)
- ✗ Network reconnection
- ✗ Server 5xx errors (no retry)

### 7.3 Attachment Upload Errors

**Location**: `useAssistantAttachments.ts` lines 36-78

**Current Handling**:
```typescript
catch (e: unknown) {
  error.value = extractErrorMessage(e)
  return false
}
```

**Good**: Simple and focused

**Missing**: 
- User-friendly error messages
- Retry suggestion for network errors
- Progress indication for large files

### 7.4 Batch Operation Errors

**Location**: `useAssistantBatch.ts` lines 87-90

```typescript
catch (e) {
  logger.error('Failed to poll batch status:', e)
  stopBatchPolling()
}
```

**Issues**:
- Polling stops on first error
- No retry with backoff
- Error not reported to user
- No distinction between temporary vs permanent failures

### 7.5 Reminder Polling Errors

**Missing Error Handling**:
- If reminder polling fails → no notification to user
- Continues polling indefinitely even after consecutive failures
- No exponential backoff

---

## 8. RESOURCE CLEANUP

### 8.1 Lifecycle Cleanup (PARTIAL)

**onUnmounted** (lines 703-708):
```typescript
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  batch.cleanup()  // ✓ Batch polling stops
  reminders.stopReminderPolling()  // ✓ Reminder polling stops
  cancelStreaming()  // ✓ Abort streaming
})
```

**Issues**:

1. **Missing Sub-Composable Cleanup**
   - `insights` has no cleanup method
   - `wizard` has no cleanup method
   - `attachments` has no cleanup method
   - `history` has no cleanup method

2. **No Memory Leak Detection**
   - No warning if cleanup incomplete
   - No automatic cleanup on long idle

### 8.2 Attachment Cleanup

**Implementation**:
```typescript
// Line 92-100: clearAttachments()
async function clearAttachments() {
  for (const attachment of pendingAttachments.value) {
    try {
      await assistantApi.deleteAttachment(attachment.id)
    } catch (e) {
      // Ignore delete errors
    }
  }
  pendingAttachments.value = []
}
```

**Good**: Server-side cleanup attempted

**Issue**: Ignores errors silently (better to log)

### 8.3 Batch Polling Cleanup

**Implementation** (lines 94-100):
```typescript
function stopBatchPolling() {
  if (batchPollInterval) {
    clearInterval(batchPollInterval)
    batchPollInterval = null
  }
}
```

**Good**: Explicit cleanup

**Issue**: Only exposed internally, relies on parent cleanup call

---

## 9. INTEGRATION ISSUES

### 9.1 Component Usage

**Only ChatAssistant.vue is used globally** (App.vue):
```typescript
import ChatAssistant from './components/assistant/ChatAssistant.vue'
```

**ChatWindow.vue is orphaned**:
- Not imported anywhere
- Exists for potential Dialog/modal usage
- Dead code or planned feature?

### 9.2 Backward Compatibility Layer

**File**: `useAssistant.ts` (26 lines)
```typescript
// Re-export from the main composable
export * from './assistant'
export { useAssistant as default } from './assistant'
```

**Good**: Maintains old import path
**Issue**: Two import paths confuse developers
- `import { useAssistant } from '@/composables/useAssistant'` (old)
- `import { useAssistant } from '@/composables/assistant'` (new)

### 9.3 Type Consistency

**Location**: `assistant/types.ts`

**Issues**:
- `ConversationMessage` has optional `metadata` field (never set)
- `ResponseData` has loose structure with `[key: string]: unknown`
- Index signatures allow API changes to silently pass through
- No strict typing for response formats per response_type

---

## 10. DUPLICATE CODE ANALYSIS

### 10.1 escapeHtml() Function

**Found in 4+ places** - should be 1 shared utility

| File | Type | Status |
|------|------|--------|
| `messageFormatting.ts` | Utility | CANONICAL ✓ |
| `ChatMessage.vue` | Component | DUPLICATE ✗ |
| `InputHints.vue` | Component | DUPLICATE ✗ |
| `WizardStep.vue` | Component | DUPLICATE ✗ |
| `PlanModeChat.vue` | Component | DUPLICATE ✗ |

**All implementations identical**, just define locally.

### 10.2 Message Formatting

**formatMessage() variations**:

1. **Utility version** - Does full formatting
2. **ChatMessage version** - Same but allows extra attributes

**Risk**: If one is fixed (security patch), others break.

---

## RECOMMENDATIONS (Priority Order)

### HIGH PRIORITY (Security/Stability)

1. **Consolidate message formatting**
   - Move ChatMessage's `escapeHtml()` to utility
   - Update utility `formatMessage()` ALLOWED_ATTR to include data-* attributes
   - Remove duplicate definitions from ChatMessage.vue, InputHints.vue, WizardStep.vue

2. **Add streaming timeout**
   - 30-second timeout for SSE streams
   - Auto-retry with exponential backoff
   - User-facing "try again" button

3. **Fix batch polling cleanup**
   - Add explicit cleanup verification
   - Warn if interval still running on unmount
   - Test with long-running batches

4. **Secure context detection**
   - Use route.name instead of path matching
   - Validate params before use
   - Add permission checks

### MEDIUM PRIORITY (Code Quality)

5. **Remove ChatWindow.vue or document its use**
   - Either integrate it or remove it
   - If keeping, add to App.vue and test both implementations

6. **Add comprehensive error recovery**
   - Implement retry logic for network errors
   - Add error classification (transient vs permanent)
   - Show retry buttons to user

7. **Improve sub-composable cleanup**
   - Add cleanup() methods to all sub-composables
   - Call them from main onUnmounted
   - Add warning if cleanup incomplete

8. **Consolidate escapeHtml() functions**
   - Export from messageFormatting.ts
   - Use throughout codebase

### LOW PRIORITY (Enhancements)

9. **Switch reminders to WebSocket**
   - Replace polling with server-push
   - Reduce latency from 30s to <1s

10. **Add idle timeout handling**
    - Cancel wizard after 10 minutes inactivity
    - Clean up batch polling if no updates
    - Show inactivity warning to user

11. **Improve action detection**
    - Use route.name instead of path
    - Cache available actions
    - Add permission checks

---

## Code Quality Metrics

| Metric | Score | Notes |
|--------|-------|-------|
| Modularity | 4.5/5 | Good separation, but ChatAssistant/ChatWindow duplication |
| Type Safety | 3.5/5 | Loose `ResponseData` structure, missing validation |
| Error Handling | 3/5 | Basic catch, no retry logic, no classification |
| Resource Cleanup | 3.5/5 | Partial cleanup, some sub-composables missing |
| Code Duplication | 2.5/5 | 4 duplicate escapeHtml functions |
| XSS Protection | 4/5 | DOMPurify used correctly, but attributes inconsistent |
| Streaming | 4/5 | Good SSE parsing, missing timeout and retry |
| Testing | Unknown | No test files found in audit scope |

---

## Files Analyzed

- `/frontend/src/composables/useAssistant.ts`
- `/frontend/src/composables/assistant/index.ts`
- `/frontend/src/composables/assistant/types.ts`
- `/frontend/src/composables/assistant/useAssistantHistory.ts`
- `/frontend/src/composables/assistant/useAssistantAttachments.ts`
- `/frontend/src/composables/assistant/useAssistantBatch.ts`
- `/frontend/src/components/assistant/ChatAssistant.vue`
- `/frontend/src/components/assistant/ChatWindow.vue`
- `/frontend/src/components/assistant/ChatMessage.vue`
- `/frontend/src/utils/messageFormatting.ts`
- `/frontend/src/services/api/ai.ts` (chat endpoints)

---

## Conclusion

The KI Assistant integration demonstrates solid architectural decisions with modular composables and proper state management. However, code duplication, missing error recovery mechanisms, and incomplete resource cleanup present maintenance and reliability risks. The presence of two chat components (ChatAssistant vs ChatWindow) creates confusion about intended usage.

Addressing the HIGH PRIORITY items (consolidating message formatting, adding streaming timeout, fixing cleanup) would significantly improve code quality and stability.
