<template>
  <v-card class="position-sticky help-toc" style="top: 80px;">
    <v-card-title class="text-subtitle-1 d-flex align-center py-2">
      <v-icon size="small" class="mr-2">mdi-table-of-contents</v-icon>
      {{ t('help.toc.title', 'Inhalt') }}
    </v-card-title>
    <v-divider />
    <div class="help-toc-content">
      <v-expansion-panels v-model="expandedGroups" multiple variant="accordion">
        <v-expansion-panel
          v-for="group in groups"
          :key="group.id"
          :value="group.id"
          elevation="0"
        >
          <v-expansion-panel-title class="py-2 px-3">
            <div class="d-flex align-center">
              <v-icon :color="group.color" size="small" class="mr-2">{{ group.icon }}</v-icon>
              <span class="text-body-2 font-weight-medium">{{ t(group.title) }}</span>
              <v-chip
                v-if="getActiveCountInGroup(group)"
                size="x-small"
                color="primary"
                variant="tonal"
                class="ml-2"
              >
                {{ getActiveCountInGroup(group) }}
              </v-chip>
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text class="pa-0">
            <v-list density="compact" nav class="py-0">
              <v-list-item
                v-for="section in group.sections"
                :key="section.id"
                :class="{ 'v-list-item--active': activeSection === section.id }"
                class="py-1 pl-6"
                @click="$emit('navigate', section.id)"
              >
                <template v-slot:prepend>
                  <v-icon :color="section.color" size="x-small">{{ section.icon }}</v-icon>
                </template>
                <v-list-item-title class="text-caption">{{ t(section.title) }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { HelpSectionGroup } from './helpSections'

const { t } = useI18n()

const props = defineProps<{
  groups: HelpSectionGroup[]
  activeSection: string
}>()

defineEmits<{
  (e: 'navigate', sectionId: string): void
}>()

// Initially expand the group containing the active section
const expandedGroups = ref<string[]>([])

// Find which group contains a section
const findGroupForSection = (sectionId: string): string | null => {
  for (const group of props.groups) {
    if (group.sections.some((s) => s.id === sectionId)) {
      return group.id
    }
  }
  return null
}

// Count active sections in a group (for badge)
const getActiveCountInGroup = (group: HelpSectionGroup): number => {
  return group.sections.filter((s) => s.id === props.activeSection).length
}

// Auto-expand group when active section changes
watch(
  () => props.activeSection,
  (newSection) => {
    const groupId = findGroupForSection(newSection)
    if (groupId && !expandedGroups.value.includes(groupId)) {
      expandedGroups.value = [...expandedGroups.value, groupId]
    }
  },
  { immediate: true }
)

// Initialize with first group expanded
if (expandedGroups.value.length === 0 && props.groups.length > 0) {
  expandedGroups.value = [props.groups[0].id]
}
</script>

<style scoped>
.help-toc {
  max-height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
}

.help-toc-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.help-toc-content::-webkit-scrollbar {
  width: 6px;
}

.help-toc-content::-webkit-scrollbar-track {
  background: transparent;
}

.help-toc-content::-webkit-scrollbar-thumb {
  background-color: rgba(128, 128, 128, 0.3);
  border-radius: 3px;
}

.help-toc-content::-webkit-scrollbar-thumb:hover {
  background-color: rgba(128, 128, 128, 0.5);
}

:deep(.v-expansion-panel-title) {
  min-height: 40px !important;
}

:deep(.v-expansion-panel-text__wrapper) {
  padding: 0 !important;
}

:deep(.v-list-item--active) {
  background-color: rgb(var(--v-theme-primary), 0.1);
}
</style>
