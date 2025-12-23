<template>
  <div>
    <PageHeader
      :title="t('help.title')"
      :subtitle="t('help.subtitle')"
      icon="mdi-help-circle"
    />

    <!-- Quick Navigation -->
    <v-card class="mb-6">
      <v-card-text>
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="section in sections"
            :key="section.id"
            :color="activeSection === section.id ? 'primary' : 'default'"
            variant="outlined"
            @click="scrollTo(section.id)"
          >
            <v-icon start size="small">{{ section.icon }}</v-icon>
            {{ section.title }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- Content -->
    <v-row>
      <v-col cols="12" lg="9">
        <!-- Section Components -->
        <HelpIntroSection />
        <HelpQuickstartSection />
        <HelpDashboardSection />
        <HelpSmartQuerySection />
        <HelpCategoriesSection />
        <HelpSourcesSection />
        <HelpAiSourceDiscoverySection />
        <HelpDataSourceTagsSection />
        <HelpCrawlerSection />
        <HelpDocumentsSection />
        <HelpMunicipalitiesSection />
        <HelpEntityFacetSection />
        <HelpAttachmentsSection />
        <HelpFacetTypeAdminSection />
        <HelpResultsSection />
        <HelpExportSection />
        <HelpNotificationsSection />
        <HelpFavoritesSection />
        <HelpAiAssistantSection />
        <HelpUserManagementSection />
        <HelpAuditLogSection />
        <HelpApiSection />
        <HelpTipsSection />
        <HelpSecuritySection />
        <HelpTroubleshootingSection />
      </v-col>

      <!-- Sidebar TOC (Desktop) -->
      <v-col cols="3" class="d-none d-lg-block">
        <v-card class="position-sticky" style="top: 80px;">
          <v-card-title class="text-subtitle-1">{{ t('help.sidebar.title') }}</v-card-title>
          <v-list density="compact" nav>
            <v-list-item
              v-for="section in sections"
              :key="section.id"
              :class="{ 'v-list-item--active': activeSection === section.id }"
              @click="scrollTo(section.id)"
            >
              <template v-slot:prepend>
                <v-icon size="small">{{ section.icon }}</v-icon>
              </template>
              <v-list-item-title class="text-body-2">{{ section.title }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import PageHeader from '@/components/common/PageHeader.vue'

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
  HelpAttachmentsSection,
  HelpFacetTypeAdminSection,
  HelpResultsSection,
  HelpExportSection,
  HelpNotificationsSection,
  HelpFavoritesSection,
  HelpAiAssistantSection,
  HelpUserManagementSection,
  HelpAuditLogSection,
  HelpApiSection,
  HelpTipsSection,
  HelpSecuritySection,
  HelpTroubleshootingSection,
} from '@/components/help'

const { t } = useI18n()
const activeSection = ref('intro')

const sections = computed(() => [
  { id: 'intro', title: t('help.sections.intro'), icon: 'mdi-information' },
  { id: 'quickstart', title: t('help.sections.quickstart'), icon: 'mdi-rocket-launch' },
  { id: 'dashboard', title: t('help.sections.dashboard'), icon: 'mdi-view-dashboard' },
  { id: 'smart-query', title: t('help.sections.smartQuery'), icon: 'mdi-brain' },
  { id: 'categories', title: t('help.sections.categories'), icon: 'mdi-folder-multiple' },
  { id: 'sources', title: t('help.sections.sources'), icon: 'mdi-web' },
  { id: 'ai-source-discovery', title: t('help.sections.aiSourceDiscovery'), icon: 'mdi-robot-outline' },
  { id: 'data-source-tags', title: t('help.sections.dataSourceTags'), icon: 'mdi-tag-multiple' },
  { id: 'crawler', title: t('help.sections.crawler'), icon: 'mdi-robot' },
  { id: 'documents', title: t('help.sections.documents'), icon: 'mdi-file-document-multiple' },
  { id: 'municipalities', title: t('help.sections.municipalities'), icon: 'mdi-city' },
  { id: 'entity-facet', title: t('help.sections.entityFacet'), icon: 'mdi-database' },
  { id: 'attachments', title: t('help.sections.attachments'), icon: 'mdi-paperclip' },
  { id: 'facet-type-admin', title: t('help.sections.facetTypeAdmin'), icon: 'mdi-tag-multiple' },
  { id: 'results', title: t('help.sections.results'), icon: 'mdi-chart-bar' },
  { id: 'export', title: t('help.sections.export'), icon: 'mdi-export' },
  { id: 'notifications', title: t('help.sections.notifications'), icon: 'mdi-bell' },
  { id: 'favorites', title: t('help.sections.favorites'), icon: 'mdi-star' },
  { id: 'ai-assistant', title: t('help.sections.aiAssistant'), icon: 'mdi-robot-happy' },
  { id: 'user-management', title: t('help.sections.userManagement'), icon: 'mdi-account-group' },
  { id: 'audit-log', title: t('help.sections.auditLog'), icon: 'mdi-history' },
  { id: 'api', title: t('help.sections.api'), icon: 'mdi-api' },
  { id: 'tips', title: t('help.sections.tips'), icon: 'mdi-lightbulb' },
  { id: 'security', title: t('help.sections.security'), icon: 'mdi-shield-lock' },
  { id: 'troubleshooting', title: t('help.sections.troubleshooting'), icon: 'mdi-wrench' },
])

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

  sections.value.forEach((section) => {
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
