# E2E Tests for CaeliCrawler Frontend

This directory contains end-to-end tests for the CaeliCrawler application using Playwright.

## Test Structure

```
e2e/
├── fixtures/           # Test data and utilities
│   └── test-data.ts   # Test users, entities, queries
├── pages/             # Page Object Models
│   ├── BasePage.ts    # Base page with common functionality
│   ├── LoginPage.ts   # Login page object
│   ├── DashboardPage.ts
│   ├── EntitiesPage.ts
│   └── SmartQueryPage.ts
├── auth.spec.ts       # Authentication tests
├── entities.spec.ts   # Entity management tests
└── smart-query.spec.ts # Smart Query tests
```

## Test Files

### auth.spec.ts
Tests authentication flows:
- Successful login
- Failed login with invalid credentials
- Logout
- Session management
- Protected routes
- Password visibility toggle
- Keyboard navigation

### entities.spec.ts
Tests entity management:
- Display entities list
- Search entities
- Filter entities
- Entity type switching
- View entity details
- Create entity (admin)
- Statistics display
- Pagination

### smart-query.spec.ts
Tests Smart Query functionality:
- Query input and submission
- Mode switching (read/write/plan)
- Results display
- Visualizations (table, chart, map, text)
- Example queries
- History
- Error handling

## Page Objects

Page objects follow the **Page Object Pattern** to:
- Encapsulate page interactions
- Improve test maintainability
- Reduce code duplication
- Provide clear API for tests

### BasePage
Base class with common functionality:
- Navigation helpers
- Element locators
- Wait functions
- Screenshot utilities
- Error handling

### LoginPage
Login page interactions:
- Fill credentials
- Submit login
- Toggle password visibility
- Error message handling

### EntitiesPage
Entity management:
- Search entities
- Apply filters
- Create entities
- View entity details
- Switch entity types

### SmartQueryPage
Smart Query interactions:
- Enter queries
- Switch modes
- Submit queries
- View results
- Switch visualizations

## Running Tests

### Prerequisites
```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install
```

### Run all tests
```bash
npm run test:e2e
```

### Run specific test file
```bash
npx playwright test auth.spec.ts
npx playwright test entities.spec.ts
npx playwright test smart-query.spec.ts
```

### Run with UI mode (interactive)
```bash
npx playwright test --ui
```

### Run in headed mode (see browser)
```bash
npx playwright test --headed
```

### Run specific test by name
```bash
npx playwright test -g "should login successfully"
```

### Run tests in debug mode
```bash
npx playwright test --debug
```

## Environment Variables

Configure tests using environment variables:

```bash
# Test environment URL
TEST_URL=http://localhost:5173

# Test user credentials
ADMIN_EMAIL=admin@test.com
ADMIN_PASSWORD=testpassword123

EDITOR_EMAIL=editor@test.com
EDITOR_PASSWORD=editor123

VIEWER_EMAIL=viewer@test.com
VIEWER_PASSWORD=viewer123
```

Create a `.env.test` file:
```bash
TEST_URL=http://localhost:5173
ADMIN_EMAIL=admin@test.com
ADMIN_PASSWORD=testpassword123
```

## Test Reports

After running tests, view the HTML report:
```bash
npx playwright show-report
```

Reports are generated in:
- `test-results/html-report/` - HTML report
- `test-results/test-results.json` - JSON report
- `test-results/junit.xml` - JUnit XML report

## Test Artifacts

On test failure, Playwright captures:
- Screenshots: `test-results/*.png`
- Videos: `test-results/*.webm`
- Traces: `test-results/*.zip` (use `npx playwright show-trace`)

## Best Practices

### 1. Use Page Objects
```typescript
// Good
const loginPage = new LoginPage(page)
await loginPage.login('user@test.com', 'password')

// Avoid
await page.fill('[data-testid="email"]', 'user@test.com')
await page.fill('[data-testid="password"]', 'password')
await page.click('[data-testid="login-button"]')
```

### 2. Use data-testid Selectors
```typescript
// Good
await page.locator('[data-testid="email-input"]').fill('test@test.com')

// Avoid (brittle)
await page.locator('.v-text-field input').first().fill('test@test.com')
```

### 3. Wait for Elements
```typescript
// Good
await page.waitForSelector('[data-testid="results"]', { state: 'visible' })

// Avoid
await page.waitForTimeout(3000)
```

### 4. Handle Async Operations
```typescript
// Good
await loginPage.loginAndWaitForNavigation(user.email, user.password)

// Avoid
await loginPage.login(user.email, user.password)
// Missing navigation wait
```

### 5. Test Isolation
Each test should be independent:
```typescript
test.beforeEach(async ({ page }) => {
  // Fresh login for each test
  await loginAsAdmin(page)
})
```

## CI/CD Integration

Tests can be run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run E2E tests
  run: |
    npm run build
    npm run test:e2e
  env:
    TEST_URL: http://localhost:5173
    ADMIN_EMAIL: ${{ secrets.TEST_ADMIN_EMAIL }}
    ADMIN_PASSWORD: ${{ secrets.TEST_ADMIN_PASSWORD }}
```

## Debugging

### Visual debugging with UI mode
```bash
npx playwright test --ui
```

### Step through tests
```bash
npx playwright test --debug
```

### View trace file
```bash
npx playwright show-trace test-results/trace.zip
```

### Generate trace on all tests
```bash
npx playwright test --trace on
```

## Adding New Tests

### 1. Create Page Object (if needed)
```typescript
// e2e/pages/MyNewPage.ts
import { Page } from '@playwright/test'
import { BasePage } from './BasePage'

export class MyNewPage extends BasePage {
  constructor(page: Page) {
    super(page)
  }

  async navigate(): Promise<void> {
    await this.goto('/my-route')
    await this.waitForPageLoad()
  }
}
```

### 2. Create Test File
```typescript
// e2e/my-feature.spec.ts
import { test, expect } from '@playwright/test'
import { LoginPage } from './pages/LoginPage'
import { MyNewPage } from './pages/MyNewPage'

test.describe('My Feature', () => {
  test('should do something', async ({ page }) => {
    // Test implementation
  })
})
```

### 3. Add Test Data
```typescript
// e2e/fixtures/test-data.ts
export const MY_TEST_DATA = {
  // Test data here
}
```

## Troubleshooting

### Tests fail with timeout
- Increase timeout in `playwright.config.ts`
- Check if backend is running
- Check network connectivity

### Cannot find elements
- Verify selectors with Playwright Inspector
- Add `data-testid` attributes to components
- Use Playwright Codegen to generate selectors

### Tests are flaky
- Add proper waits for dynamic content
- Use `waitForLoadState('networkidle')`
- Avoid `waitForTimeout`, use element waits

### Screenshots/videos not captured
- Check `playwright.config.ts` settings
- Verify `test-results/` directory exists
- Check disk space

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Page Object Pattern](https://playwright.dev/docs/pom)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging Tests](https://playwright.dev/docs/debug)
