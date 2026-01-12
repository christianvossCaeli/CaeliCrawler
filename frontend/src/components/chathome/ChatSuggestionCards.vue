<template>
  <div class="chat-suggestions">
    <!-- Category Filter -->
    <div class="chat-suggestions__categories">
      <button
        v-for="category in categories"
        :key="category.id"
        class="category-chip"
        :class="{ 'category-chip--active': activeCategory === category.id }"
        @click="activeCategory = category.id"
      >
        <v-icon size="14" class="mr-1">{{ category.icon }}</v-icon>
        {{ category.label }}
      </button>
    </div>

    <!-- Suggestions Grid -->
    <div class="chat-suggestions__grid">
      <div
        v-for="suggestion in filteredSuggestions"
        :key="suggestion.id"
        class="suggestion-card"
        @click="$emit('select', suggestion.query)"
      >
        <div class="suggestion-card__icon" :class="`suggestion-card__icon--${suggestion.category}`">
          <v-icon size="20">{{ suggestion.icon }}</v-icon>
        </div>
        <div class="suggestion-card__content">
          <div class="suggestion-card__title">{{ suggestion.title }}</div>
          <div class="suggestion-card__text">{{ suggestion.query }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface Suggestion {
  id: string
  title: string
  query: string
  icon: string
  category: 'query' | 'crawler' | 'summary'
}

defineEmits<{
  select: [query: string]
}>()

const { t } = useI18n()

const activeCategory = ref<string>('all')

const categories = computed(() => [
  { id: 'all', label: t('chatHome.categories.all'), icon: 'mdi-apps' },
  { id: 'query', label: t('chatHome.categories.query'), icon: 'mdi-magnify' },
  { id: 'crawler', label: t('chatHome.categories.crawler'), icon: 'mdi-spider-web' },
  { id: 'summary', label: t('chatHome.categories.summary'), icon: 'mdi-text-box-outline' },
])

const suggestions = computed<Suggestion[]>(() => [
  // Query suggestions
  {
    id: 'q1',
    title: t('chatHome.suggestions.showEntities.title'),
    query: t('chatHome.suggestions.showEntities.query'),
    icon: 'mdi-database-search',
    category: 'query'
  },
  {
    id: 'q2',
    title: t('chatHome.suggestions.countDocuments.title'),
    query: t('chatHome.suggestions.countDocuments.query'),
    icon: 'mdi-file-document-multiple',
    category: 'query'
  },
  {
    id: 'q3',
    title: t('chatHome.suggestions.searchDocuments.title'),
    query: t('chatHome.suggestions.searchDocuments.query'),
    icon: 'mdi-text-search',
    category: 'query'
  },
  // Crawler suggestions
  {
    id: 'c1',
    title: t('chatHome.suggestions.startCrawl.title'),
    query: t('chatHome.suggestions.startCrawl.query'),
    icon: 'mdi-play-circle-outline',
    category: 'crawler'
  },
  {
    id: 'c2',
    title: t('chatHome.suggestions.crawlerStatus.title'),
    query: t('chatHome.suggestions.crawlerStatus.query'),
    icon: 'mdi-information-outline',
    category: 'crawler'
  },
  {
    id: 'c3',
    title: t('chatHome.suggestions.retryCrawl.title'),
    query: t('chatHome.suggestions.retryCrawl.query'),
    icon: 'mdi-refresh',
    category: 'crawler'
  },
  // Summary suggestions
  {
    id: 's1',
    title: t('chatHome.suggestions.whatsNew.title'),
    query: t('chatHome.suggestions.whatsNew.query'),
    icon: 'mdi-bell-outline',
    category: 'summary'
  },
  {
    id: 's2',
    title: t('chatHome.suggestions.createSummary.title'),
    query: t('chatHome.suggestions.createSummary.query'),
    icon: 'mdi-text-box-plus-outline',
    category: 'summary'
  },
  {
    id: 's3',
    title: t('chatHome.suggestions.weeklyChanges.title'),
    query: t('chatHome.suggestions.weeklyChanges.query'),
    icon: 'mdi-calendar-week',
    category: 'summary'
  },
])

const filteredSuggestions = computed(() => {
  if (activeCategory.value === 'all') {
    return suggestions.value
  }
  return suggestions.value.filter(s => s.category === activeCategory.value)
})
</script>
