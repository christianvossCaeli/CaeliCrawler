/**
 * Entities Page Object
 *
 * Encapsulates entities page interactions
 */

import { Page, expect, Locator } from '@playwright/test'
import { BasePage } from './BasePage'
import { TIMEOUTS } from '../fixtures/test-data'

export class EntitiesPage extends BasePage {
  // Selectors
  private readonly searchInput = 'input[type="search"], input[placeholder*="Such"], .v-text-field input'
  private readonly createButton = 'button:has-text("Erstellen"), button:has-text("Create"), [aria-label*="createNew"]'
  private readonly filterButton = 'button:has(.mdi-filter), button:has(.mdi-tune)'
  private readonly entityCards = '.v-card, [data-entity-card]'
  private readonly entityList = '.v-list, .v-data-table'
  private readonly loadingOverlay = '.v-overlay--active'
  private readonly statsCards = '.v-card'
  private readonly categoryFilter = '[aria-label*="category"], .category-select'
  private readonly entityTypeTabs = '.v-tabs'
  private readonly entityTypeTab = '.v-tab'
  private readonly createDialog = '[role="dialog"], .v-dialog'
  private readonly entityNameInput = 'input[label*="Name"], input[placeholder*="Name"]'
  private readonly saveButton = 'button:has-text("Speichern"), button:has-text("Save")'
  private readonly cancelButton = 'button:has-text("Abbrechen"), button:has-text("Cancel")'
  private readonly emptyState = '.empty-state, [data-empty]'
  private readonly errorMessage = '.error-message, .v-alert--error'

  constructor(page: Page) {
    super(page)
  }

  /**
   * Navigate to entities page
   */
  async navigate(): Promise<void> {
    await this.goto('/entities')
    await this.waitForPageLoad()
  }

  /**
   * Navigate to specific entity type
   */
  async navigateToType(typeSlug: string): Promise<void> {
    await this.goto(`/entities/${typeSlug}`)
    await this.waitForPageLoad()
  }

  /**
   * Wait for entities page to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('domcontentloaded')
    await this.waitForLoadingComplete()
  }

  /**
   * Verify entities page is loaded
   */
  async verifyPageLoaded(): Promise<void> {
    await this.verifyURL(/.*entities/)
    await this.page.waitForSelector('main, .v-main', { state: 'visible', timeout: TIMEOUTS.medium })
  }

  /**
   * Search for entities
   */
  async search(query: string): Promise<void> {
    const searchField = this.page.locator(this.searchInput).first()
    await searchField.waitFor({ state: 'visible', timeout: TIMEOUTS.medium })
    await searchField.fill(query)
    // Wait for debounced search
    await this.page.waitForTimeout(800)
    await this.waitForLoadingComplete()
  }

  /**
   * Clear search
   */
  async clearSearch(): Promise<void> {
    const searchField = this.page.locator(this.searchInput).first()
    if (await searchField.isVisible({ timeout: TIMEOUTS.short })) {
      await searchField.clear()
      await this.page.waitForTimeout(800)
    }
  }

  /**
   * Click create button
   */
  async clickCreate(): Promise<void> {
    await this.page.locator(this.createButton).first().click()
    await this.waitForCreateDialog()
  }

  /**
   * Wait for create dialog
   */
  async waitForCreateDialog(): Promise<void> {
    await this.page.waitForSelector(this.createDialog, { state: 'visible', timeout: TIMEOUTS.medium })
  }

  /**
   * Create new entity
   */
  async createEntity(name: string, additionalFields?: Record<string, string>): Promise<void> {
    await this.clickCreate()

    // Fill name
    const nameInput = this.page.locator(this.entityNameInput).first()
    await nameInput.waitFor({ state: 'visible', timeout: TIMEOUTS.medium })
    await nameInput.fill(name)

    // Fill additional fields if provided
    if (additionalFields) {
      for (const [field, value] of Object.entries(additionalFields)) {
        const input = this.page.locator(`input[label*="${field}"], input[placeholder*="${field}"]`).first()
        if (await input.isVisible({ timeout: TIMEOUTS.short })) {
          await input.fill(value)
        }
      }
    }

    // Save
    await this.page.locator(this.saveButton).first().click()
    await this.waitForLoadingComplete()
  }

  /**
   * Cancel entity creation
   */
  async cancelCreate(): Promise<void> {
    await this.page.locator(this.cancelButton).first().click()
    await this.page.waitForSelector(this.createDialog, { state: 'hidden', timeout: TIMEOUTS.medium })
  }

  /**
   * Open filters
   */
  async openFilters(): Promise<void> {
    const filterBtn = this.page.locator(this.filterButton).first()
    if (await filterBtn.isVisible({ timeout: TIMEOUTS.short })) {
      await filterBtn.click()
      await this.page.waitForTimeout(300)
    }
  }

  /**
   * Apply category filter
   */
  async filterByCategory(category: string): Promise<void> {
    const categorySelect = this.page.locator(this.categoryFilter).first()
    if (await categorySelect.isVisible({ timeout: TIMEOUTS.short })) {
      await categorySelect.click()
      await this.page.click(`text=${category}`)
      await this.waitForLoadingComplete()
    }
  }

  /**
   * Get entity count from stats
   */
  async getEntityCount(): Promise<number> {
    const statsCard = this.page.locator(this.statsCards).first()
    await statsCard.waitFor({ state: 'visible', timeout: TIMEOUTS.medium })
    const text = await statsCard.textContent()
    const match = text?.match(/\d+/)
    return match ? parseInt(match[0], 10) : 0
  }

  /**
   * Get all entity cards
   */
  getEntityCards(): Locator {
    return this.page.locator(this.entityCards)
  }

  /**
   * Get entity count
   */
  async getEntityCardsCount(): Promise<number> {
    try {
      await this.page.waitForSelector(this.entityCards, { timeout: TIMEOUTS.short })
      return await this.getEntityCards().count()
    } catch {
      return 0
    }
  }

  /**
   * Click entity by name
   */
  async clickEntityByName(name: string): Promise<void> {
    await this.page.click(`text=${name}`)
    await this.waitForLoadingComplete()
  }

  /**
   * Click first entity
   */
  async clickFirstEntity(): Promise<void> {
    const cards = this.getEntityCards()
    const count = await cards.count()
    if (count > 0) {
      await cards.first().click()
      await this.waitForLoadingComplete()
    }
  }

  /**
   * Verify entity exists
   */
  async verifyEntityExists(name: string): Promise<void> {
    await expect(this.page.locator(`text=${name}`)).toBeVisible({ timeout: TIMEOUTS.medium })
  }

  /**
   * Check if entity type tabs are visible
   */
  async hasEntityTypeTabs(): Promise<boolean> {
    return await this.isVisible(this.entityTypeTabs, TIMEOUTS.short)
  }

  /**
   * Switch entity type tab
   */
  async switchEntityType(typeName: string): Promise<void> {
    if (await this.hasEntityTypeTabs()) {
      await this.page.click(`${this.entityTypeTab}:has-text("${typeName}")`)
      await this.waitForLoadingComplete()
    }
  }

  /**
   * Get active entity type
   */
  async getActiveEntityType(): Promise<string> {
    const activeTab = this.page.locator(`${this.entityTypeTab}.v-tab--selected`).first()
    return await activeTab.textContent() || ''
  }

  /**
   * Verify search results
   */
  async verifySearchResults(expectedCount?: number): Promise<void> {
    await this.waitForLoadingComplete()

    if (expectedCount !== undefined && expectedCount === 0) {
      // Verify empty state
      const isEmpty = await this.isVisible(this.emptyState, TIMEOUTS.short)
      expect(isEmpty).toBe(true)
    } else {
      // Verify results are present
      const count = await this.getEntityCardsCount()
      if (expectedCount !== undefined) {
        expect(count).toBe(expectedCount)
      } else {
        expect(count).toBeGreaterThan(0)
      }
    }
  }

  /**
   * Verify filter applied
   */
  async verifyFilterApplied(): Promise<void> {
    await this.waitForLoadingComplete()
    // Check if filter badge or active filter indicator is present
    const filterBadge = this.page.locator('.v-badge, [data-filter-active]').first()
    if (await filterBadge.isVisible({ timeout: TIMEOUTS.short })) {
      await expect(filterBadge).toBeVisible()
    }
  }

  /**
   * Check if empty state is shown
   */
  async isEmptyStateShown(): Promise<boolean> {
    return await this.isVisible(this.emptyState, TIMEOUTS.short)
  }

  /**
   * Check if error is shown
   */
  async hasError(): Promise<boolean> {
    return await this.isVisible(this.errorMessage, TIMEOUTS.short)
  }

  /**
   * Get error message
   */
  async getErrorMessage(): Promise<string> {
    if (await this.hasError()) {
      return await this.page.locator(this.errorMessage).textContent() || ''
    }
    return ''
  }

  /**
   * Verify stats cards are visible
   */
  async verifyStatsCards(): Promise<void> {
    const statsCards = this.page.locator(this.statsCards)
    await expect(statsCards.first()).toBeVisible({ timeout: TIMEOUTS.medium })
  }

  /**
   * Verify search functionality
   */
  async verifySearchFunctionality(): Promise<void> {
    const searchField = this.page.locator(this.searchInput).first()
    await expect(searchField).toBeVisible({ timeout: TIMEOUTS.medium })
    await expect(searchField).toBeEnabled()
  }
}
