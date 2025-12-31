/**
 * Categories Components Barrel Export
 *
 * Provides centralized exports for all category-related components.
 * Import from '@/components/categories' for cleaner imports.
 *
 * @example
 * ```typescript
 * import { CategoriesTree, CategoryDetailsPanel } from '@/components/categories'
 * ```
 */

// Main Components
export { default as CategoriesTree } from './CategoriesTree.vue'
export { default as CategoriesToolbar } from './CategoriesToolbar.vue'
export { default as CategoriesSkeleton } from './CategoriesSkeleton.vue'

// Details & Panels
export { default as CategoryDetailsPanel } from './CategoryDetailsPanel.vue'
export { default as CategoryEditForm } from './CategoryEditForm.vue'

// Form Sections
export { default as CategoryFormGeneral } from './CategoryFormGeneral.vue'
export { default as CategoryFormFilters } from './CategoryFormFilters.vue'
export { default as CategoryFormSearch } from './CategoryFormSearch.vue'
export { default as CategoryFormAi } from './CategoryFormAi.vue'

// Dialogs
export { default as CategoryAiPreviewDialog } from './CategoryAiPreviewDialog.vue'
export { default as CategoryCrawlerDialog } from './CategoryCrawlerDialog.vue'
export { default as CategorySourcesDialog } from './CategorySourcesDialog.vue'
export { default as CategoryReanalyzeDialog } from './CategoryReanalyzeDialog.vue'
