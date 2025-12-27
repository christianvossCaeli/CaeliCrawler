# Smart Query Composables

Vue 3 Composables für das Smart Query Feature.

## Architektur

```
composables/smartquery/
├── index.ts                    # Re-Exports
├── types.ts                    # Type-Definitionen
├── useSmartQueryCore.ts        # Haupt-Composable
├── useSmartQueryAttachments.ts # Attachment-Handling
└── README.md
```

## Usage

```typescript
import { useSmartQuery } from '@/composables/smartquery'
import type { QueryMode, SmartQueryResults, LoadingState } from '@/composables/smartquery'

const {
  question,
  currentMode,
  loading,
  loadingState, // Granulare Loading States
  error,
  results,
  executeQuery,
} = useSmartQuery()
```

## Granulare Loading States

```typescript
interface LoadingState {
  isLoading: boolean
  phase: LoadingPhase
  progress?: number // 0-100
  message?: string
}

type LoadingPhase =
  | 'idle'
  | 'validating'
  | 'interpreting'
  | 'executing'
  | 'generating'
  | 'streaming'
  | 'processing'
```

### Verwendung in Templates

```vue
<template>
  <div v-if="loadingState.isLoading">
    <v-progress-linear
      :value="loadingState.progress"
      :indeterminate="!loadingState.progress"
    />
    <span>{{ loadingState.message }}</span>
  </div>
</template>
```

## Attachment Handling

```typescript
import { useSmartQueryAttachments } from '@/composables/smartquery'

const {
  pendingAttachments,
  isUploading,
  uploadAttachment,
  removeAttachment,
  clearAttachments,
} = useSmartQueryAttachments()

// Upload a file
const file = event.target.files[0]
await uploadAttachment(file)

// Get attachment IDs for API call
const ids = getAttachmentIds()
```

## Tests

```bash
npm run test -- src/composables/smartquery
```

## Backward Compatibility

Bestehende Imports funktionieren weiterhin:

```typescript
// Alt (funktioniert noch)
import { useSmartQuery } from '@/composables/useSmartQuery'

// Neu (empfohlen)
import { useSmartQuery } from '@/composables/smartquery'
```
