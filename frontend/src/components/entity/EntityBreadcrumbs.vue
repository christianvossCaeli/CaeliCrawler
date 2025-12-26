<template>
  <v-breadcrumbs :items="breadcrumbs" class="px-0">
    <template #prepend>
      <v-icon icon="mdi-home" size="small"></v-icon>
    </template>
  </v-breadcrumbs>
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
