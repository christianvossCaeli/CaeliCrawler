/**
 * Dashboard Page Object
 *
 * Encapsulates dashboard page interactions
 */

import { Page, expect } from '@playwright/test'
import { BasePage } from './BasePage'
import { TIMEOUTS } from '../fixtures/test-data'

export class DashboardPage extends BasePage {
  // Selectors
  private readonly navigationDrawer = '.v-navigation-drawer'
  private readonly appBar = '.v-app-bar, .v-toolbar'
  private readonly userAvatar = '.v-avatar'
  private readonly userMenu = '[role="menu"]'
  private readonly logoutButton = 'text=Logout, text=Abmelden'
  private readonly themeToggle = 'button:has(.mdi-weather-sunny), button:has(.mdi-weather-night)'
  private readonly notificationBell = '.mdi-bell-outline, [aria-label*="Notification"]'
  private readonly mainContent = 'main, .v-main'

  constructor(page: Page) {
    super(page)
  }

  /**
   * Navigate to dashboard
   */
  async navigate(): Promise<void> {
    await this.goto('/')
    await this.waitForPageLoad()
  }

  /**
   * Wait for dashboard to load
   */
  async waitForPageLoad(): Promise<void> {
    await this.page.waitForSelector(this.mainContent, { state: 'visible', timeout: TIMEOUTS.medium })
    await this.waitForLoadingComplete()
  }

  /**
   * Verify dashboard is loaded
   */
  async verifyDashboardLoaded(): Promise<void> {
    await expect(this.page.locator(this.mainContent)).toBeVisible({ timeout: TIMEOUTS.medium })
    await expect(this.page.locator(this.appBar)).toBeVisible()
  }

  /**
   * Open user menu
   */
  async openUserMenu(): Promise<void> {
    await this.page.locator(this.userAvatar).first().click()
    await this.page.waitForSelector(this.userMenu, { state: 'visible', timeout: TIMEOUTS.short })
  }

  /**
   * Click logout
   */
  async clickLogout(): Promise<void> {
    await this.openUserMenu()
    await this.page.locator(this.logoutButton).click()
  }

  /**
   * Perform logout
   */
  async logout(): Promise<void> {
    await this.clickLogout()
    // Wait for redirect to login page
    await this.waitForURL(/.*login/, TIMEOUTS.medium)
  }

  /**
   * Toggle theme
   */
  async toggleTheme(): Promise<void> {
    const toggle = this.page.locator(this.themeToggle).first()
    if (await toggle.isVisible({ timeout: TIMEOUTS.short })) {
      await toggle.click()
      await this.page.waitForTimeout(500) // Wait for theme transition
    }
  }

  /**
   * Check if navigation drawer is visible
   */
  async isNavigationDrawerVisible(): Promise<boolean> {
    return await this.isVisible(this.navigationDrawer, TIMEOUTS.short)
  }

  /**
   * Navigate to section via drawer
   */
  async navigateToSection(sectionName: string): Promise<void> {
    await this.page.click(`text=${sectionName}`)
    await this.waitForLoadingComplete()
  }

  /**
   * Verify navigation drawer is present
   */
  async verifyNavigationDrawer(): Promise<void> {
    await expect(this.page.locator(this.navigationDrawer)).toBeVisible()
  }

  /**
   * Verify app bar is present
   */
  async verifyAppBar(): Promise<void> {
    await expect(this.page.locator(this.appBar)).toBeVisible()
  }

  /**
   * Verify user avatar is present
   */
  async verifyUserAvatar(): Promise<void> {
    await expect(this.page.locator(this.userAvatar).first()).toBeVisible()
  }

  /**
   * Check if notification bell is visible
   */
  async hasNotificationBell(): Promise<boolean> {
    return await this.isVisible(this.notificationBell, TIMEOUTS.short)
  }

  /**
   * Click notification bell
   */
  async clickNotificationBell(): Promise<void> {
    if (await this.hasNotificationBell()) {
      await this.page.locator(this.notificationBell).first().click()
    }
  }

  /**
   * Get page heading
   */
  async getPageHeading(): Promise<string> {
    const heading = this.page.locator('h1, h2').first()
    return await heading.textContent() || ''
  }

  /**
   * Wait for specific heading
   */
  async waitForHeading(expectedHeading: string | RegExp): Promise<void> {
    const heading = this.page.locator('h1, h2').first()
    await expect(heading).toContainText(expectedHeading, { timeout: TIMEOUTS.medium })
  }
}
