/**
 * Smart Query Page Object
 *
 * Encapsulates Smart Query page interactions
 */

import { Page, expect, Locator } from '@playwright/test'
import { BasePage } from './BasePage'
import { TIMEOUTS } from '../fixtures/test-data'

export class SmartQueryPage extends BasePage {
  // Selectors
  private readonly modeToggle = '.mode-toggle .v-btn'
  private readonly readModeButton = '.mode-toggle .v-btn[value="read"]'
  private readonly writeModeButton = '.mode-toggle .v-btn[value="write"]'
  private readonly planModeButton = '.mode-toggle .v-btn[value="plan"]'
  private readonly queryInput = 'textarea, [contenteditable="true"], input[type="text"]'
  private readonly submitButton = 'button[type="submit"], button:has(.mdi-send)'
  private readonly historyButton = 'button:has(.mdi-history)'
  private readonly resultContainer = '.smart-query-result, .result-container'
  private readonly visualizationContainer = '.visualization-container'
  private readonly tableVisualization = '.table-visualization'
  private readonly chartVisualization = '.chart-visualization, canvas'
  private readonly mapVisualization = '.map-visualization, .maplibregl-map'
  private readonly textVisualization = '.text-visualization'
  private readonly loadingIndicator = '.v-progress-circular, [role="progressbar"]'
  private readonly errorMessage = '.error-message, .v-alert--error'
  private readonly exampleQueries = '.example-query, [data-example-query]'
  private readonly visualizationTypeSelector = '.visualization-type-selector'
  private readonly exportButton = 'button:has-text("Export"), button:has(.mdi-download)'
  private readonly clearButton = 'button:has-text("Clear"), button:has(.mdi-close)'
  private readonly attachmentButton = 'button:has(.mdi-paperclip)'
  private readonly voiceButton = 'button:has(.mdi-microphone)'

  constructor(page: Page) {
    super(page)
  }

  /**
   * Navigate to smart query page
   */
  async navigate(): Promise<void> {
    await this.goto('/smart-query')
    await this.waitForPageLoad()
  }

  /**
   * Wait for smart query page to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('domcontentloaded')
    await this.waitForLoadingComplete()
  }

  /**
   * Verify smart query page is loaded
   */
  async verifyPageLoaded(): Promise<void> {
    await this.verifyURL(/.*smart-query/)
    await this.page.waitForSelector('main, .v-main', { state: 'visible', timeout: TIMEOUTS.medium })
  }

  /**
   * Get mode buttons
   */
  getModeButtons(): Locator {
    return this.page.locator(this.modeToggle)
  }

  /**
   * Switch to read mode
   */
  async switchToReadMode(): Promise<void> {
    await this.page.locator(this.readModeButton).click()
    await this.page.waitForTimeout(300)
  }

  /**
   * Switch to write mode
   */
  async switchToWriteMode(): Promise<void> {
    await this.page.locator(this.writeModeButton).click()
    await this.page.waitForTimeout(300)
  }

  /**
   * Switch to plan mode
   */
  async switchToPlanMode(): Promise<void> {
    await this.page.locator(this.planModeButton).click()
    await this.page.waitForTimeout(300)
  }

  /**
   * Get active mode
   */
  async getActiveMode(): Promise<string> {
    const activeButton = this.page.locator(`${this.modeToggle}.v-btn--active`).first()
    return await activeButton.getAttribute('value') || ''
  }

  /**
   * Enter query
   */
  async enterQuery(query: string): Promise<void> {
    const input = this.page.locator(this.queryInput).first()
    await input.waitFor({ state: 'visible', timeout: TIMEOUTS.medium })
    await input.fill(query)
  }

  /**
   * Clear query
   */
  async clearQuery(): Promise<void> {
    const input = this.page.locator(this.queryInput).first()
    await input.clear()
  }

  /**
   * Submit query
   */
  async submitQuery(): Promise<void> {
    await this.page.locator(this.submitButton).first().click()
    await this.waitForResults()
  }

  /**
   * Execute query (enter and submit)
   */
  async executeQuery(query: string): Promise<void> {
    await this.enterQuery(query)
    await this.submitQuery()
  }

  /**
   * Wait for results to load
   */
  async waitForResults(timeout = TIMEOUTS.long): Promise<void> {
    // Wait for loading indicator to appear
    try {
      await this.page.waitForSelector(this.loadingIndicator, { state: 'visible', timeout: 3000 })
    } catch {
      // Loading might be very fast
    }

    // Wait for loading to complete
    try {
      await this.page.waitForSelector(this.loadingIndicator, { state: 'hidden', timeout })
    } catch {
      // Already hidden
    }

    // Wait for results or error
    await Promise.race([
      this.page.waitForSelector(this.resultContainer, { state: 'visible', timeout }),
      this.page.waitForSelector(this.errorMessage, { state: 'visible', timeout })
    ])

    await this.page.waitForTimeout(500)
  }

  /**
   * Check if results are displayed
   */
  async hasResults(): Promise<boolean> {
    return await this.isVisible(this.resultContainer, TIMEOUTS.short)
  }

  /**
   * Get result container
   */
  getResultContainer(): Locator {
    return this.page.locator(this.resultContainer).first()
  }

  /**
   * Verify results displayed
   */
  async verifyResultsDisplayed(): Promise<void> {
    await expect(this.page.locator(this.resultContainer)).toBeVisible({ timeout: TIMEOUTS.long })
  }

  /**
   * Check visualization type
   */
  async hasVisualizationType(type: 'table' | 'chart' | 'map' | 'text'): Promise<boolean> {
    const selector = {
      table: this.tableVisualization,
      chart: this.chartVisualization,
      map: this.mapVisualization,
      text: this.textVisualization
    }[type]

    return await this.isVisible(selector, TIMEOUTS.medium)
  }

  /**
   * Verify table visualization
   */
  async verifyTableVisualization(): Promise<void> {
    await expect(this.page.locator(this.tableVisualization)).toBeVisible({ timeout: TIMEOUTS.medium })
  }

  /**
   * Verify chart visualization
   */
  async verifyChartVisualization(): Promise<void> {
    await expect(this.page.locator(this.chartVisualization)).toBeVisible({ timeout: TIMEOUTS.medium })
  }

  /**
   * Verify map visualization
   */
  async verifyMapVisualization(): Promise<void> {
    await expect(this.page.locator(this.mapVisualization)).toBeVisible({ timeout: TIMEOUTS.medium })
  }

  /**
   * Verify text visualization
   */
  async verifyTextVisualization(): Promise<void> {
    await expect(this.page.locator(this.textVisualization)).toBeVisible({ timeout: TIMEOUTS.medium })
  }

  /**
   * Switch visualization type
   */
  async switchVisualization(type: string): Promise<void> {
    const selector = this.page.locator(this.visualizationTypeSelector).first()
    if (await selector.isVisible({ timeout: TIMEOUTS.short })) {
      await selector.click()
      await this.page.click(`text=${type}`)
      await this.page.waitForTimeout(500)
    }
  }

  /**
   * Check if error is displayed
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
   * Verify error displayed
   */
  async verifyErrorDisplayed(): Promise<void> {
    await expect(this.page.locator(this.errorMessage)).toBeVisible({ timeout: TIMEOUTS.short })
  }

  /**
   * Click example query
   */
  async clickExampleQuery(index: number): Promise<void> {
    const examples = this.page.locator(this.exampleQueries)
    const count = await examples.count()
    if (index < count) {
      await examples.nth(index).click()
      await this.page.waitForTimeout(300)
    }
  }

  /**
   * Click first example query
   */
  async clickFirstExampleQuery(): Promise<void> {
    await this.clickExampleQuery(0)
  }

  /**
   * Check if example queries are visible
   */
  async hasExampleQueries(): Promise<boolean> {
    return await this.isVisible(this.exampleQueries, TIMEOUTS.short)
  }

  /**
   * Open history
   */
  async openHistory(): Promise<void> {
    const historyBtn = this.page.locator(this.historyButton).first()
    if (await historyBtn.isVisible({ timeout: TIMEOUTS.short })) {
      await historyBtn.click()
      await this.page.waitForTimeout(300)
    }
  }

  /**
   * Export results
   */
  async exportResults(): Promise<void> {
    const exportBtn = this.page.locator(this.exportButton).first()
    if (await exportBtn.isVisible({ timeout: TIMEOUTS.short })) {
      await exportBtn.click()
      await this.page.waitForTimeout(500)
    }
  }

  /**
   * Check if loading
   */
  async isLoading(): Promise<boolean> {
    return await this.isVisible(this.loadingIndicator, TIMEOUTS.short)
  }

  /**
   * Verify mode toggle visible
   */
  async verifyModeToggleVisible(): Promise<void> {
    await expect(this.getModeButtons().first()).toBeVisible()
  }

  /**
   * Verify query input visible
   */
  async verifyQueryInputVisible(): Promise<void> {
    const input = this.page.locator(this.queryInput).first()
    await expect(input).toBeVisible({ timeout: TIMEOUTS.medium })
  }

  /**
   * Verify submit button visible
   */
  async verifySubmitButtonVisible(): Promise<void> {
    const button = this.page.locator(this.submitButton).first()
    await expect(button).toBeVisible()
  }

  /**
   * Check if attachment button is visible
   */
  async hasAttachmentButton(): Promise<boolean> {
    return await this.isVisible(this.attachmentButton, TIMEOUTS.short)
  }

  /**
   * Check if voice button is visible
   */
  async hasVoiceButton(): Promise<boolean> {
    return await this.isVisible(this.voiceButton, TIMEOUTS.short)
  }

  /**
   * Get result text content
   */
  async getResultText(): Promise<string> {
    const result = await this.getResultContainer()
    return await result.textContent() || ''
  }

  /**
   * Verify result contains text
   */
  async verifyResultContains(text: string | RegExp): Promise<void> {
    const result = this.page.locator(this.resultContainer)
    await expect(result).toContainText(text, { timeout: TIMEOUTS.long })
  }

  /**
   * Count table rows
   */
  async getTableRowCount(): Promise<number> {
    if (await this.hasVisualizationType('table')) {
      const rows = this.page.locator(`${this.tableVisualization} tr, ${this.tableVisualization} .v-data-table__tr`)
      return await rows.count()
    }
    return 0
  }

  /**
   * Verify visualization container
   */
  async verifyVisualizationContainer(): Promise<void> {
    await expect(this.page.locator(this.visualizationContainer)).toBeVisible({ timeout: TIMEOUTS.medium })
  }
}
