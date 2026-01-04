/**
 * Sources Configuration
 *
 * Centralized configuration for sources-related constants.
 * Avoids magic numbers scattered throughout the codebase.
 */

/** Pagination defaults */
export const SOURCES_PAGINATION = {
  /** Default items per page in sources table */
  ITEMS_PER_PAGE: 50,
  /** Maximum items per page */
  MAX_ITEMS_PER_PAGE: 100,
  /** Categories per page for dropdown loading */
  CATEGORIES_PER_PAGE: 100,
} as const

/** Bulk import limits */
export const BULK_IMPORT = {
  /** Maximum CSV file size in bytes (5MB) */
  MAX_FILE_SIZE: 5 * 1024 * 1024,
  /** Maximum number of lines in CSV */
  MAX_LINES: 10_000,
  /** Number of preview items to display */
  PREVIEW_DISPLAY_LIMIT: 50,
} as const

/** Sidebar configuration */
export const SIDEBAR = {
  /** Initial number of categories to show */
  CATEGORY_INITIAL_LIMIT: 8,
  /** Initial number of tags to show */
  TAG_INITIAL_LIMIT: 12,
} as const

/** Entity search configuration */
export const ENTITY_SEARCH = {
  /** Minimum characters to trigger search */
  MIN_QUERY_LENGTH: 2,
  /** Maximum results to return */
  MAX_RESULTS: 10,
  /** Debounce delay in ms */
  DEBOUNCE_MS: 300,
} as const

/** Search debounce configuration */
export const SEARCH = {
  /** Debounce delay for source search in ms */
  DEBOUNCE_MS: 300,
} as const

/** Cache configuration */
export const CACHE = {
  /** Time-to-live for sidebar counts cache in ms (30 seconds) */
  SIDEBAR_COUNTS_TTL: 30_000,
  /** Time-to-live for available tags cache in ms (60 seconds) */
  AVAILABLE_TAGS_TTL: 60_000,
} as const

/** Crawl configuration defaults */
export const CRAWL_DEFAULTS = {
  MAX_DEPTH: 3,
  MAX_PAGES: 100,
  RENDER_JAVASCRIPT: false,
  /** SharePoint defaults */
  SHAREPOINT: {
    FILE_EXTENSIONS: ['.pdf', '.docx', '.doc', '.xlsx', '.pptx'],
    RECURSIVE: true,
    EXCLUDE_PATTERNS: ['~$*', '*.tmp', '.DS_Store'],
    MAX_FILES: 1000,
  },
} as const

/**
 * Source Type Options for Dropdowns
 * Used in preset editor and source filters
 */
export const SOURCE_TYPE_OPTIONS = [
  { value: 'WEBSITE', title: 'Website' },
  { value: 'OPARL_API', title: 'OParl API' },
  { value: 'RSS', title: 'RSS Feed' },
  { value: 'CUSTOM_API', title: 'Custom API' },
  { value: 'REST_API', title: 'REST API' },
  { value: 'SPARQL_API', title: 'SPARQL API' },
] as const

/**
 * Source Type Labels Mapping
 * Maps source type enum values to human-readable labels
 */
export const SOURCE_TYPE_LABELS: Record<string, string> = {
  WEBSITE: 'Website',
  OPARL_API: 'OParl API',
  RSS: 'RSS Feed',
  CUSTOM_API: 'Custom API',
  REST_API: 'REST API',
  SPARQL_API: 'SPARQL API',
}

/** Table header configuration item */
export interface TableHeaderConfig {
  key: string
  i18nKey: string
  sortable?: boolean
  align?: 'start' | 'end' | 'center'
}

/** Table headers configuration (keys for i18n) */
export const TABLE_HEADERS: TableHeaderConfig[] = [
  { key: 'name', i18nKey: 'sources.columns.name', sortable: true },
  { key: 'categories', i18nKey: 'sources.columns.categories', sortable: false },
  { key: 'source_type', i18nKey: 'sources.columns.type', sortable: true },
  { key: 'status', i18nKey: 'sources.columns.status', sortable: true },
  { key: 'last_crawl', i18nKey: 'sources.columns.lastCrawl', sortable: true },
  { key: 'document_count', i18nKey: 'sources.columns.documents', sortable: true },
  { key: 'actions', i18nKey: 'sources.columns.actions', sortable: false, align: 'end' },
]

/** AI Discovery configuration */
export const AI_DISCOVERY = {
  /** Default max results */
  MAX_RESULTS_DEFAULT: 50,
  /** Min max results */
  MAX_RESULTS_MIN: 10,
  /** Max max results */
  MAX_RESULTS_MAX: 200,
} as const

/** Action loading cleanup delay in ms */
export const ACTION_CLEANUP_DELAY = 1000

/**
 * Crawl Presets Configuration
 */
export const CRAWL_PRESETS = {
  /** localStorage keys for persisting UI state */
  STORAGE_KEYS: {
    INFO_HIDDEN: 'crawlPresets.infoHidden',
    EDITOR_INFO_HIDDEN: 'crawlPresets.editorInfoHidden',
  },
  /** Debounce delay for auto-preview in ms */
  AUTO_PREVIEW_DELAY_MS: 500,
  /** Default CRON expression for new scheduled presets */
  DEFAULT_CRON: '0 6 * * *',
} as const

/**
 * UI Layout Constants
 * Consistent sizing for common UI elements across Sources components
 */
export const UI_LAYOUT = {
  /** Sidebar width in pixels */
  SIDEBAR_WIDTH: 280,
  /** Avatar sizes for dialog headers */
  AVATAR: {
    SM: 32,
    MD: 40,
    LG: 48,
  },
  /** Icon sizes */
  ICON: {
    XS: 'x-small',
    SM: 'small',
    MD: 'default',
    LG: 'large',
  },
  /** Card padding variants (Vuetify spacing units) */
  CARD_PADDING: {
    SM: 3,
    MD: 4,
    LG: 6,
  },
  /** Empty state icon size */
  EMPTY_STATE_ICON_SIZE: 64,
  /** Table row height for dense tables */
  TABLE_ROW_HEIGHT_DENSE: 48,
  /** Preview table max displayed rows */
  PREVIEW_TABLE_ROWS: 10,
} as const

/**
 * Timing Constants
 * Animation and delay durations
 */
export const TIMING = {
  /** Snackbar auto-hide duration in ms */
  SNACKBAR_DURATION: 3000,
  /** Tooltip delay in ms */
  TOOLTIP_DELAY: 500,
  /** Loading indicator minimum display time */
  MIN_LOADING_DISPLAY: 300,
} as const
