<template>
  <v-navigation-drawer
    v-model="isOpen"
    :rail="isCollapsed"
    :permanent="!isMobile"
    :temporary="isMobile"
    width="280"
    class="sources-sidebar"
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
        />
      </div>

      <!-- Categories Section -->
      <div class="sidebar-section" v-if="!isCollapsed">
        <div class="text-overline text-medium-emphasis mb-2">{{ $t('sources.sidebar.categories') }}</div>
        <v-list density="compact" nav>
          <v-list-item
            :active="!selectedCategory"
            @click="$emit('update:selectedCategory', null)"
            rounded="lg"
          >
            <template v-slot:prepend>
              <v-icon size="small">mdi-folder-multiple</v-icon>
            </template>
            <v-list-item-title>{{ $t('sources.sidebar.all') }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal">{{ counts.total }}</v-chip>
            </template>
          </v-list-item>

          <v-list-item
            v-for="cat in counts.categories"
            :key="cat.id"
            :active="selectedCategory === cat.id"
            @click="$emit('update:selectedCategory', cat.id)"
            rounded="lg"
          >
            <template v-slot:prepend>
              <v-icon size="small">mdi-folder</v-icon>
            </template>
            <v-list-item-title>{{ cat.name }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal">{{ cat.count }}</v-chip>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <v-divider class="my-3" v-if="!isCollapsed" />

      <!-- Types Section -->
      <div class="sidebar-section" v-if="!isCollapsed">
        <div class="text-overline text-medium-emphasis mb-2">{{ $t('sources.sidebar.types') }}</div>
        <v-list density="compact" nav>
          <v-list-item
            :active="!selectedType"
            @click="$emit('update:selectedType', null)"
            rounded="lg"
          >
            <template v-slot:prepend>
              <v-icon size="small">mdi-shape</v-icon>
            </template>
            <v-list-item-title>{{ $t('sources.sidebar.all') }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal">{{ typesTotal }}</v-chip>
            </template>
          </v-list-item>
          <v-list-item
            v-for="type in counts.types.filter(t => t.type)"
            :key="type.type || 'unknown'"
            :active="selectedType === type.type"
            @click="toggleType(type.type)"
            rounded="lg"
          >
            <template v-slot:prepend>
              <v-icon size="small" :color="getTypeColor(type.type)">{{ getTypeIcon(type.type) }}</v-icon>
            </template>
            <v-list-item-title>{{ getTypeLabel(type.type) }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal" :color="getTypeColor(type.type)">{{ type.count }}</v-chip>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <v-divider class="my-3" v-if="!isCollapsed" />

      <!-- Status Section -->
      <div class="sidebar-section" v-if="!isCollapsed">
        <div class="text-overline text-medium-emphasis mb-2">{{ $t('sources.sidebar.status') }}</div>
        <v-list density="compact" nav>
          <v-list-item
            :active="!selectedStatus"
            @click="$emit('update:selectedStatus', null)"
            rounded="lg"
          >
            <template v-slot:prepend>
              <v-icon size="small">mdi-format-list-bulleted</v-icon>
            </template>
            <v-list-item-title>{{ $t('sources.sidebar.all') }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal">{{ statusesTotal }}</v-chip>
            </template>
          </v-list-item>
          <v-list-item
            v-for="status in counts.statuses.filter(s => s.status)"
            :key="status.status || 'unknown'"
            :active="selectedStatus === status.status"
            @click="toggleStatus(status.status)"
            rounded="lg"
          >
            <template v-slot:prepend>
              <v-icon size="small" :color="getStatusColor(status.status)">{{ getStatusIcon(status.status) }}</v-icon>
            </template>
            <v-list-item-title>{{ getStatusLabel(status.status) }}</v-list-item-title>
            <template v-slot:append>
              <v-chip size="x-small" variant="tonal" :color="getStatusColor(status.status)">{{ status.count }}</v-chip>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <v-divider class="my-3" v-if="!isCollapsed && availableTags.length > 0" />

      <!-- Tags Section -->
      <div class="sidebar-section" v-if="!isCollapsed && availableTags.length > 0">
        <div class="text-overline text-medium-emphasis mb-2">{{ $t('sources.sidebar.tags') }}</div>
        <div class="tags-container">
          <v-chip
            v-for="tag in availableTags.slice(0, 15)"
            :key="tag.tag"
            :color="isTagSelected(tag.tag) ? getTagColor(tag.tag) : 'default'"
            :variant="isTagSelected(tag.tag) ? 'flat' : 'outlined'"
            size="small"
            class="ma-1"
            @click="toggleTag(tag.tag)"
          >
            {{ tag.tag }}
            <span class="ml-1 text-caption">({{ tag.count }})</span>
          </v-chip>
          <v-chip
            v-if="selectedTags.length > 0"
            color="grey"
            variant="text"
            size="small"
            class="ma-1"
            @click="clearTags"
          >
            <v-icon size="x-small" start>mdi-close</v-icon>
            {{ $t('sources.filters.clearAll') }}
          </v-chip>
        </div>
      </div>

      <!-- Collapsed Icons -->
      <div v-if="isCollapsed" class="collapsed-icons">
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
            />
          </template>
          <span>{{ cat.name }} ({{ cat.count }})</span>
        </v-tooltip>
      </div>
    </div>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDisplay } from 'vuetify'
import { useSourceHelpers } from '@/composables/useSourceHelpers'

const { mobile } = useDisplay()
const {
  getTypeColor,
  getTypeIcon,
  getTypeLabel,
  getStatusColor,
  getStatusIcon,
  getStatusLabel,
} = useSourceHelpers()

interface CategoryCount {
  id: string
  name: string
  slug: string
  count: number
}

interface TypeCount {
  type: string
  count: number
}

interface StatusCount {
  status: string
  count: number
}

interface TagCount {
  tag: string
  count: number
}

interface Counts {
  total: number
  categories: CategoryCount[]
  types: TypeCount[]
  statuses: StatusCount[]
}

const props = defineProps<{
  counts: Counts
  selectedCategory: string | null
  selectedType: string | null
  selectedStatus: string | null
  selectedTags: string[]
  availableTags: TagCount[]
  modelValue?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:selectedCategory', value: string | null): void
  (e: 'update:selectedType', value: string | null): void
  (e: 'update:selectedStatus', value: string | null): void
  (e: 'update:selectedTags', value: string[]): void
  (e: 'update:modelValue', value: boolean): void
}>()

const isCollapsed = ref(false)
const isMobile = computed(() => mobile.value)

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

const toggleType = (type: string) => {
  emit('update:selectedType', props.selectedType === type ? null : type)
}

const toggleStatus = (status: string) => {
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

// Color mapping for tags based on type
const getTagColor = (tag: string): string => {
  const tagLower = tag?.toLowerCase() || ''
  // Geographic regions
  if (['nrw', 'bayern', 'baden-württemberg', 'niedersachsen', 'hessen', 'sachsen',
       'rheinland-pfalz', 'berlin', 'schleswig-holstein', 'brandenburg',
       'sachsen-anhalt', 'thüringen', 'hamburg', 'mecklenburg-vorpommern',
       'saarland', 'bremen', 'nordrhein-westfalen'].includes(tagLower)) {
    return 'blue'
  }
  // Countries
  if (['deutschland', 'österreich', 'schweiz', 'de', 'at', 'ch', 'uk'].includes(tagLower)) {
    return 'indigo'
  }
  // Source types
  if (['kommunal', 'gemeinde', 'stadt', 'landkreis', 'landesebene', 'kreis'].includes(tagLower)) {
    return 'green'
  }
  // API types
  if (['oparl', 'rss', 'api'].includes(tagLower)) {
    return 'purple'
  }
  return 'grey'
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
