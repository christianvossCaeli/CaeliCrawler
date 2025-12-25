/**
 * Base Page Object
 *
 * Provides common functionality for all page objects
 */

import { Page, Locator, expect } from '@playwright/test'
import { TIMEOUTS } from '../fixtures/test-data'

export class BasePage {
  protected readonly page: Page
  protected readonly baseURL: string

  constructor(page: Page) {
    this.page = page
    this.baseURL = process.env.TEST_URL || 'http://localhost:5173'
  }

  /**
   * Navigate to a specific path
   */
  async goto(path: string): Promise<void> {
    await this.page.goto(`${this.baseURL}${path}`)
    await this.page.waitForLoadState('domcontentloaded')
  }

  /**
   * Wait for navigation to complete
   */
  async waitForNavigation(timeout = TIMEOUTS.medium): Promise<void> {
    await this.page.waitForLoadState('networkidle', { timeout })
  }

  /**
   * Get element by test ID
   */
  getByTestId(testId: string): Locator {
    return this.page.locator(`[data-testid="${testId}"]`)
  }

  /**
   * Wait for element by test ID
   */
  async waitForTestId(testId: string, timeout = TIMEOUTS.medium): Promise<Locator> {
    const element = this.getByTestId(testId)
    await element.waitFor({ state: 'visible', timeout })
    return element
  }

  /**
   * Click element by test ID
   */
  async clickTestId(testId: string): Promise<void> {
    const element = await this.waitForTestId(testId)
    await element.click()
  }

  /**
   * Fill input by test ID
   */
  async fillTestId(testId: string, value: string): Promise<void> {
    const element = await this.waitForTestId(testId)
    await element.fill(value)
  }

  /**
   * Get element by text
   */
  getByText(text: string | RegExp): Locator {
    return this.page.getByText(text)
  }

  /**
   * Wait for element by text
   */
  async waitForText(text: string | RegExp, timeout = TIMEOUTS.medium): Promise<Locator> {
    const element = this.getByText(text)
    await element.waitFor({ state: 'visible', timeout })
    return element
  }

  /**
   * Get element by role
   */
  getByRole(role: 'button' | 'link' | 'textbox' | 'heading' | 'navigation' | 'main', options?: { name?: string | RegExp }): Locator {
    return this.page.getByRole(role, options)
  }

  /**
   * Wait for URL to match pattern
   */
  async waitForURL(pattern: string | RegExp, timeout = TIMEOUTS.medium): Promise<void> {
    await this.page.waitForURL(pattern, { timeout })
  }

  /**
   * Check if element is visible
   */
  async isVisible(selector: string, timeout = TIMEOUTS.short): Promise<boolean> {
    try {
      await this.page.locator(selector).waitFor({ state: 'visible', timeout })
      return true
    } catch {
      return false
    }
  }

  /**
   * Wait for loading to complete
   */
  async waitForLoadingComplete(timeout = TIMEOUTS.long): Promise<void> {
    // Wait for any loading indicators to disappear
    const loadingSelectors = [
      '.v-progress-circular',
      '.v-overlay--active',
      '[role="progressbar"]',
      '[aria-busy="true"]'
    ]

    for (const selector of loadingSelectors) {
      try {
        await this.page.locator(selector).waitFor({ state: 'hidden', timeout: 5000 })
      } catch {
        // Continue if selector not found
      }
    }

    await this.waitForNavigation()
  }

  /**
   * Take screenshot with name
   */
  async screenshot(name: string): Promise<void> {
    await this.page.screenshot({ path: `test-results/${name}.png`, fullPage: true })
  }

  /**
   * Get current URL
   */
  getCurrentURL(): string {
    return this.page.url()
  }

  /**
   * Verify page title
   */
  async verifyTitle(expectedTitle: string | RegExp): Promise<void> {
    await expect(this.page).toHaveTitle(expectedTitle)
  }

  /**
   * Verify URL pattern
   */
  async verifyURL(pattern: string | RegExp): Promise<void> {
    await expect(this.page).toHaveURL(pattern)
  }

  /**
   * Wait for element and verify visibility
   */
  async verifyElementVisible(selector: string, timeout = TIMEOUTS.medium): Promise<void> {
    const element = this.page.locator(selector)
    await expect(element).toBeVisible({ timeout })
  }

  /**
   * Verify element contains text
   */
  async verifyElementText(selector: string, expectedText: string | RegExp): Promise<void> {
    const element = this.page.locator(selector)
    await expect(element).toContainText(expectedText)
  }

  /**
   * Wait for API response
   */
  async waitForAPIResponse(urlPattern: string | RegExp, timeout = TIMEOUTS.medium): Promise<void> {
    await this.page.waitForResponse((response) => {
      const url = response.url()
      return typeof urlPattern === 'string' ? url.includes(urlPattern) : urlPattern.test(url)
    }, { timeout })
  }

  /**
   * Handle dialog/confirmation
   */
  async handleDialog(accept = true): Promise<void> {
    this.page.once('dialog', async (dialog) => {
      if (accept) {
        await dialog.accept()
      } else {
        await dialog.dismiss()
      }
    })
  }
}
