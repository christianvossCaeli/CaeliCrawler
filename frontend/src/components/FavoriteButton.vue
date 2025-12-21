<script setup lang="ts">
/**
 * FavoriteButton - Toggle favorite status for an entity
 *
 * Displays a star icon that can be clicked to add/remove
 * an entity from the user's favorites.
 */

import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFavoritesStore } from '@/stores/favorites'

const props = withDefaults(
  defineProps<{
    entityId: string
    size?: 'x-small' | 'small' | 'default' | 'large' | 'x-large'
    variant?: 'flat' | 'text' | 'elevated' | 'tonal' | 'outlined' | 'plain'
    showTooltip?: boolean
  }>(),
  {
    size: 'default',
    variant: 'text',
    showTooltip: true,
  }
)

const { t } = useI18n()
const store = useFavoritesStore()
const isLoading = ref(false)
const isChecked = ref(false)

const isFavorited = computed(() => store.isFavorited(props.entityId))

const icon = computed(() =>
  isFavorited.value ? 'mdi-star' : 'mdi-star-outline'
)

const color = computed(() =>
  isFavorited.value ? 'amber-darken-2' : undefined
)

const tooltipText = computed(() =>
  isFavorited.value
    ? t('favorites.removeFromFavorites')
    : t('favorites.addToFavorites')
)

async function toggle() {
  isLoading.value = true
  try {
    await store.toggleFavorite(props.entityId)
  } catch (e) {
    console.error('Failed to toggle favorite:', e)
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  // Check if favorited on mount if not already known
  if (!isChecked.value && !store.favoriteIds.has(props.entityId)) {
    await store.checkFavorite(props.entityId)
    isChecked.value = true
  }
})
</script>

<template>
  <v-tooltip v-if="showTooltip" location="bottom">
    <template #activator="{ props: tooltipProps }">
      <v-btn
        v-bind="tooltipProps"
        :color="color"
        :size="size"
        :variant="variant"
        :loading="isLoading"
        @click.stop="toggle"
      >
        <v-icon :icon="icon" />
      </v-btn>
    </template>
    {{ tooltipText }}
  </v-tooltip>

  <v-btn
    v-else
    :color="color"
    :size="size"
    :variant="variant"
    :loading="isLoading"
    @click.stop="toggle"
  >
    <v-icon :icon="icon" />
  </v-btn>
</template>
