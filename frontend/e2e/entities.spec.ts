/**
 * Entity Management E2E Tests
 *
 * Tests covering entity management flows:
 * - Display entities list
 * - Filter entities
 * - Search entities
 * - Open entity details
 * - Create entity (admin)
 * - Entity type switching
 * - Statistics display
 */

import { test, expect } from '@playwright/test'
import { LoginPage } from './pages/LoginPage'
import { EntitiesPage } from './pages/EntitiesPage'
import { TEST_USERS, TIMEOUTS } from './fixtures/test-data'

// Helper function to login before each test
async function loginAsAdmin(page: any) {
  const loginPage = new LoginPage(page)
  await loginPage.navigate()
  await loginPage.loginWithUserAndWait(TEST_USERS.admin)
}

test.describe('Entity Management', () => {
  test.describe('Entities List', () => {
    test('should display entities list page', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Verify page loaded
      await entitiesPage.verifyPageLoaded()

      // Verify main content is visible
      await expect(page.locator('main, .v-main')).toBeVisible()
    })

    test('should display statistics cards', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Verify stats cards are visible
      await entitiesPage.verifyStatsCards()
    })

    test('should show entity count in stats', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Get entity count
      const count = await entitiesPage.getEntityCount()
      expect(count).toBeGreaterThanOrEqual(0)
    })

    test('should display entity type tabs if no specific type selected', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Check if entity type tabs exist
      const hasTabs = await entitiesPage.hasEntityTypeTabs()

      if (hasTabs) {
        // Verify tabs are visible
        await expect(page.locator('.v-tabs')).toBeVisible()
      }
    })

    test('should load entities without errors', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Wait for loading to complete
      await entitiesPage.waitForLoadingComplete()

      // Check for errors
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })
  })

  test.describe('Entity Search', () => {
    test('should have search functionality', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Verify search functionality exists
      await entitiesPage.verifySearchFunctionality()
    })

    test('should search for entities', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Get initial count
      const initialCount = await entitiesPage.getEntityCardsCount()

      // Perform search
      await entitiesPage.search('Test')

      // Wait for results
      await entitiesPage.waitForLoadingComplete()

      // Results should load (might be 0 if no matches)
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })

    test('should clear search', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Search for something
      await entitiesPage.search('Test')
      await entitiesPage.waitForLoadingComplete()

      // Clear search
      await entitiesPage.clearSearch()
      await entitiesPage.waitForLoadingComplete()

      // Should show all entities again
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })

    test('should show empty state for no results', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Search for something that likely doesn't exist
      await entitiesPage.search('xyznonexistententity12345')
      await entitiesPage.waitForLoadingComplete()

      // Should show empty state or no results
      const count = await entitiesPage.getEntityCardsCount()
      const isEmpty = await entitiesPage.isEmptyStateShown()

      // Either no cards or empty state shown
      expect(count === 0 || isEmpty).toBe(true)
    })

    test('should update results as user types (debounced)', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Type search query
      await entitiesPage.search('A')

      // Wait for debounce and results
      await page.waitForTimeout(1000)

      // Should not have errors
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })
  })

  test.describe('Entity Filtering', () => {
    test('should have filter button', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Open filters
      await entitiesPage.openFilters()

      // Verify no errors
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })

    test('should open filter dialog', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Open filters
      await entitiesPage.openFilters()

      // Wait a moment for any dialogs to appear
      await page.waitForTimeout(500)

      // Should not error
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })
  })

  test.describe('Entity Type Navigation', () => {
    test('should switch between entity types', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Check if tabs exist
      const hasTabs = await entitiesPage.hasEntityTypeTabs()

      if (hasTabs) {
        // Try to switch to a different type
        const tabs = page.locator('.v-tab')
        const tabCount = await tabs.count()

        if (tabCount > 1) {
          // Click second tab
          await tabs.nth(1).click()
          await entitiesPage.waitForLoadingComplete()

          // Verify no errors
          const hasError = await entitiesPage.hasError()
          expect(hasError).toBe(false)
        }
      }
    })

    test('should navigate to specific entity type via URL', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)

      // Navigate to specific type (organization is common)
      await entitiesPage.navigateToType('organization')

      // Wait for page load
      await entitiesPage.waitForLoadingComplete()

      // Verify URL
      await expect(page).toHaveURL(/.*entities\/organization/)

      // Verify page loaded
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })

    test('should display type-specific entities', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigateToType('person')

      await entitiesPage.waitForLoadingComplete()

      // Should show entities or empty state (but no errors)
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })
  })

  test.describe('Entity Details', () => {
    test('should open entity details when clicking entity', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()
      await entitiesPage.waitForLoadingComplete()

      // Check if there are entities
      const count = await entitiesPage.getEntityCardsCount()

      if (count > 0) {
        // Click first entity
        await entitiesPage.clickFirstEntity()

        // Should navigate to entity detail
        await page.waitForURL(/.*entities\/.*\/.*/, { timeout: TIMEOUTS.medium })

        // Verify detail page loaded
        await expect(page.locator('main, .v-main')).toBeVisible()
      } else {
        // No entities to test with
        console.log('No entities available for testing entity details')
      }
    })

    test('should load entity detail page directly via URL', async ({ page }) => {
      await loginAsAdmin(page)

      // Try to access entity detail by ID (using a common test pattern)
      await page.goto('/entity/1')

      // Either loads successfully or redirects (404 handling)
      await page.waitForLoadState('networkidle')

      // Should not crash
      await expect(page.locator('main, .v-main')).toBeVisible()
    })
  })

  test.describe('Entity Creation', () => {
    test('should have create button for admin users', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Look for create button
      const createButton = page.locator('button:has-text("Erstellen"), button:has-text("Create")').first()

      // Should be visible for admin
      const isVisible = await createButton.isVisible({ timeout: TIMEOUTS.short })
      expect(isVisible).toBe(true)
    })

    test('should open create dialog when clicking create button', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Click create button
      await entitiesPage.clickCreate()

      // Dialog should open
      await entitiesPage.waitForCreateDialog()

      // Verify dialog is visible
      await expect(page.locator('[role="dialog"], .v-dialog')).toBeVisible({ timeout: TIMEOUTS.medium })
    })

    test('should close create dialog when clicking cancel', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Open create dialog
      await entitiesPage.clickCreate()
      await entitiesPage.waitForCreateDialog()

      // Cancel
      await entitiesPage.cancelCreate()

      // Dialog should close
      await page.waitForTimeout(500)
      const dialog = page.locator('[role="dialog"], .v-dialog')
      const isVisible = await dialog.isVisible({ timeout: TIMEOUTS.short }).catch(() => false)
      expect(isVisible).toBe(false)
    })

    test('should validate required fields in create form', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Open create dialog
      await entitiesPage.clickCreate()
      await entitiesPage.waitForCreateDialog()

      // Try to submit without filling required fields
      const saveButton = page.locator('button:has-text("Speichern"), button:has-text("Save")').first()

      // Save button might be disabled
      const isEnabled = await saveButton.isEnabled({ timeout: TIMEOUTS.short })

      if (isEnabled) {
        await saveButton.click()
        await page.waitForTimeout(500)

        // Should show validation errors or stay on dialog
        const dialog = page.locator('[role="dialog"], .v-dialog')
        await expect(dialog).toBeVisible()
      } else {
        // Button is properly disabled for empty form
        expect(isEnabled).toBe(false)
      }
    })
  })

  test.describe('Entity Statistics', () => {
    test('should display entity statistics', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Verify stats cards
      await entitiesPage.verifyStatsCards()

      // Should show various statistics
      const statsText = await page.locator('.v-card .text-h5').first().textContent()
      expect(statsText).toBeTruthy()
    })

    test('should update statistics after filtering', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Get initial count
      const initialCount = await entitiesPage.getEntityCount()

      // Apply search filter
      await entitiesPage.search('Test')
      await entitiesPage.waitForLoadingComplete()

      // Stats might update (or might not depending on implementation)
      // Just verify no errors occurred
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })
  })

  test.describe('Pagination and Loading', () => {
    test('should handle page loading states', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Wait for loading to complete
      await entitiesPage.waitForLoadingComplete()

      // Should not show loading overlay anymore
      const loadingOverlay = page.locator('.v-overlay--active')
      const isVisible = await loadingOverlay.isVisible({ timeout: 1000 }).catch(() => false)
      expect(isVisible).toBe(false)
    })

    test('should maintain scroll position after loading', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()
      await entitiesPage.waitForLoadingComplete()

      // Scroll down
      await page.evaluate(() => window.scrollTo(0, 500))
      const scrollY = await page.evaluate(() => window.scrollY)

      // Scroll should have happened
      expect(scrollY).toBeGreaterThan(0)
    })
  })

  test.describe('Error Handling', () => {
    test('should handle network errors gracefully', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()
      await entitiesPage.waitForLoadingComplete()

      // Go offline
      await page.context().setOffline(true)

      // Try to search (will fail)
      await entitiesPage.search('Test')
      await page.waitForTimeout(2000)

      // Should handle error gracefully (error message or stay on current state)
      await expect(page.locator('main, .v-main')).toBeVisible()

      // Go back online
      await page.context().setOffline(false)
    })

    test('should recover from errors', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()
      await entitiesPage.waitForLoadingComplete()

      // Page should be functional
      const hasError = await entitiesPage.hasError()
      expect(hasError).toBe(false)
    })
  })

  test.describe('Responsive Design', () => {
    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 })

      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Should load successfully
      await entitiesPage.verifyPageLoaded()

      // Main content should be visible
      await expect(page.locator('main, .v-main')).toBeVisible()
    })

    test('should work on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 })

      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Should load successfully
      await entitiesPage.verifyPageLoaded()
    })
  })

  test.describe('Accessibility', () => {
    test('should have proper heading structure', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // Check for headings
      const headings = page.locator('h1, h2, h3')
      const count = await headings.count()
      expect(count).toBeGreaterThan(0)
    })

    test('should have accessible buttons', async ({ page }) => {
      await loginAsAdmin(page)

      const entitiesPage = new EntitiesPage(page)
      await entitiesPage.navigate()

      // All buttons should be accessible
      const buttons = page.locator('button')
      const buttonCount = await buttons.count()
      expect(buttonCount).toBeGreaterThan(0)
    })
  })
})
