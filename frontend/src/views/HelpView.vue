<template>
  <div>
    <PageHeader
      :title="t('help.title')"
      :subtitle="t('help.subtitle')"
      icon="mdi-help-circle"
    />

    <!-- Quick Navigation by Groups -->
    <v-card class="mb-6">
      <v-card-text>
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="group in sectionGroups"
            :key="group.id"
            :color="isGroupActive(group) ? 'primary' : 'default'"
            variant="outlined"
            @click="scrollTo(group.sections[0].id)"
          >
            <v-icon start size="small">{{ group.icon }}</v-icon>
            {{ t(group.title) }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- Content -->
    <v-row>
      <v-col cols="12" lg="9">
        <!-- Getting Started -->
        <HelpIntroSection />
        <HelpQuickstartSection />
        <HelpDashboardSection />

        <!-- Search & Analysis -->
        <HelpSmartQuerySection />
        <HelpResultsSection />
        <HelpFavoritesSection />

        <!-- Data Sources -->
        <HelpCategoriesSection />
        <HelpSourcesSection />
        <HelpAiSourceDiscoverySection />
        <HelpDataSourceTagsSection />
        <HelpCrawlerSection />

        <!-- Documents -->
        <HelpDocumentsSection />
        <HelpAttachmentsSection />
        <HelpMunicipalitiesSection />

        <!-- Entities & Facets -->
        <HelpEntityFacetSection />
        <HelpEntityMapViewSection />
        <HelpFacetHistorySection />
        <HelpFacetTypeAdminSection />

        <!-- AI & Automation -->
        <HelpAiAssistantSection />
        <HelpExternalApisSection />

        <!-- Export & Notifications -->
        <HelpExportSection />
        <HelpNotificationsSection />

        <!-- Administration -->
        <HelpUserManagementSection />
        <HelpAuditLogSection />
        <HelpSecuritySection />

        <!-- Developer -->
        <HelpApiSection />
        <HelpTipsSection />
        <HelpTroubleshootingSection />
      </v-col>

      <!-- Sidebar TOC (Desktop) -->
      <v-col cols="3" class="d-none d-lg-block">
        <HelpTableOfContents
          :groups="sectionGroups"
          :active-section="activeSection"
          @navigate="scrollTo"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'
import { helpSectionGroups, helpSections, type HelpSectionGroup } from '@/components/help/helpSections'

// Import all help section components
import {
  HelpIntroSection,
  HelpQuickstartSection,
  HelpDashboardSection,
  HelpSmartQuerySection,
  HelpCategoriesSection,
  HelpSourcesSection,
  HelpAiSourceDiscoverySection,
  HelpDataSourceTagsSection,
  HelpCrawlerSection,
  HelpDocumentsSection,
  HelpMunicipalitiesSection,
  HelpEntityFacetSection,
  HelpEntityMapViewSection,
  HelpFacetHistorySection,
  HelpAttachmentsSection,
  HelpFacetTypeAdminSection,
  HelpResultsSection,
  HelpExportSection,
  HelpNotificationsSection,
  HelpFavoritesSection,
  HelpAiAssistantSection,
  HelpUserManagementSection,
  HelpAuditLogSection,
  HelpExternalApisSection,
  HelpApiSection,
  HelpTipsSection,
  HelpSecuritySection,
  HelpTroubleshootingSection,
  HelpTableOfContents,
} from '@/components/help'

const { t } = useI18n()
const activeSection = ref('intro')
const sectionGroups = helpSectionGroups

// Check if any section in a group is active
const isGroupActive = (group: HelpSectionGroup): boolean => {
  return group.sections.some((s) => s.id === activeSection.value)
}

const scrollTo = (id: string) => {
  const element = document.getElementById(id)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeSection.value = id
  }
}

// Track active section on scroll
let observer: IntersectionObserver | null = null

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          activeSection.value = entry.target.id
        }
      })
    },
    { threshold: 0.3, rootMargin: '-100px 0px -50% 0px' }
  )

  helpSections.forEach((section) => {
    const element = document.getElementById(section.id)
    if (element) observer?.observe(element)
  })
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>

<style scoped>
.v-code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  border-radius: 4px;
  font-family: monospace;
}
</style>
