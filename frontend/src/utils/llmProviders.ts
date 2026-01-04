/**
 * LLM Provider utilities
 *
 * Shared constants and helper functions for LLM provider display.
 */

export type LLMProviderType = 'azure_openai' | 'openai' | 'anthropic' | 'serpapi' | 'serper'

/**
 * Provider icon mapping (Material Design Icons)
 */
export const PROVIDER_ICONS: Record<LLMProviderType, string> = {
  azure_openai: 'mdi-microsoft-azure',
  openai: 'mdi-robot',
  anthropic: 'mdi-brain',
  serpapi: 'mdi-google',
  serper: 'mdi-magnify',
}

/**
 * Provider color mapping (Vuetify colors)
 */
export const PROVIDER_COLORS: Record<LLMProviderType, string> = {
  azure_openai: 'blue',
  openai: 'teal',
  anthropic: 'orange',
  serpapi: 'green',
  serper: 'indigo',
}

/**
 * Provider display labels
 */
export const PROVIDER_LABELS: Record<LLMProviderType, string> = {
  azure_openai: 'Azure OpenAI',
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  serpapi: 'SerpAPI',
  serper: 'Serper',
}

/**
 * Get provider icon for a given provider string
 */
export function getProviderIcon(provider: string): string {
  return PROVIDER_ICONS[provider as LLMProviderType] || 'mdi-chip'
}

/**
 * Get provider color for a given provider string
 */
export function getProviderColor(provider: string): string {
  return PROVIDER_COLORS[provider as LLMProviderType] || 'grey'
}

/**
 * Get provider label for a given provider string
 */
export function getProviderLabel(provider: string): string {
  return PROVIDER_LABELS[provider as LLMProviderType] || provider
}

/**
 * Pricing source colors
 */
export const SOURCE_COLORS: Record<string, string> = {
  azure_api: 'blue',
  official_docs: 'success',
  litellm: 'purple',
  manual: 'grey',
}

/**
 * Get source color for a given source string
 */
export function getSourceColor(source: string): string {
  return SOURCE_COLORS[source] || 'grey'
}
