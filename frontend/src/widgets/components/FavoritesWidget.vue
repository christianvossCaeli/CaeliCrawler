<script setup lang="ts">
/**
 * FavoritesWidget - Dashboard widget showing user's favorite entities
 */

import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useFavoritesStore, type Favorite } from '@/stores/favorites'
import { handleKeyboardClick } from '../composables'
import BaseWidget from '../BaseWidget.vue'
import type { WidgetDefinition, WidgetConfig } from '../types'

const props = defineProps<{
  definition: WidgetDefinition
  config?: WidgetConfig
  isEditing?: boolean
}>()

const { t } = useI18n()
const router = useRouter()
const store = useFavoritesStore()
const loading = ref(true)
const error = ref<string | null>(null)

const refresh = async () => {
  loading.value = true
  error.value = null
  try {
    await store.loadFavorites({ page: 1 })
  } catch (e) {
    error.value = e instanceof Error ? e.message : t('common.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (store.favorites.length === 0) {
    refresh()
  } else {
    loading.value = false
  }
})

// Show max 8 favorites in widget
const favorites = computed(() => store.favorites.slice(0, 8))
const hasMore = computed(() => store.total > 8)

function navigateToEntity(fav: Favorite) {
  if (props.isEditing) return
  if (fav.entity.entity_type_slug && fav.entity.slug) {
    router.push({
      name: 'entity-detail',
      params: {
        typeSlug: fav.entity.entity_type_slug,
        entitySlug: fav.entity.slug,
      },
    })
  }
}

function navigateToFavorites() {
  if (props.isEditing) return
  router.push({ name: 'favorites' })
}

function handleKeydownEntity(event: KeyboardEvent, fav: Favorite) {
  handleKeyboardClick(event, () => navigateToEntity(fav))
}

function handleKeydownShowAll(event: KeyboardEvent) {
  handleKeyboardClick(event, () => navigateToFavorites())
}
</script>

<template>
  <BaseWidget
    :definition="definition"
    :config="config"
    :is-editing="isEditing"
    @refresh="refresh"
  >
    <div v-if="loading" class="d-flex justify-center py-6">
      <v-progress-circular indeterminate size="32" />
    </div>

    <v-list v-else-if="favorites.length > 0" density="compact" class="favorites-list" role="list">
      <v-list-item
        v-for="fav in favorites"
        :key="fav.id"
        class="px-2 clickable-item"
        :class="{ 'non-interactive': isEditing }"
        role="button"
        :tabindex="isEditing ? -1 : 0"
        :aria-label="fav.entity.name + ' - ' + fav.entity.entity_type_name"
        @click="navigateToEntity(fav)"
        @keydown="handleKeydownEntity($event, fav)"
      >
        <template #prepend>
          <v-avatar
            size="32"
            :color="fav.entity.entity_type_color || 'grey'"
            variant="tonal"
          >
            <v-icon
              :icon="fav.entity.entity_type_icon || 'mdi-folder'"
              size="small"
            />
          </v-avatar>
        </template>

        <v-list-item-title class="text-body-2">
          {{ fav.entity.name }}
        </v-list-item-title>
        <v-list-item-subtitle class="text-caption">
          {{ fav.entity.entity_type_name }}
        </v-list-item-subtitle>

        <template #append>
          <v-icon icon="mdi-star" color="amber-darken-2" size="small" />
        </template>
      </v-list-item>

      <v-list-item
        v-if="hasMore"
        class="px-2 clickable-item"
        :class="{ 'non-interactive': isEditing }"
        role="button"
        :tabindex="isEditing ? -1 : 0"
        :aria-label="t('favorites.showAll', { count: store.total })"
        @click="navigateToFavorites"
        @keydown="handleKeydownShowAll($event)"
      >
        <v-list-item-title class="text-body-2 text-primary">
          {{ t('favorites.showAll', { count: store.total }) }}
        </v-list-item-title>
      </v-list-item>
    </v-list>

    <div v-else class="text-center py-6 text-medium-emphasis">
      <v-icon size="32" class="mb-2">mdi-star-outline</v-icon>
      <div>{{ t('favorites.noFavorites') }}</div>
      <div class="text-caption mt-1">{{ t('favorites.noFavoritesHint') }}</div>
    </div>
  </BaseWidget>
</template>

<style scoped>
.favorites-list {
  max-height: 300px;
  overflow-y: auto;
}

.clickable-item {
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.clickable-item:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

.clickable-item:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

.non-interactive {
  cursor: default;
  pointer-events: none;
}
</style>
