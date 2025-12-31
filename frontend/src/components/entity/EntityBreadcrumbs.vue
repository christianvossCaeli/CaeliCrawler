<template>
  <nav aria-label="Breadcrumb" class="breadcrumb-nav">
    <v-breadcrumbs :items="breadcrumbs" class="px-0">
      <template #prepend>
        <v-icon icon="mdi-home" size="small" aria-hidden="true"></v-icon>
      </template>
      <template #item="{ item, index }">
        <v-breadcrumbs-item
          v-if="item.to && !item.disabled"
          :to="item.to"
          :title="item.title"
        >
          {{ item.title }}
        </v-breadcrumbs-item>
        <span
          v-else
          :aria-current="index === breadcrumbs.length - 1 ? 'page' : undefined"
          class="text-medium-emphasis"
        >
          {{ item.title }}
        </span>
      </template>
    </v-breadcrumbs>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Entity, EntityType } from '@/stores/entity'

const props = defineProps<{
  entity: Entity | null
  entityType: EntityType | null
  typeSlug?: string
}>()

const { t } = useI18n()

const breadcrumbs = computed(() => {
  // Use typeSlug from route or fallback to entityType.slug
  const slug = props.typeSlug || props.entityType?.slug
  return [
    { title: t('nav.dashboard'), to: '/' },
    { title: props.entityType?.name_plural || t('nav.entities'), to: slug ? `/entities/${slug}` : '/entities' },
    { title: props.entity?.name || '...', disabled: true },
  ]
})
</script>

<style scoped>
.breadcrumb-nav {
  display: block;
}
</style>
