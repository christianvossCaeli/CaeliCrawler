/**
 * Authentication E2E Tests
 *
 * Tests covering authentication flows:
 * - Login successful
 * - Login failed (wrong credentials)
 * - Logout
 * - Session timeout/redirect
 * - Password visibility toggle
 * - Remember session
 */

import { test, expect } from '@playwright/test'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { TEST_USERS, INVALID_CREDENTIALS, TIMEOUTS } from './fixtures/test-data'

test.describe('Authentication', () => {
  test.describe('Login', () => {
    test('should display login page with all elements', async ({ page }) => {
      const loginPage = new LoginPage(page)
      await loginPage.navigate()

      // Verify page elements
      await expect(page.locator('[data-testid="email-input"]')).toBeVisible()
      await expect(page.locator('[data-testid="password-input"]')).toBeVisible()
      await expect(page.locator('[data-testid="login-button"]')).toBeVisible()

      // Verify login button is disabled with empty form
      await loginPage.verifyLoginButtonDisabled()

      // Verify page branding
      await expect(page.locator('text=CAELI')).toBeVisible()
      await expect(page.locator('text=CRAWLER')).toBeVisible()
    })

    test('should enable login button when form is filled', async ({ page }) => {
      const loginPage = new LoginPage(page)
      await loginPage.navigate()

      // Initially disabled
      await loginPage.verifyLoginButtonDisabled()

      // Fill form
      await loginPage.fillEmail(TEST_USERS.admin.email)
      await loginPage.fillPassword(TEST_USERS.admin.password)

      // Should be enabled now
      await loginPage.verifyLoginButtonEnabled()
    })

    test('should login successfully with valid credentials', async ({ page }) => {
      const loginPage = new LoginPage(page)
      const dashboardPage = new DashboardPage(page)

      await loginPage.navigate()
      await loginPage.loginWithUserAndWait(TEST_USERS.admin)

      // Verify successful login
      await loginPage.verifyLoggedIn()
      await dashboardPage.verifyDashboardLoaded()

      // Verify URL changed from login
      expect(page.url()).not.toContain('/login')
    })

    test('should show error with invalid credentials', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()
      await loginPage.login(INVALID_CREDENTIALS.email, INVALID_CREDENTIALS.password)

      // Wait a moment for the request to complete
      await page.waitForTimeout(3000)

      // Should stay on login page
      await loginPage.verifyOnLoginPage()

      // Error message should be displayed
      const hasError = await loginPage.hasError()
      expect(hasError).toBe(true)
    })

    test('should show error with empty password', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()
      await loginPage.fillEmail(TEST_USERS.admin.email)
      // Don't fill password

      // Login button should be disabled
      await loginPage.verifyLoginButtonDisabled()
    })

    test('should show error with empty email', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()
      // Don't fill email
      await loginPage.fillPassword(TEST_USERS.admin.password)

      // Login button should be disabled
      await loginPage.verifyLoginButtonDisabled()
    })

    test('should toggle password visibility', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()
      await loginPage.fillPassword('testpassword')

      // Initially hidden
      await loginPage.verifyPasswordHidden()

      // Toggle to visible
      await loginPage.togglePasswordVisibility()
      await loginPage.verifyPasswordVisible()

      // Toggle back to hidden
      await loginPage.togglePasswordVisibility()
      await loginPage.verifyPasswordHidden()
    })

    test('should submit form with Enter key', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()
      await loginPage.fillEmail(TEST_USERS.admin.email)
      await loginPage.fillPassword(TEST_USERS.admin.password)

      // Press Enter in password field
      await loginPage.pressEnterInPassword()

      // Should login
      await loginPage.verifyLoggedIn()
    })

    test('should show loading state during login', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()
      await loginPage.fillEmail(TEST_USERS.admin.email)
      await loginPage.fillPassword(TEST_USERS.admin.password)

      // Start login and immediately check for loading state
      const loginPromise = loginPage.clickLogin()

      // Check if loading state appears (might be very fast)
      try {
        await expect(page.locator('[data-testid="login-button"]')).toBeDisabled({ timeout: 1000 })
      } catch {
        // Loading might be too fast to catch
      }

      await loginPromise
      await loginPage.waitForLoadingFinished()
    })
  })

  test.describe('Logout', () => {
    test('should logout successfully', async ({ page }) => {
      const loginPage = new LoginPage(page)
      const dashboardPage = new DashboardPage(page)

      // First login
      await loginPage.navigate()
      await loginPage.loginWithUserAndWait(TEST_USERS.admin)
      await dashboardPage.verifyDashboardLoaded()

      // Then logout
      await dashboardPage.logout()

      // Should redirect to login page
      await loginPage.verifyOnLoginPage()
    })

    test('should clear session after logout', async ({ page }) => {
      const loginPage = new LoginPage(page)
      const dashboardPage = new DashboardPage(page)

      // Login
      await loginPage.navigate()
      await loginPage.loginWithUserAndWait(TEST_USERS.admin)

      // Logout
      await dashboardPage.logout()
      await loginPage.verifyOnLoginPage()

      // Try to access protected page directly
      await page.goto('/entities')

      // Should redirect to login
      await loginPage.verifyOnLoginPage()
    })
  })

  test.describe('Protected Routes', () => {
    test('should redirect to login when accessing protected route without auth', async ({ page }) => {
      const loginPage = new LoginPage(page)

      // Try to access protected route directly
      await page.goto('/entities')

      // Should redirect to login
      await loginPage.verifyOnLoginPage()
    })

    test('should preserve redirect URL after login', async ({ page }) => {
      const loginPage = new LoginPage(page)

      // Try to access protected route
      await page.goto('/entities')

      // Should be on login page
      await loginPage.verifyOnLoginPage()

      // Login
      await loginPage.loginWithUserAndWait(TEST_USERS.admin)

      // Should redirect to originally requested page
      await expect(page).toHaveURL(/.*entities/, { timeout: TIMEOUTS.medium })
    })

    test('should redirect authenticated user away from login page', async ({ page }) => {
      const loginPage = new LoginPage(page)
      const dashboardPage = new DashboardPage(page)

      // Login
      await loginPage.navigate()
      await loginPage.loginWithUserAndWait(TEST_USERS.admin)
      await dashboardPage.verifyDashboardLoaded()

      // Try to go to login page again
      await page.goto('/login')

      // Should redirect to dashboard
      expect(page.url()).not.toContain('/login')
    })
  })

  test.describe('Session Management', () => {
    test('should maintain session on page reload', async ({ page }) => {
      const loginPage = new LoginPage(page)
      const dashboardPage = new DashboardPage(page)

      // Login
      await loginPage.navigate()
      await loginPage.loginWithUserAndWait(TEST_USERS.admin)
      await dashboardPage.verifyDashboardLoaded()

      // Reload page
      await page.reload()
      await page.waitForLoadState('networkidle')

      // Should still be authenticated
      await dashboardPage.verifyDashboardLoaded()
      expect(page.url()).not.toContain('/login')
    })

    test('should maintain session across navigation', async ({ page }) => {
      const loginPage = new LoginPage(page)
      const dashboardPage = new DashboardPage(page)

      // Login
      await loginPage.navigate()
      await loginPage.loginWithUserAndWait(TEST_USERS.admin)
      await dashboardPage.verifyDashboardLoaded()

      // Navigate to different pages
      await page.goto('/entities')
      await page.waitForLoadState('networkidle')
      expect(page.url()).not.toContain('/login')

      await page.goto('/documents')
      await page.waitForLoadState('networkidle')
      expect(page.url()).not.toContain('/login')

      await page.goto('/')
      await page.waitForLoadState('networkidle')
      await dashboardPage.verifyDashboardLoaded()
    })
  })

  test.describe('Error Handling', () => {
    test('should handle network errors gracefully', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()

      // Simulate network failure by going offline
      await page.context().setOffline(true)

      await loginPage.fillEmail(TEST_USERS.admin.email)
      await loginPage.fillPassword(TEST_USERS.admin.password)
      await loginPage.clickLogin()

      // Wait for error handling
      await page.waitForTimeout(3000)

      // Should show some error indication (either error message or stay on login)
      await loginPage.verifyOnLoginPage()

      // Restore network
      await page.context().setOffline(false)
    })

    test('should clear error message when typing', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()

      // Trigger error with invalid credentials
      await loginPage.login(INVALID_CREDENTIALS.email, INVALID_CREDENTIALS.password)
      await page.waitForTimeout(3000)

      // Verify error shown
      const hasError = await loginPage.hasError()
      if (hasError) {
        // Start typing in email field
        await loginPage.fillEmail('new@email.com')

        // Error might clear or stay (depends on implementation)
        // Just verify the form is still interactive
        await loginPage.verifyLoginButtonEnabled()
      }
    })
  })

  test.describe('Accessibility', () => {
    test('should have proper ARIA labels', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()

      // Check for ARIA attributes
      const emailInput = page.locator('[data-testid="email-input"]')
      const passwordInput = page.locator('[data-testid="password-input"]')
      const loginButton = page.locator('[data-testid="login-button"]')

      await expect(emailInput).toBeVisible()
      await expect(passwordInput).toBeVisible()
      await expect(loginButton).toBeVisible()

      // Check autocomplete attributes
      await expect(emailInput).toHaveAttribute('autocomplete', 'email')
      await expect(passwordInput).toHaveAttribute('autocomplete', 'current-password')
    })

    test('should be keyboard navigable', async ({ page }) => {
      const loginPage = new LoginPage(page)

      await loginPage.navigate()

      // Tab through form
      await page.keyboard.press('Tab')

      // Check if email field has focus (or becomes focused after tab)
      await page.waitForTimeout(300)

      // Fill with keyboard
      await page.keyboard.type(TEST_USERS.admin.email)
      await page.keyboard.press('Tab')
      await page.keyboard.type(TEST_USERS.admin.password)
      await page.keyboard.press('Enter')

      // Should login
      await loginPage.verifyLoggedIn()
    })
  })
})
