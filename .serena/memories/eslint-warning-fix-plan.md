# ESLint Warning Fix Plan

## Warning Categories (757 total)

| Priority | Rule | Count | Complexity | Approach |
|----------|------|-------|------------|----------|
| 1 | `vue/prefer-true-attribute-shorthand` | 17 | Easy | Auto-fixable pattern: `:prop="true"` → `prop` |
| 2 | `@typescript-eslint/no-unused-vars` | 13 | Easy | Remove or prefix with `_` |
| 3 | `no-useless-escape` | 3 | Easy | Remove unnecessary `\` |
| 4 | `no-case-declarations` | 2 | Easy | Wrap case blocks in `{}` |
| 5 | `@ts-ignore` → `@ts-expect-error` | 4 | Easy | Simple text replace |
| 6 | `vue/no-required-prop-with-default` | 1 | Easy | Make prop optional |
| 7 | `no-control-regex` | 1 | Easy | Fix regex pattern |
| 8 | `vue/no-template-shadow` | 36 | Medium | Rename slot variables |
| 9 | `@typescript-eslint/no-empty-object-type` | 8 | Medium | Add `Record<string, never>` or proper type |
| 10 | `@typescript-eslint/no-non-null-assertion` | 38 | Medium | Add null checks or optional chaining |
| 11 | `vue/no-static-inline-styles` | 50 | Medium | Move to CSS classes |
| 12 | `no-console` | 49 | Medium | Replace with logger or remove |
| 13 | `vue/no-v-html` | 6 | Skip | Intentional - keep as warning |
| 14 | `vue/one-component-per-file` | 2 | Skip | Intentional - keep as warning |
| 15 | `@typescript-eslint/no-explicit-any` | 515 | Hard | Requires proper typing |

## Execution Plan

### Phase 1: Quick Wins (Auto-fixable/Simple patterns)
1. Fix `vue/prefer-true-attribute-shorthand` (17)
2. Fix `@typescript-eslint/no-unused-vars` (13)
3. Fix `no-useless-escape` (3)
4. Fix `no-case-declarations` (2)
5. Fix `@ts-ignore` → `@ts-expect-error` (4)
6. Fix `vue/no-required-prop-with-default` (1)
7. Fix `no-control-regex` (1)

### Phase 2: Medium Complexity
1. Fix `vue/no-template-shadow` (36) - rename slot variables
2. Fix `@typescript-eslint/no-empty-object-type` (8)
3. Fix `@typescript-eslint/no-non-null-assertion` (38)
4. Fix `vue/no-static-inline-styles` (50)
5. Fix `no-console` in source files (49)

### Phase 3: Type Improvements
1. Fix `@typescript-eslint/no-explicit-any` (515) - by file/component

## Files with Most Warnings
- PySisTab.vue (30+ any types)
- EntityDialogsManager.vue (16+ any types)
- ResultsView.vue (14+ any types)
- DocumentsView.vue (14+ any types)
