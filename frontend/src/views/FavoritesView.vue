<template>
  <div>
    <!-- Header -->
    <PageHeader
      :title="t('favorites.title')"
      :subtitle="t('favorites.subtitle', { count: total })"
      icon="mdi-star"
      avatar-color="amber-darken-2"
    />

    <!-- Info Box -->
    <PageInfoBox :storage-key="INFO_BOX_STORAGE_KEYS.FAVORITES" :title="t('favorites.info.title')">
      {{ t('favorites.info.description') }}
    </PageInfoBox>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="4">
            <v-text-field
              v-model="searchQuery"
              :label="t('common.search')"
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
              @update:model-value="debouncedSearch"
              @keyup.enter="loadFavorites(1)"
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="entityTypeFilter"
              :items="entityTypeOptions"
              item-title="name"
              item-value="slug"
              :label="t('favorites.filterByType')"
              clearable
              hide-details
              @update:model-value="loadFavorites(1)"
            >
              <template #item="{ item, props }">
                <v-list-item v-bind="props">
                  <template #prepend>
                    <v-icon :icon="item.raw.icon" :color="item.raw.color" size="small"></v-icon>
                  </template>
                </v-list-item>
              </template>
              <template #selection="{ item }">
                <v-icon :icon="item.raw.icon" :color="item.raw.color" size="small" class="mr-2"></v-icon>
                {{ item.raw.name }}
              </template>
            </v-select>
          </v-col>
          <v-col cols="auto">
            <v-btn
              variant="tonal"
              color="primary"
              @click="loadFavorites()"
            >
              <v-icon start>mdi-refresh</v-icon>
              {{ t('common.refresh') }}
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Favorites List -->
    <transition name="fade" mode="out-in">
      <!-- Loading Skeleton -->
      <FavoritesSkeleton
        v-if="loading && !favorites.length"
        key="skeleton"
        :row-count="5"
      />

      <!-- Content Card -->
      <v-card v-else key="content">
        <v-card-title class="d-flex align-center">
          <span>{{ t('favorites.myFavorites') }}</span>
          <v-spacer></v-spacer>
          <v-chip size="small" color="amber-darken-2" variant="tonal">
            {{ total }} {{ t('favorites.entries') }}
          </v-chip>
        </v-card-title>

        <!-- Loading Overlay for subsequent loads -->
        <div v-if="loading && favorites.length > 0" class="d-flex justify-center py-4" role="status">
          <v-progress-circular
            indeterminate
            size="32"
            color="primary"
            :aria-label="t('common.loading')"
          />
        </div>

        <!-- Empty State -->
        <v-card-text v-else-if="favorites.length === 0" class="text-center py-12">
        <v-icon size="64" color="grey-lighten-1" class="mb-4">mdi-star-outline</v-icon>
        <div class="text-h6 text-medium-emphasis mb-2">{{ t('favorites.noFavorites') }}</div>
        <div class="text-body-2 text-medium-emphasis mb-4">{{ t('favorites.noFavoritesHint') }}</div>
        <v-btn color="primary" variant="tonal" @click="router.push({ name: 'entities' })">
          <v-icon start>mdi-database</v-icon>
          {{ t('favorites.browseEntities') }}
        </v-btn>
      </v-card-text>

      <!-- Favorites Table -->
      <v-data-table-server
        v-else
        :headers="headers"
        :items="favorites"
        :items-length="total"
        :loading="loading"
        :items-per-page="itemsPerPage"
        :page="currentPage"
        :sort-by="sortBy"
        class="cursor-pointer"
        @update:options="onTableOptionsUpdate"
        @click:row="(_event: Event, { item }: { item: any }) => navigateToEntity(item)"
      >
        <template #item.entity="{ item }">
          <div class="d-flex align-center py-2">
            <v-avatar
              :color="item.entity.entity_type_color || 'grey'"
              size="36"
              variant="tonal"
              class="mr-3"
            >
              <v-icon :icon="item.entity.entity_type_icon || 'mdi-folder'" size="small"></v-icon>
            </v-avatar>
            <div>
              <div class="font-weight-medium">{{ item.entity.name }}</div>
              <div class="text-caption text-medium-emphasis">
                {{ item.entity.entity_type_name }}
              </div>
            </div>
          </div>
        </template>

        <template #item.entity_type="{ item }">
          <v-chip
            size="small"
            :color="item.entity.entity_type_color || 'grey'"
            variant="tonal"
          >
            <v-icon start size="x-small" :icon="item.entity.entity_type_icon || 'mdi-folder'"></v-icon>
            {{ item.entity.entity_type_name }}
          </v-chip>
        </template>

        <template #item.created_at="{ item }">
          <span class="text-caption">
            {{ formatDateTime(item.created_at) }}
          </span>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex justify-end ga-1">
            <v-btn
              icon="mdi-eye"
              size="small"
              variant="tonal"
              color="primary"
              :title="t('common.details')"
              :aria-label="t('common.details') + ': ' + item.entity.name"
              @click.stop="navigateToEntity(item)"
            ></v-btn>
            <v-btn
              icon="mdi-star-off"
              size="small"
              variant="tonal"
              color="warning"
              :title="t('favorites.removeFromFavorites')"
              :aria-label="t('favorites.removeFromFavorites') + ': ' + item.entity.name"
              :loading="removingId === item.id"
              @click.stop="removeFavorite(item)"
            ></v-btn>
          </div>
        </template>
      </v-data-table-server>
      </v-card>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useFavoritesStore, type Favorite } from '@/stores/favorites'
import { useEntityStore } from '@/stores/entity'
import { useSnackbar } from '@/composables/useSnackbar'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import { useDateFormatter } from '@/composables'
import PageHeader from '@/components/common/PageHeader.vue'
import PageInfoBox from '@/components/common/PageInfoBox.vue'
import { INFO_BOX_STORAGE_KEYS } from '@/config/infoBox'
import FavoritesSkeleton from '@/components/common/FavoritesSkeleton.vue'
import { useLogger } from '@/composables/useLogger'
import { usePageContextProvider, PAGE_ACTIONS } from '@/composables/usePageContext'
import type { PageContextData } from '@/composables/assistant/types'

const logger = useLogger('FavoritesView')

const { t } = useI18n()
const router = useRouter()
const favoritesStore = useFavoritesStore()
const entityStore = useEntityStore()
const { showSuccess, showError } = useSnackbar()
const { formatDateTime } = useDateFormatter()

// State
const loading = ref(false)
const searchQuery = ref('')
const entityTypeFilter = ref<string | null>(null)
const currentPage = ref(1)
const itemsPerPage = ref(25)
const removingId = ref<string | null>(null)
const sortBy = ref<Array<{ key: string; order: 'asc' | 'desc' }>>([{ key: 'created_at', order: 'desc' }])

// Computed
const favorites = computed(() => favoritesStore.favorites)
const total = computed(() => favoritesStore.total)

const entityTypeOptions = computed(() => {
  return entityStore.entityTypes.map(et => ({
    slug: et.slug,
    name: et.name,
    icon: et.icon,
    color: et.color,
  }))
})

const headers = computed(() => [
  { title: t('favorites.entity'), key: 'entity', sortable: true },
  { title: t('favorites.type'), key: 'entity_type', sortable: false },
  { title: t('favorites.addedAt'), key: 'created_at', sortable: true },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const },
])

// Page Context Provider for KI-Assistant awareness
usePageContextProvider(
  '/favorites',
  (): PageContextData => ({
    current_route: '/favorites',
    view_mode: 'list',
    total_count: total.value,
    filters: {
      search_query: searchQuery.value || undefined,
      entity_type_filter: entityTypeFilter.value || undefined
    },
    available_features: ['filter_by_type', 'search', 'remove_favorite'],
    available_actions: [...PAGE_ACTIONS.base, 'filter', 'search', 'view_entity', 'remove_favorite']
  })
)

// Methods
async function loadFavorites(page = currentPage.value) {
  // Prevent multiple simultaneous loads
  if (loading.value) {
    return
  }

  loading.value = true
  try {
    // Map frontend sort keys to backend keys
    let sortByKey: string | undefined
    let sortOrder: 'asc' | 'desc' | undefined
    if (sortBy.value.length > 0) {
      const sortItem = sortBy.value[0]
      // Map 'entity' column to 'entity_name' for backend
      sortByKey = sortItem.key === 'entity' ? 'entity_name' : sortItem.key
      sortOrder = sortItem.order
    }

    await favoritesStore.loadFavorites({
      page,
      per_page: itemsPerPage.value,
      search: searchQuery.value || undefined,
      entity_type_slug: entityTypeFilter.value || undefined,
      sort_by: sortByKey,
      sort_order: sortOrder,
    })
    currentPage.value = page
  } catch (e) {
    logger.error('Failed to load favorites:', e)
    showError(t('favorites.loadError'))
  } finally {
    loading.value = false
  }
}

function onTableOptionsUpdate(options: { page: number; itemsPerPage: number; sortBy: Array<{ key: string; order: 'asc' | 'desc' }> }) {
  // Prevent unnecessary reloads that cause infinite loops
  const pageChanged = options.page !== currentPage.value
  const perPageChanged = options.itemsPerPage !== itemsPerPage.value
  const sortChanged = JSON.stringify(options.sortBy) !== JSON.stringify(sortBy.value)

  if (!pageChanged && !perPageChanged && !sortChanged) {
    return // No actual change, skip reload
  }

  if (perPageChanged) {
    itemsPerPage.value = options.itemsPerPage
  }

  if (sortChanged) {
    sortBy.value = options.sortBy
  }

  if (pageChanged || perPageChanged || sortChanged) {
    loadFavorites(options.page)
  }
}

function navigateToEntity(favorite: Favorite) {
  if (favorite.entity.entity_type_slug && favorite.entity.slug) {
    router.push({
      name: 'entity-detail',
      params: {
        typeSlug: favorite.entity.entity_type_slug,
        entitySlug: favorite.entity.slug,
      },
    })
  }
}

async function removeFavorite(favorite: Favorite) {
  removingId.value = favorite.id
  try {
    await favoritesStore.removeFavorite(favorite.entity_id)
    showSuccess(t('favorites.removed'))
  } catch (e) {
    logger.error('Failed to remove favorite:', e)
    showError(t('favorites.removeError'))
  } finally {
    removingId.value = null
  }
}

// formatDate now from useDateFormatter composable (using formatDateTime)

// Debounce search - uses composable with automatic cleanup
const { debouncedFn: debouncedSearch } = useDebounce(
  () => loadFavorites(1),
  { delay: DEBOUNCE_DELAYS.SEARCH }
)

// Init
onMounted(async () => {
  // Load entity types for filter
  if (entityStore.entityTypes.length === 0) {
    await entityStore.fetchEntityTypes()
  }
  await loadFavorites()
})
</script>

<style scoped>
.cursor-pointer :deep(tbody tr) {
  cursor: pointer;
}
.cursor-pointer :deep(tbody tr:hover) {
  background-color: rgba(var(--v-theme-primary), 0.1);
}

/* Fade transition for skeleton → content */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
