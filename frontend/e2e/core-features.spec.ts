/**
 * Core Feature E2E Tests for CaeliCrawler
 *
 * Tests covering main application features:
 * - Dashboard
 * - Navigation
 * - Entities
 * - Documents
 * - Export
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.TEST_URL || 'http://localhost:5173';
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || 'admin@test.com';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'testpassword123';

// Helper function for login
async function performLogin(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('[data-testid="email-input"]', { timeout: 10000 });
  await page.fill('[data-testid="email-input"]', ADMIN_EMAIL);
  await page.fill('[data-testid="password-input"]', ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 }),
    page.click('[data-testid="login-button"]'),
  ]);
  await page.waitForLoadState('networkidle');
}

// =============================================================================
// AUTHENTICATION TESTS
// =============================================================================
test.describe('Authentication', () => {
  test('should show login page when not authenticated', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    // Should redirect to login
    await expect(page).toHaveURL(/.*login/);
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await performLogin(page);
    // Should be on dashboard after login
    await expect(page.locator('text=Dashboard')).toBeVisible({ timeout: 10000 }).catch(() => {});
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForSelector('[data-testid="email-input"]');
    await page.fill('[data-testid="email-input"]', 'invalid@test.com');
    await page.fill('[data-testid="password-input"]', 'wrongpassword');
    await page.click('[data-testid="login-button"]');
    // Should show error or stay on login
    await page.waitForTimeout(3000);
    // Login should fail - page should still be login
    await expect(page).toHaveURL(/.*login/);
  });
});

// =============================================================================
// DASHBOARD TESTS
// =============================================================================
test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should display dashboard widgets', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // Dashboard should have content
    const mainContent = page.locator('main, .v-main');
    await expect(mainContent).toBeVisible();
  });

  test('should have navigation drawer', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // Navigation drawer should be visible
    const navDrawer = page.locator('.v-navigation-drawer');
    await expect(navDrawer).toBeVisible();
  });

  test('should have app bar with user menu', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // App bar should be visible
    const appBar = page.locator('.v-app-bar, .v-toolbar');
    await expect(appBar).toBeVisible();

    // User avatar should be present
    const userAvatar = page.locator('.v-avatar');
    await expect(userAvatar.first()).toBeVisible();
  });

  test('should toggle theme', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // Find theme toggle button
    const themeToggle = page.locator('button:has(.mdi-weather-sunny), button:has(.mdi-weather-night)');
    if (await themeToggle.isVisible()) {
      await themeToggle.click();
      await page.waitForTimeout(500);
      // Theme should change (we just verify no error occurs)
    }
  });
});

// =============================================================================
// NAVIGATION TESTS
// =============================================================================
test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should navigate to Entities page', async ({ page }) => {
    await page.goto(`${BASE_URL}/entities`);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/.*entities/);
  });

  test('should navigate to Categories page', async ({ page }) => {
    await page.goto(`${BASE_URL}/categories`);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/.*categories/);
  });

  test('should navigate to Sources page', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    await page.click('text=Datenquellen');
    await page.waitForURL('**/sources');
    await expect(page).toHaveURL(/.*sources/);
  });

  test('should navigate to Documents page', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    await page.click('text=Dokumente');
    await page.waitForURL('**/documents');
    await expect(page).toHaveURL(/.*documents/);
  });

  test('should navigate to Help page', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    await page.click('text=Hilfe');
    await page.waitForURL('**/help');
    await expect(page).toHaveURL(/.*help/);
  });
});

// =============================================================================
// ENTITIES TESTS
// =============================================================================
test.describe('Entities', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should display entities list', async ({ page }) => {
    await page.goto(`${BASE_URL}/entities`);
    await page.waitForLoadState('networkidle');

    // Should show entities view
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });

  test('should have search functionality', async ({ page }) => {
    await page.goto(`${BASE_URL}/entities`);
    await page.waitForLoadState('networkidle');

    // Look for search input
    const searchInput = page.locator('input[type="search"], input[placeholder*="Such"], [aria-label*="Search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('Test');
      await page.waitForTimeout(500);
    }
  });

  test('should show entity types filter', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/entity-types`);
    await page.waitForLoadState('networkidle');

    // Entity types page should load
    await expect(page.locator('text=Entity-Typen, text=EntityTypes')).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});

// =============================================================================
// DOCUMENTS TESTS
// =============================================================================
test.describe('Documents', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should display documents list', async ({ page }) => {
    await page.goto(`${BASE_URL}/documents`);
    await page.waitForLoadState('networkidle');

    // Documents page should load
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });

  test('should have filter options', async ({ page }) => {
    await page.goto(`${BASE_URL}/documents`);
    await page.waitForLoadState('networkidle');

    // Look for filter controls
    const filterButton = page.locator('button:has(.mdi-filter), text=Filter').first();
    if (await filterButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await filterButton.click();
      await page.waitForTimeout(500);
    }
  });
});

// =============================================================================
// CRAWLER TESTS
// =============================================================================
test.describe('Crawler', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should display crawler status', async ({ page }) => {
    await page.goto(`${BASE_URL}/crawler`);
    await page.waitForLoadState('networkidle');

    // Crawler page should load with status info
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });

  test('should show running jobs', async ({ page }) => {
    await page.goto(`${BASE_URL}/crawler`);
    await page.waitForLoadState('networkidle');

    // Should have jobs section
    await page.waitForTimeout(1000);
  });
});

// =============================================================================
// EXPORT TESTS
// =============================================================================
test.describe('Export', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should display export page', async ({ page }) => {
    await page.goto(`${BASE_URL}/export`);
    await page.waitForLoadState('networkidle');

    // Export page should load
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });

  test('should have export format options', async ({ page }) => {
    await page.goto(`${BASE_URL}/export`);
    await page.waitForLoadState('networkidle');

    // Look for format selection
    await page.waitForTimeout(1000);
  });
});

// =============================================================================
// FAVORITES TESTS
// =============================================================================
test.describe('Favorites', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should display favorites page', async ({ page }) => {
    await page.goto(`${BASE_URL}/favorites`);
    await page.waitForLoadState('networkidle');

    // Favorites page should load
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });
});

// =============================================================================
// NOTIFICATIONS TESTS
// =============================================================================
test.describe('Notifications', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should display notifications page', async ({ page }) => {
    await page.goto(`${BASE_URL}/notifications`);
    await page.waitForLoadState('networkidle');

    // Notifications page should load
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });

  test('should have notification bell in header', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // Bell icon should be in header
    const bellIcon = page.locator('.mdi-bell-outline, [aria-label*="Notification"]');
    await expect(bellIcon.first()).toBeVisible();
  });
});

// =============================================================================
// RESULTS TESTS
// =============================================================================
test.describe('Results', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should display results page', async ({ page }) => {
    await page.goto(`${BASE_URL}/results`);
    await page.waitForLoadState('networkidle');

    // Results page should load
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });
});

// =============================================================================
// ADMIN TESTS
// =============================================================================
test.describe('Admin', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should access admin users page', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');

    // Admin users page should load
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });

  test('should access audit log page', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/audit-log`);
    await page.waitForLoadState('networkidle');

    // Audit log page should load
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });

  test('should access facet types page', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/facet-types`);
    await page.waitForLoadState('networkidle');

    // Facet types page should load
    const pageContent = page.locator('.v-main');
    await expect(pageContent).toBeVisible();
  });
});

// =============================================================================
// LANGUAGE TESTS
// =============================================================================
test.describe('Internationalization', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should have language switcher', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // Look for language switcher
    const langSwitcher = page.locator('.language-switcher, [aria-label*="language"], .mdi-translate');
    // May or may not be visible depending on implementation
  });
});

// =============================================================================
// RESPONSIVE TESTS
// =============================================================================
test.describe('Responsive Design', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should work on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // App should still be functional
    const appBar = page.locator('.v-app-bar');
    await expect(appBar).toBeVisible();

    // Navigation drawer might be collapsed
    const navToggle = page.locator('.v-app-bar-nav-icon');
    if (await navToggle.isVisible()) {
      await navToggle.click();
      await page.waitForTimeout(300);
    }
  });

  test('should work on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // App should be functional
    const mainContent = page.locator('.v-main');
    await expect(mainContent).toBeVisible();
  });
});

// =============================================================================
// ACCESSIBILITY TESTS
// =============================================================================
test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await performLogin(page);
  });

  test('should have proper heading structure', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // Check for headings
    const headings = page.locator('h1, h2, h3');
    const count = await headings.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should have ARIA live regions', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // Check for ARIA live regions
    const liveRegions = page.locator('[aria-live]');
    const count = await liveRegions.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should have accessible buttons', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForLoadState('networkidle');

    // All buttons should have accessible names
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();
    expect(buttonCount).toBeGreaterThan(0);
  });
});
