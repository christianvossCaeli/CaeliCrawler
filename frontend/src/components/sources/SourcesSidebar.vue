<template>
  <v-navigation-drawer
    v-model="isOpen"
    :rail="isCollapsed"
    :permanent="!isMobile"
    :temporary="isMobile"
    width="280"
    class="sources-sidebar"
    role="navigation"
    :aria-label="$t('sources.sidebar.navigation')"
  >
    <div class="pa-3">
      <!-- Collapse Toggle -->
      <div class="d-flex justify-end mb-2" v-if="!isMobile">
        <v-btn
          :icon="isCollapsed ? 'mdi-chevron-right' : 'mdi-chevron-left'"
          variant="text"
          size="small"
          @click="isCollapsed = !isCollapsed"
          :title="isCollapsed ? $t('sources.sidebar.expand') : $t('sources.sidebar.collapse')"
          :aria-label="isCollapsed ? $t('sources.sidebar.expand') : $t('sources.sidebar.collapse')"
          :aria-expanded="!isCollapsed"
        />
      </div>

      <!-- Categories Section -->
      <div class="sidebar-section" v-if="!isCollapsed" role="group" aria-labelledby="categories-heading">
        <h3 id="categories-heading" class="text-overline text-medium-emphasis mb-2">{{ $t('sources.sidebar.categories') }}</h3>
        <v-list density="compact" nav role="listbox" :aria-label="$t('sources.sidebar.categories')">
          <v-list-item
            :active="!selectedCategory"
            @click="$emit('update:selectedCategory', null)"
            rounded="lg"
            role="option"
            :aria-selected="!selectedCategory"
          >
            <template v-slot:prepend>
              <v-icon size="small" aria-hidden="true">mdi-folder-multiple</v-icon>
            </template>
            <v-list-item-title>{{ $t('sources.sidebar.all') }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal" :aria-label="$t('sources.sidebar.itemCount', { count: counts.total })">{{ counts.total }}</v-chip>
            </template>
          </v-list-item>

          <v-list-item
            v-for="cat in displayedCategories"
            :key="cat.id"
            :active="selectedCategory === cat.id"
            @click="$emit('update:selectedCategory', cat.id)"
            rounded="lg"
            role="option"
            :aria-selected="selectedCategory === cat.id"
          >
            <template v-slot:prepend>
              <v-icon size="small" aria-hidden="true">mdi-folder</v-icon>
            </template>
            <v-list-item-title>{{ cat.name }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal" :aria-label="$t('sources.sidebar.itemCount', { count: cat.count })">{{ cat.count }}</v-chip>
            </template>
          </v-list-item>
          <!-- Show more/less button for categories -->
          <v-list-item
            v-if="hasMoreCategories"
            @click="showAllCategories = !showAllCategories"
            class="text-center"
            role="button"
            :aria-expanded="showAllCategories"
          >
            <v-list-item-title class="text-caption text-primary">
              {{ showAllCategories ? $t('common.showLess') : $t('common.showMore', { count: hiddenCategoriesCount }) }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </div>

      <v-divider class="my-3" v-if="!isCollapsed" />

      <!-- Types Section -->
      <div class="sidebar-section" v-if="!isCollapsed" role="group" aria-labelledby="types-heading">
        <h3 id="types-heading" class="text-overline text-medium-emphasis mb-2">{{ $t('sources.sidebar.types') }}</h3>
        <v-list density="compact" nav role="listbox" :aria-label="$t('sources.sidebar.types')">
          <v-list-item
            :active="!selectedType"
            @click="$emit('update:selectedType', null)"
            rounded="lg"
            role="option"
            :aria-selected="!selectedType"
          >
            <template v-slot:prepend>
              <v-icon size="small" aria-hidden="true">mdi-shape</v-icon>
            </template>
            <v-list-item-title>{{ $t('sources.sidebar.all') }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal" :aria-label="$t('sources.sidebar.itemCount', { count: typesTotal })">{{ typesTotal }}</v-chip>
            </template>
          </v-list-item>
          <v-list-item
            v-for="type in counts.types.filter(t => t.type)"
            :key="type.type || 'unknown'"
            :active="selectedType === type.type"
            @click="toggleType(type.type)"
            rounded="lg"
            role="option"
            :aria-selected="selectedType === type.type"
          >
            <template v-slot:prepend>
              <v-icon size="small" :color="getTypeColor(type.type)" aria-hidden="true">{{ getTypeIcon(type.type) }}</v-icon>
            </template>
            <v-list-item-title>{{ getTypeLabel(type.type) }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal" :color="getTypeColor(type.type)" :aria-label="$t('sources.sidebar.itemCount', { count: type.count })">{{ type.count }}</v-chip>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <v-divider class="my-3" v-if="!isCollapsed" />

      <!-- Status Section -->
      <div class="sidebar-section" v-if="!isCollapsed" role="group" aria-labelledby="status-heading">
        <h3 id="status-heading" class="text-overline text-medium-emphasis mb-2">{{ $t('sources.sidebar.status') }}</h3>
        <v-list density="compact" nav role="listbox" :aria-label="$t('sources.sidebar.status')">
          <v-list-item
            :active="!selectedStatus"
            @click="$emit('update:selectedStatus', null)"
            rounded="lg"
            role="option"
            :aria-selected="!selectedStatus"
          >
            <template v-slot:prepend>
              <v-icon size="small" aria-hidden="true">mdi-format-list-bulleted</v-icon>
            </template>
            <v-list-item-title>{{ $t('sources.sidebar.all') }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal" :aria-label="$t('sources.sidebar.itemCount', { count: statusesTotal })">{{ statusesTotal }}</v-chip>
            </template>
          </v-list-item>
          <v-list-item
            v-for="status in counts.statuses.filter(s => s.status)"
            :key="status.status || 'unknown'"
            :active="selectedStatus === status.status"
            @click="toggleStatus(status.status)"
            rounded="lg"
            role="option"
            :aria-selected="selectedStatus === status.status"
          >
            <template v-slot:prepend>
              <v-icon size="small" :color="getStatusColor(status.status)" aria-hidden="true">{{ getStatusIcon(status.status) }}</v-icon>
            </template>
            <v-list-item-title>{{ getStatusLabel(status.status) }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal" :color="getStatusColor(status.status)" :aria-label="$t('sources.sidebar.itemCount', { count: status.count })">{{ status.count }}</v-chip>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <v-divider class="my-3" v-if="!isCollapsed && availableTags.length > 0" />

      <!-- Tags Section -->
      <div class="sidebar-section" v-if="!isCollapsed && availableTags.length > 0" role="group" aria-labelledby="tags-heading">
        <h3 id="tags-heading" class="text-overline text-medium-emphasis mb-2">{{ $t('sources.sidebar.tags') }}</h3>
        <div class="tags-container" role="group" :aria-label="$t('sources.sidebar.tagsFilter')">
          <v-chip
            v-for="tag in displayedTags"
            :key="tag.tag"
            :color="isTagSelected(tag.tag) ? getTagColor(tag.tag) : 'default'"
            :variant="isTagSelected(tag.tag) ? 'flat' : 'outlined'"
            size="small"
            class="ma-1"
            @click="toggleTag(tag.tag)"
            @keydown.enter="toggleTag(tag.tag)"
            @keydown.space.prevent="toggleTag(tag.tag)"
            tabindex="0"
            role="checkbox"
            :aria-checked="isTagSelected(tag.tag)"
            :aria-label="$t('sources.sidebar.tagWithCount', { tag: tag.tag, count: tag.count })"
          >
            {{ tag.tag }}
            <span class="ml-1 text-caption" aria-hidden="true">({{ tag.count }})</span>
          </v-chip>
          <!-- Show more/less button for tags -->
          <v-chip
            v-if="hasMoreTags"
            color="primary"
            variant="text"
            size="small"
            class="ma-1"
            @click="showAllTags = !showAllTags"
            @keydown.enter="showAllTags = !showAllTags"
            tabindex="0"
            role="button"
            :aria-expanded="showAllTags"
            :aria-label="showAllTags ? $t('common.showLess') : $t('sources.sidebar.showMoreTags', { count: hiddenTagsCount })"
          >
            {{ showAllTags ? $t('common.showLess') : `+${hiddenTagsCount}` }}
          </v-chip>
          <v-chip
            v-if="selectedTags.length > 0"
            color="grey"
            variant="text"
            size="small"
            class="ma-1"
            @click="clearTags"
            @keydown.enter="clearTags"
            tabindex="0"
            role="button"
            :aria-label="$t('sources.filters.clearAllTags')"
          >
            <v-icon size="x-small" start aria-hidden="true">mdi-close</v-icon>
            {{ $t('sources.filters.clearAll') }}
          </v-chip>
        </div>
      </div>

      <!-- Collapsed Icons -->
      <div v-if="isCollapsed" class="collapsed-icons" role="group" :aria-label="$t('sources.sidebar.quickAccess')">
        <v-tooltip location="right" v-for="cat in counts.categories.slice(0, 5)" :key="cat.id">
          <template v-slot:activator="{ props }">
            <v-btn
              v-bind="props"
              icon="mdi-folder"
              variant="text"
              size="small"
              :color="selectedCategory === cat.id ? 'primary' : undefined"
              @click="$emit('update:selectedCategory', cat.id)"
              class="mb-1"
              :aria-label="$t('sources.sidebar.selectCategory', { name: cat.name, count: cat.count })"
              :aria-pressed="selectedCategory === cat.id"
            />
          </template>
          <span>{{ cat.name }} ({{ cat.count }})</span>
        </v-tooltip>
      </div>
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
/**
 * SourcesSidebar - Navigation sidebar for filtering sources
 *
 * Provides filters for categories, source types, statuses, and tags.
 * Supports collapsible sections and mobile-responsive drawer.
 */
import { ref, computed } from 'vue'
import { useDisplay } from 'vuetify'
import { useSourceHelpers } from '@/composables/useSourceHelpers'
import { SIDEBAR } from '@/config/sources'
import type {
  SidebarCounts,
  TagCount,
  SourceType,
  SourceStatus,
} from '@/types/sources'

const { mobile } = useDisplay()
const {
  getTypeColor,
  getTypeIcon,
  getTypeLabel,
  getStatusColor,
  getStatusIcon,
  getStatusLabel,
  getTagColor,
} = useSourceHelpers()

const props = defineProps<{
  counts: SidebarCounts
  selectedCategory: string | null
  selectedType: SourceType | null
  selectedStatus: SourceStatus | null
  selectedTags: string[]
  availableTags: TagCount[]
  modelValue?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:selectedCategory', value: string | null): void
  (e: 'update:selectedType', value: SourceType | null): void
  (e: 'update:selectedStatus', value: SourceStatus | null): void
  (e: 'update:selectedTags', value: string[]): void
  (e: 'update:modelValue', value: boolean): void
}>()

const isCollapsed = ref(false)
const isMobile = computed(() => mobile.value)

// Pagination for large lists using centralized config
const showAllCategories = ref(false)
const showAllTags = ref(false)

const displayedCategories = computed(() => {
  if (showAllCategories.value || props.counts.categories.length <= SIDEBAR.CATEGORY_INITIAL_LIMIT) {
    return props.counts.categories
  }
  return props.counts.categories.slice(0, SIDEBAR.CATEGORY_INITIAL_LIMIT)
})

const hasMoreCategories = computed(() => props.counts.categories.length > SIDEBAR.CATEGORY_INITIAL_LIMIT)
const hiddenCategoriesCount = computed(() => Math.max(0, props.counts.categories.length - SIDEBAR.CATEGORY_INITIAL_LIMIT))

const displayedTags = computed(() => {
  if (showAllTags.value || props.availableTags.length <= SIDEBAR.TAG_INITIAL_LIMIT) {
    return props.availableTags
  }
  return props.availableTags.slice(0, SIDEBAR.TAG_INITIAL_LIMIT)
})

const hasMoreTags = computed(() => props.availableTags.length > SIDEBAR.TAG_INITIAL_LIMIT)
const hiddenTagsCount = computed(() => Math.max(0, props.availableTags.length - SIDEBAR.TAG_INITIAL_LIMIT))

// Computed totals for "All" options
const typesTotal = computed(() => {
  return props.counts.types.reduce((sum, t) => sum + t.count, 0)
})

const statusesTotal = computed(() => {
  return props.counts.statuses.reduce((sum, s) => sum + s.count, 0)
})

const isOpen = computed({
  get: () => props.modelValue !== false,
  set: (val) => emit('update:modelValue', val)
})

const toggleType = (type: SourceType | null) => {
  if (!type) return
  emit('update:selectedType', props.selectedType === type ? null : type)
}

const toggleStatus = (status: SourceStatus | null) => {
  if (!status) return
  emit('update:selectedStatus', props.selectedStatus === status ? null : status)
}

// Tag functions
const isTagSelected = (tag: string) => props.selectedTags.includes(tag)

const toggleTag = (tag: string) => {
  const newTags = isTagSelected(tag)
    ? props.selectedTags.filter(t => t !== tag)
    : [...props.selectedTags, tag]
  emit('update:selectedTags', newTags)
}

const clearTags = () => {
  emit('update:selectedTags', [])
}
</script>

<style scoped>
.sources-sidebar {
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.sidebar-section {
  margin-bottom: 8px;
}

.collapsed-icons {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 8px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}
</style>
