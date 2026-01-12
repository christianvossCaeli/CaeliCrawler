/**
 * LLM Provider utilities
 *
 * Shared constants and helper functions for LLM provider display.
 * Uses UPPERCASE to match backend enum values (PostgreSQL enums).
 */

export type LLMProviderType = 'AZURE_OPENAI' | 'OPENAI' | 'ANTHROPIC' | 'SERPAPI' | 'SERPER'

/**
 * Provider icon mapping (Material Design Icons)
 */
export const PROVIDER_ICONS: Record<LLMProviderType, string> = {
  AZURE_OPENAI: 'mdi-microsoft-azure',
  OPENAI: 'mdi-robot',
  ANTHROPIC: 'mdi-brain',
  SERPAPI: 'mdi-google',
  SERPER: 'mdi-magnify',
}

/**
 * Provider color mapping (Vuetify colors)
 */
export const PROVIDER_COLORS: Record<LLMProviderType, string> = {
  AZURE_OPENAI: 'blue',
  OPENAI: 'teal',
  ANTHROPIC: 'orange',
  SERPAPI: 'green',
  SERPER: 'indigo',
}

/**
 * Provider display labels
 */
export const PROVIDER_LABELS: Record<LLMProviderType, string> = {
  AZURE_OPENAI: 'Azure',
  OPENAI: 'OpenAI',
  ANTHROPIC: 'Anthropic',
  SERPAPI: 'SerpAPI',
  SERPER: 'Serper',
}

/**
 * Normalize provider string to uppercase (handles legacy lowercase values)
 */
function normalizeProvider(provider: string): LLMProviderType {
  return provider.toUpperCase() as LLMProviderType
}

/**
 * Get provider icon for a given provider string
 */
export function getProviderIcon(provider: string): string {
  return PROVIDER_ICONS[normalizeProvider(provider)] || 'mdi-chip'
}

/**
 * Get provider color for a given provider string
 */
export function getProviderColor(provider: string): string {
  return PROVIDER_COLORS[normalizeProvider(provider)] || 'grey'
}

/**
 * Get provider label for a given provider string
 */
export function getProviderLabel(provider: string): string {
  return PROVIDER_LABELS[normalizeProvider(provider)] || provider
}

/**
 * Pricing source type (matches backend PricingSource enum)
 */
export type PricingSourceType = 'AZURE_API' | 'OFFICIAL_DOCS' | 'MANUAL'

/**
 * Pricing source colors
 */
export const SOURCE_COLORS: Record<PricingSourceType, string> = {
  AZURE_API: 'blue',
  OFFICIAL_DOCS: 'success',
  MANUAL: 'grey',
}

/**
 * Normalize source string to uppercase
 */
function normalizeSource(source: string): PricingSourceType {
  return source.toUpperCase() as PricingSourceType
}

/**
 * Get source color for a given source string
 */
export function getSourceColor(source: string): string {
  return SOURCE_COLORS[normalizeSource(source)] || 'grey'
}
