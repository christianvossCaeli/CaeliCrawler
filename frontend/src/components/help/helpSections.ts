/**
 * Help sections data - extracted from HelpView.vue for maintainability.
 */

export interface HelpSection {
  id: string
  title: string
  icon: string
  color?: string
}

export interface HelpSectionGroup {
  id: string
  title: string
  icon: string
  color: string
  sections: HelpSection[]
}

/**
 * Grouped help sections for better navigation
 */
export const helpSectionGroups: HelpSectionGroup[] = [
  {
    id: 'getting-started',
    title: 'help.groups.gettingStarted',
    icon: 'mdi-rocket-launch',
    color: 'success',
    sections: [
      { id: 'intro', title: 'help.sections.intro', icon: 'mdi-information', color: 'primary' },
      { id: 'quickstart', title: 'help.sections.quickstart', icon: 'mdi-rocket-launch', color: 'success' },
      { id: 'dashboard', title: 'help.sections.dashboard', icon: 'mdi-view-dashboard', color: 'info' },
    ],
  },
  {
    id: 'search-analysis',
    title: 'help.groups.searchAnalysis',
    icon: 'mdi-brain',
    color: 'purple',
    sections: [
      { id: 'smart-query', title: 'help.sections.smartQuery', icon: 'mdi-brain', color: 'purple' },
      { id: 'results', title: 'help.sections.results', icon: 'mdi-chart-bar', color: 'orange' },
      { id: 'favorites', title: 'help.sections.favorites', icon: 'mdi-star', color: 'amber' },
    ],
  },
  {
    id: 'data-sources',
    title: 'help.groups.dataSources',
    icon: 'mdi-web',
    color: 'teal',
    sections: [
      { id: 'categories', title: 'help.sections.categories', icon: 'mdi-folder-multiple', color: 'purple' },
      { id: 'sources', title: 'help.sections.sources', icon: 'mdi-web', color: 'teal' },
      { id: 'ai-source-discovery', title: 'help.sections.aiSourceDiscovery', icon: 'mdi-magnify-plus', color: 'amber' },
      { id: 'data-source-tags', title: 'help.sections.dataSourceTags', icon: 'mdi-tag-multiple', color: 'cyan' },
      { id: 'crawler', title: 'help.sections.crawler', icon: 'mdi-robot', color: 'cyan' },
    ],
  },
  {
    id: 'documents-data',
    title: 'help.groups.documentsData',
    icon: 'mdi-file-document-multiple',
    color: 'blue-grey',
    sections: [
      { id: 'documents', title: 'help.sections.documents', icon: 'mdi-file-document-multiple', color: 'blue-grey' },
      { id: 'attachments', title: 'help.sections.attachments', icon: 'mdi-paperclip', color: 'info' },
      { id: 'municipalities', title: 'help.sections.municipalities', icon: 'mdi-city', color: 'indigo' },
    ],
  },
  {
    id: 'entities-facets',
    title: 'help.groups.entitiesFacets',
    icon: 'mdi-database',
    color: 'deep-purple',
    sections: [
      { id: 'entity-facet', title: 'help.sections.entityFacet', icon: 'mdi-database', color: 'deep-purple' },
      { id: 'entity-map', title: 'help.sections.entityMap', icon: 'mdi-map', color: 'success' },
      { id: 'facet-history', title: 'help.sections.facetHistory', icon: 'mdi-chart-timeline', color: 'info' },
      { id: 'facet-type-admin', title: 'help.sections.facetTypeAdmin', icon: 'mdi-tag-multiple', color: 'teal' },
    ],
  },
  {
    id: 'ai-automation',
    title: 'help.groups.aiAutomation',
    icon: 'mdi-robot-happy',
    color: 'pink',
    sections: [
      { id: 'ai-assistant', title: 'help.sections.aiAssistant', icon: 'mdi-robot-happy', color: 'pink' },
      { id: 'external-apis', title: 'help.sections.externalApis', icon: 'mdi-cloud-sync', color: 'teal' },
    ],
  },
  {
    id: 'export-notifications',
    title: 'help.groups.exportNotifications',
    icon: 'mdi-export',
    color: 'deep-purple',
    sections: [
      { id: 'export', title: 'help.sections.export', icon: 'mdi-export', color: 'deep-purple' },
      { id: 'notifications', title: 'help.sections.notifications', icon: 'mdi-bell', color: 'orange-darken-2' },
    ],
  },
  {
    id: 'administration',
    title: 'help.groups.administration',
    icon: 'mdi-cog',
    color: 'blue',
    sections: [
      { id: 'user-management', title: 'help.sections.userManagement', icon: 'mdi-account-group', color: 'blue' },
      { id: 'audit-log', title: 'help.sections.auditLog', icon: 'mdi-history', color: 'brown' },
      { id: 'security', title: 'help.sections.security', icon: 'mdi-shield-lock', color: 'purple' },
    ],
  },
  {
    id: 'developer',
    title: 'help.groups.developer',
    icon: 'mdi-code-tags',
    color: 'grey-darken-1',
    sections: [
      { id: 'api', title: 'help.sections.api', icon: 'mdi-api', color: 'grey-darken-3' },
      { id: 'tips', title: 'help.sections.tips', icon: 'mdi-lightbulb', color: 'amber' },
      { id: 'troubleshooting', title: 'help.sections.troubleshooting', icon: 'mdi-wrench', color: 'red' },
    ],
  },
]

/**
 * Flat list of all sections (for backwards compatibility)
 */
export const helpSections: HelpSection[] = helpSectionGroups.flatMap((group) => group.sections)

export interface ApiEndpoint {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  path: string
  description: string
}

export interface ApiGroup {
  title: string
  icon: string
  color: string
  endpoints: ApiEndpoint[]
  note?: string
}

export const apiGroups: ApiGroup[] = [
  {
    title: 'help.apiGroups.categories.title',
    icon: 'mdi-folder-multiple',
    color: 'primary',
    endpoints: [
      { method: 'GET', path: '/api/admin/categories', description: 'help.apiGroups.categories.endpoints.list' },
      { method: 'POST', path: '/api/admin/categories', description: 'help.apiGroups.categories.endpoints.create' },
      { method: 'GET', path: '/api/admin/categories/{id}', description: 'help.apiGroups.categories.endpoints.get' },
      { method: 'PUT', path: '/api/admin/categories/{id}', description: 'help.apiGroups.categories.endpoints.update' },
      { method: 'DELETE', path: '/api/admin/categories/{id}', description: 'help.apiGroups.categories.endpoints.delete' },
      { method: 'GET', path: '/api/admin/categories/{id}/stats', description: 'help.apiGroups.categories.endpoints.stats' },
    ],
  },
  {
    title: 'help.apiGroups.sources.title',
    icon: 'mdi-web',
    color: 'teal',
    endpoints: [
      { method: 'GET', path: '/api/admin/sources', description: 'help.apiGroups.sources.endpoints.list' },
      { method: 'POST', path: '/api/admin/sources', description: 'help.apiGroups.sources.endpoints.create' },
      { method: 'POST', path: '/api/admin/sources/bulk-import', description: 'help.apiGroups.sources.endpoints.bulkImport' },
      { method: 'GET', path: '/api/admin/sources/meta/countries', description: 'help.apiGroups.sources.endpoints.countries' },
      { method: 'GET', path: '/api/admin/sources/meta/locations', description: 'help.apiGroups.sources.endpoints.locations' },
      { method: 'GET', path: '/api/admin/sources/{id}', description: 'help.apiGroups.sources.endpoints.get' },
      { method: 'PUT', path: '/api/admin/sources/{id}', description: 'help.apiGroups.sources.endpoints.update' },
      { method: 'DELETE', path: '/api/admin/sources/{id}', description: 'help.apiGroups.sources.endpoints.delete' },
      { method: 'POST', path: '/api/admin/sources/{id}/reset', description: 'help.apiGroups.sources.endpoints.reset' },
    ],
  },
  {
    title: 'help.apiGroups.crawler.title',
    icon: 'mdi-robot',
    color: 'cyan',
    endpoints: [
      { method: 'POST', path: '/api/admin/crawler/start', description: 'help.apiGroups.crawler.endpoints.start' },
      { method: 'GET', path: '/api/admin/crawler/status', description: 'help.apiGroups.crawler.endpoints.status' },
      { method: 'GET', path: '/api/admin/crawler/stats', description: 'help.apiGroups.crawler.endpoints.stats' },
      { method: 'GET', path: '/api/admin/crawler/running', description: 'help.apiGroups.crawler.endpoints.running' },
      { method: 'GET', path: '/api/admin/crawler/jobs', description: 'help.apiGroups.crawler.endpoints.jobs' },
      { method: 'GET', path: '/api/admin/crawler/jobs/{id}', description: 'help.apiGroups.crawler.endpoints.jobDetails' },
      { method: 'GET', path: '/api/admin/crawler/jobs/{id}/log', description: 'help.apiGroups.crawler.endpoints.jobLog' },
      { method: 'POST', path: '/api/admin/crawler/jobs/{id}/cancel', description: 'help.apiGroups.crawler.endpoints.cancelJob' },
      { method: 'POST', path: '/api/admin/crawler/reanalyze', description: 'help.apiGroups.crawler.endpoints.reanalyze' },
    ],
  },
  {
    title: 'help.apiGroups.aiTasks.title',
    icon: 'mdi-brain',
    color: 'purple',
    endpoints: [
      { method: 'GET', path: '/api/admin/crawler/ai-tasks', description: 'help.apiGroups.aiTasks.endpoints.list' },
      { method: 'GET', path: '/api/admin/crawler/ai-tasks/running', description: 'help.apiGroups.aiTasks.endpoints.running' },
      { method: 'POST', path: '/api/admin/crawler/ai-tasks/{id}/cancel', description: 'help.apiGroups.aiTasks.endpoints.cancel' },
      { method: 'POST', path: '/api/admin/crawler/documents/{id}/process', description: 'help.apiGroups.aiTasks.endpoints.processDocument' },
      { method: 'POST', path: '/api/admin/crawler/documents/{id}/analyze', description: 'help.apiGroups.aiTasks.endpoints.analyzeDocument' },
      { method: 'POST', path: '/api/admin/crawler/documents/process-pending', description: 'help.apiGroups.aiTasks.endpoints.processPending' },
      { method: 'POST', path: '/api/admin/crawler/documents/stop-all', description: 'help.apiGroups.aiTasks.endpoints.stopAll' },
      { method: 'POST', path: '/api/admin/crawler/documents/reanalyze-filtered', description: 'help.apiGroups.aiTasks.endpoints.reanalyzeFiltered' },
    ],
  },
  {
    title: 'help.apiGroups.locations.title',
    icon: 'mdi-map-marker',
    color: 'indigo',
    endpoints: [
      { method: 'GET', path: '/api/admin/locations', description: 'help.apiGroups.locations.endpoints.list' },
      { method: 'GET', path: '/api/admin/locations/{id}', description: 'help.apiGroups.locations.endpoints.get' },
      { method: 'GET', path: '/api/admin/locations/search', description: 'help.apiGroups.locations.endpoints.search' },
      { method: 'GET', path: '/api/admin/locations/with-sources', description: 'help.apiGroups.locations.endpoints.withSources' },
      { method: 'GET', path: '/api/admin/locations/countries', description: 'help.apiGroups.locations.endpoints.countries' },
      { method: 'GET', path: '/api/admin/locations/states', description: 'help.apiGroups.locations.endpoints.states' },
      { method: 'GET', path: '/api/admin/locations/admin-levels', description: 'help.apiGroups.locations.endpoints.adminLevels' },
      { method: 'POST', path: '/api/admin/locations', description: 'help.apiGroups.locations.endpoints.create' },
      { method: 'PUT', path: '/api/admin/locations/{id}', description: 'help.apiGroups.locations.endpoints.update' },
      { method: 'DELETE', path: '/api/admin/locations/{id}', description: 'help.apiGroups.locations.endpoints.delete' },
      { method: 'POST', path: '/api/admin/locations/link-sources', description: 'help.apiGroups.locations.endpoints.linkSources' },
      { method: 'POST', path: '/api/admin/locations/enrich-admin-levels', description: 'help.apiGroups.locations.endpoints.enrichAdminLevels' },
    ],
  },
  {
    title: 'help.apiGroups.publicApi.title',
    icon: 'mdi-database-search',
    color: 'info',
    endpoints: [
      { method: 'GET', path: '/api/v1/data', description: 'help.apiGroups.publicApi.endpoints.data' },
      { method: 'GET', path: '/api/v1/data/stats', description: 'help.apiGroups.publicApi.endpoints.stats' },
      { method: 'GET', path: '/api/v1/data/locations', description: 'help.apiGroups.publicApi.endpoints.locations' },
      { method: 'GET', path: '/api/v1/data/countries', description: 'help.apiGroups.publicApi.endpoints.countries' },
      { method: 'GET', path: '/api/v1/data/documents', description: 'help.apiGroups.publicApi.endpoints.documents' },
      { method: 'GET', path: '/api/v1/data/documents/{id}', description: 'help.apiGroups.publicApi.endpoints.documentDetails' },
      { method: 'GET', path: '/api/v1/data/documents/locations', description: 'help.apiGroups.publicApi.endpoints.documentLocations' },
      { method: 'GET', path: '/api/v1/data/search', description: 'help.apiGroups.publicApi.endpoints.search' },
      { method: 'PUT', path: '/api/v1/data/extracted/{id}/verify', description: 'help.apiGroups.publicApi.endpoints.verify' },
    ],
  },
  {
    title: 'help.apiGroups.entities.title',
    icon: 'mdi-cube-outline',
    color: 'deep-purple',
    note: 'help.apiGroups.entities.note',
    endpoints: [
      { method: 'GET', path: '/api/v1/entities', description: 'help.apiGroups.entities.endpoints.list' },
      { method: 'POST', path: '/api/v1/entities', description: 'help.apiGroups.entities.endpoints.create' },
      { method: 'GET', path: '/api/v1/entities/{id}', description: 'help.apiGroups.entities.endpoints.get' },
      { method: 'PUT', path: '/api/v1/entities/{id}', description: 'help.apiGroups.entities.endpoints.update' },
      { method: 'DELETE', path: '/api/v1/entities/{id}', description: 'help.apiGroups.entities.endpoints.delete' },
      { method: 'GET', path: '/api/v1/entities/{id}/brief', description: 'help.apiGroups.entities.endpoints.brief' },
      { method: 'GET', path: '/api/v1/entities/{id}/children', description: 'help.apiGroups.entities.endpoints.children' },
      { method: 'GET', path: '/api/v1/entities/{id}/documents', description: 'help.apiGroups.entities.endpoints.documents' },
      { method: 'GET', path: '/api/v1/entities/{id}/sources', description: 'help.apiGroups.entities.endpoints.sources' },
      { method: 'GET', path: '/api/v1/entities/{id}/external-data', description: 'help.apiGroups.entities.endpoints.externalData' },
      { method: 'GET', path: '/api/v1/entities/hierarchy/{type}', description: 'help.apiGroups.entities.endpoints.hierarchy' },
      { method: 'GET', path: '/api/v1/entities/filter-options/location', description: 'help.apiGroups.entities.endpoints.filterLocation' },
      { method: 'GET', path: '/api/v1/entities/filter-options/attributes', description: 'help.apiGroups.entities.endpoints.filterAttributes' },
    ],
  },
  {
    title: 'help.apiGroups.smartQuery.title',
    icon: 'mdi-brain',
    color: 'pink',
    note: 'help.apiGroups.smartQuery.note',
    endpoints: [
      { method: 'POST', path: '/api/v1/analysis/smart-query', description: 'help.apiGroups.smartQuery.endpoints.query' },
      { method: 'POST', path: '/api/v1/analysis/smart-write', description: 'help.apiGroups.smartQuery.endpoints.write' },
      { method: 'GET', path: '/api/v1/analysis/smart-query/examples', description: 'help.apiGroups.smartQuery.endpoints.examples' },
      { method: 'GET', path: '/api/v1/analysis/templates', description: 'help.apiGroups.smartQuery.endpoints.templates' },
      { method: 'POST', path: '/api/v1/analysis/templates', description: 'help.apiGroups.smartQuery.endpoints.createTemplate' },
      { method: 'GET', path: '/api/v1/analysis/templates/{id}', description: 'help.apiGroups.smartQuery.endpoints.getTemplate' },
      { method: 'PUT', path: '/api/v1/analysis/templates/{id}', description: 'help.apiGroups.smartQuery.endpoints.updateTemplate' },
      { method: 'DELETE', path: '/api/v1/analysis/templates/{id}', description: 'help.apiGroups.smartQuery.endpoints.deleteTemplate' },
      { method: 'GET', path: '/api/v1/analysis/overview', description: 'help.apiGroups.smartQuery.endpoints.overview' },
      { method: 'GET', path: '/api/v1/analysis/report/{entity_id}', description: 'help.apiGroups.smartQuery.endpoints.report' },
      { method: 'GET', path: '/api/v1/analysis/stats', description: 'help.apiGroups.smartQuery.endpoints.stats' },
    ],
  },
  {
    title: 'help.apiGroups.municipalities.title',
    icon: 'mdi-city',
    color: 'orange',
    endpoints: [
      { method: 'GET', path: '/api/v1/data/municipalities', description: 'help.apiGroups.municipalities.endpoints.list' },
      { method: 'GET', path: '/api/v1/data/municipalities/{name}/report', description: 'help.apiGroups.municipalities.endpoints.report' },
      { method: 'GET', path: '/api/v1/data/municipalities/{name}/documents', description: 'help.apiGroups.municipalities.endpoints.documents' },
      { method: 'GET', path: '/api/v1/data/report/overview', description: 'help.apiGroups.municipalities.endpoints.overview' },
      { method: 'GET', path: '/api/v1/data/history/municipalities', description: 'help.apiGroups.municipalities.endpoints.history' },
      { method: 'GET', path: '/api/v1/data/history/crawls', description: 'help.apiGroups.municipalities.endpoints.crawlHistory' },
    ],
  },
  {
    title: 'help.apiGroups.export.title',
    icon: 'mdi-export',
    color: 'deep-purple',
    endpoints: [
      { method: 'GET', path: '/api/v1/export/json', description: 'help.apiGroups.export.endpoints.json' },
      { method: 'GET', path: '/api/v1/export/csv', description: 'help.apiGroups.export.endpoints.csv' },
      { method: 'GET', path: '/api/v1/export/changes', description: 'help.apiGroups.export.endpoints.changes' },
      { method: 'POST', path: '/api/v1/export/webhook/test', description: 'help.apiGroups.export.endpoints.webhookTest' },
    ],
  },
  {
    title: 'help.apiGroups.favorites.title',
    icon: 'mdi-star',
    color: 'amber',
    endpoints: [
      { method: 'GET', path: '/api/v1/favorites', description: 'help.apiGroups.favorites.endpoints.list' },
      { method: 'POST', path: '/api/v1/favorites', description: 'help.apiGroups.favorites.endpoints.add' },
      { method: 'GET', path: '/api/v1/favorites/check/{entity_id}', description: 'help.apiGroups.favorites.endpoints.check' },
      { method: 'DELETE', path: '/api/v1/favorites/{favorite_id}', description: 'help.apiGroups.favorites.endpoints.remove' },
      { method: 'DELETE', path: '/api/v1/favorites/entity/{entity_id}', description: 'help.apiGroups.favorites.endpoints.removeByEntity' },
    ],
  },
  {
    title: 'help.apiGroups.system.title',
    icon: 'mdi-heart-pulse',
    color: 'green',
    endpoints: [
      { method: 'GET', path: '/', description: 'help.apiGroups.system.endpoints.root' },
      { method: 'GET', path: '/health', description: 'help.apiGroups.system.endpoints.health' },
      { method: 'GET', path: '/docs', description: 'help.apiGroups.system.endpoints.swagger' },
      { method: 'GET', path: '/redoc', description: 'help.apiGroups.system.endpoints.redoc' },
      { method: 'GET', path: '/openapi.json', description: 'help.apiGroups.system.endpoints.openapi' },
    ],
  },
]

export const methodColors: Record<string, string> = {
  GET: 'success',
  POST: 'primary',
  PUT: 'warning',
  DELETE: 'error',
}
