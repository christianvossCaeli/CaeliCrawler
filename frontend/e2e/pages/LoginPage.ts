/**
 * Login Page Object
 *
 * Encapsulates login page interactions
 */

import { Page, expect } from '@playwright/test'
import { BasePage } from './BasePage'
import { TestUser, TIMEOUTS } from '../fixtures/test-data'

export class LoginPage extends BasePage {
  // Selectors
  private readonly emailInput = '[data-testid="email-input"]'
  private readonly passwordInput = '[data-testid="password-input"]'
  private readonly loginButton = '[data-testid="login-button"]'
  private readonly passwordToggle = '.password-toggle'
  private readonly errorAlert = '.error-alert, #login-error'
  private readonly loadingSpinner = '.spinner, .v-progress-circular'

  constructor(page: Page) {
    super(page)
  }

  /**
   * Navigate to login page
   */
  async navigate(): Promise<void> {
    await this.goto('/login')
    await this.waitForPageLoad()
  }

  /**
   * Wait for login page to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.page.waitForSelector(this.emailInput, { state: 'visible', timeout: TIMEOUTS.medium })
    await this.page.waitForSelector(this.passwordInput, { state: 'visible', timeout: TIMEOUTS.medium })
    await this.page.waitForSelector(this.loginButton, { state: 'visible', timeout: TIMEOUTS.medium })
  }

  /**
   * Fill email field
   */
  async fillEmail(email: string): Promise<void> {
    await this.page.fill(this.emailInput, email)
  }

  /**
   * Fill password field
   */
  async fillPassword(password: string): Promise<void> {
    await this.page.fill(this.passwordInput, password)
  }

  /**
   * Click login button
   */
  async clickLogin(): Promise<void> {
    await this.page.click(this.loginButton)
  }

  /**
   * Toggle password visibility
   */
  async togglePasswordVisibility(): Promise<void> {
    await this.page.click(this.passwordToggle)
  }

  /**
   * Perform login with credentials
   */
  async login(email: string, password: string): Promise<void> {
    await this.fillEmail(email)
    await this.fillPassword(password)
    await this.clickLogin()
  }

  /**
   * Perform login with test user
   */
  async loginWithUser(user: TestUser): Promise<void> {
    await this.login(user.email, user.password)
  }

  /**
   * Perform login and wait for navigation
   */
  async loginAndWaitForNavigation(email: string, password: string): Promise<void> {
    await this.login(email, password)
    // Wait for navigation away from login page
    await this.page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: TIMEOUTS.long
    })
    await this.waitForLoadingComplete()
  }

  /**
   * Perform login with user and wait for navigation
   */
  async loginWithUserAndWait(user: TestUser): Promise<void> {
    await this.loginAndWaitForNavigation(user.email, user.password)
  }

  /**
   * Check if error message is displayed
   */
  async hasError(): Promise<boolean> {
    return await this.isVisible(this.errorAlert, TIMEOUTS.short)
  }

  /**
   * Get error message text
   */
  async getErrorMessage(): Promise<string> {
    await this.page.waitForSelector(this.errorAlert, { state: 'visible', timeout: TIMEOUTS.short })
    return await this.page.locator(this.errorAlert).textContent() || ''
  }

  /**
   * Verify error message is displayed
   */
  async verifyErrorDisplayed(): Promise<void> {
    await expect(this.page.locator(this.errorAlert)).toBeVisible({ timeout: TIMEOUTS.short })
  }

  /**
   * Verify still on login page
   */
  async verifyOnLoginPage(): Promise<void> {
    await this.verifyURL(/.*login/)
    await expect(this.page.locator(this.loginButton)).toBeVisible()
  }

  /**
   * Verify navigated away from login page
   */
  async verifyLoggedIn(): Promise<void> {
    await this.page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: TIMEOUTS.long
    })
    // Verify we're on a protected page (usually dashboard)
    await this.waitForLoadingComplete()
  }

  /**
   * Verify login button is disabled
   */
  async verifyLoginButtonDisabled(): Promise<void> {
    const button = this.page.locator(this.loginButton)
    await expect(button).toBeDisabled()
  }

  /**
   * Verify login button is enabled
   */
  async verifyLoginButtonEnabled(): Promise<void> {
    const button = this.page.locator(this.loginButton)
    await expect(button).toBeEnabled()
  }

  /**
   * Check if loading spinner is visible
   */
  async isLoading(): Promise<boolean> {
    return await this.isVisible(this.loadingSpinner, TIMEOUTS.short)
  }

  /**
   * Wait for loading to finish
   */
  async waitForLoadingFinished(): Promise<void> {
    try {
      await this.page.locator(this.loadingSpinner).waitFor({ state: 'hidden', timeout: TIMEOUTS.medium })
    } catch {
      // Loading might have already finished
    }
  }

  /**
   * Get password input type
   */
  async getPasswordInputType(): Promise<string | null> {
    return await this.page.locator(this.passwordInput).getAttribute('type')
  }

  /**
   * Verify password is hidden
   */
  async verifyPasswordHidden(): Promise<void> {
    const type = await this.getPasswordInputType()
    expect(type).toBe('password')
  }

  /**
   * Verify password is visible
   */
  async verifyPasswordVisible(): Promise<void> {
    const type = await this.getPasswordInputType()
    expect(type).toBe('text')
  }

  /**
   * Clear login form
   */
  async clearForm(): Promise<void> {
    await this.page.fill(this.emailInput, '')
    await this.page.fill(this.passwordInput, '')
  }

  /**
   * Check if email input has focus
   */
  async isEmailFocused(): Promise<boolean> {
    return await this.page.locator(this.emailInput).evaluate((el) => el === document.activeElement)
  }

  /**
   * Press Enter key in email field
   */
  async pressEnterInEmail(): Promise<void> {
    await this.page.locator(this.emailInput).press('Enter')
  }

  /**
   * Press Enter key in password field
   */
  async pressEnterInPassword(): Promise<void> {
    await this.page.locator(this.passwordInput).press('Enter')
  }
}
