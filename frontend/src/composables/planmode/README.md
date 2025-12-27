# Plan Mode Composables

Vue 3 Composables für den Plan/Guide Mode im Smart Query Feature.

## Architektur

```
composables/planmode/
├── index.ts              # Re-Exports
├── types.ts              # Type-Definitionen
├── usePlanModeCore.ts    # Haupt-Composable
├── usePlanModeSSE.ts     # SSE Streaming
└── README.md
```

## Usage

```typescript
import { usePlanMode } from '@/composables/planmode'
import type { PlanMessage, GeneratedPrompt } from '@/composables/planmode'

const {
  conversation,
  loading,
  streaming,
  error,
  results,
  generatedPrompt,
  hasConversation,
  executePlanQuery,
  executePlanQueryStream,
  validatePrompt,
  reset,
} = usePlanMode()
```

## Features

### Non-Streaming Query

```typescript
const success = await executePlanQuery('Hilf mir bei der Suche')
```

### Streaming Query (SSE)

```typescript
const success = await executePlanQueryStream('Hilf mir bei der Suche')
```

### Prompt Validation

```typescript
const result = await validatePrompt('Zeige alle Gemeinden', 'read')
if (result?.valid) {
  // Prompt is valid
}
```

### Generated Prompts

```typescript
if (generatedPrompt.value) {
  const { prompt, suggested_mode } = generatedPrompt.value
  // Use the generated prompt
}
```

## Conversation Management

```typescript
// Check conversation state
if (hasConversation.value) {
  // Show conversation UI
}

// Check if near limit
if (isNearLimit.value) {
  // Warn user about conversation limit
}

// Reset conversation
reset()
```

## Types

```typescript
interface PlanMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
  isStreaming?: boolean
}

interface GeneratedPrompt {
  prompt: string
  suggested_mode?: 'read' | 'write'
}

interface ValidationResult {
  valid: boolean
  mode: string
  interpretation: Record<string, unknown> | null
  preview: string | null
  warnings: string[]
  original_prompt: string
}
```

## Constants

```typescript
MAX_CONVERSATION_MESSAGES = 20  // Maximum messages before blocking
TRIM_THRESHOLD = 25             // When to trim conversation
TRIM_TARGET = 20                // Target size after trimming
```

## Tests

```bash
npm run test -- src/composables/planmode
```

## Backward Compatibility

Bestehende Imports funktionieren weiterhin:

```typescript
// Alt (funktioniert noch)
import { usePlanMode } from '@/composables/usePlanMode'

// Neu (empfohlen)
import { usePlanMode } from '@/composables/planmode'
```
