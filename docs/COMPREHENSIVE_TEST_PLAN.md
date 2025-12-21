# Comprehensive Test Plan

This document outlines the complete testing strategy for CaeliCrawler, including unit tests, integration tests, and E2E tests.

## Test Categories

### 1. Unit Tests

#### Backend Services

| Service | Test File | Coverage |
|---------|-----------|----------|
| AI Source Discovery | `tests/test_services/test_ai_discovery.py` | Models, Extractors, Service |
| Multi-Entity Extraction | `tests/test_services/test_multi_entity_extraction.py` | Prompt generation, Entity creation |
| Smart Query | `tests/test_services/test_smart_query.py` | Query parsing, Write execution |
| Entity Facet Service | `tests/test_services/test_entity_facet.py` | Facet CRUD operations |
| Change Tracker | `tests/test_services/test_change_tracker.py` | Version tracking |

#### Backend Models

| Model | Test File | Coverage |
|-------|-----------|----------|
| DataSource (Tags) | `tests/test_models/test_datasource.py` | Tag validation, filtering |
| CategoryEntityType | `tests/test_models/test_category_entity_type.py` | N:M relationships |
| Entity | `tests/test_models/test_entity.py` | Core attributes, soft delete |

### 2. Integration Tests (API)

#### AI Discovery API

| Endpoint | Test Case | Expected Result |
|----------|-----------|-----------------|
| POST /api/admin/ai-discovery/discover | Valid prompt | 200 + sources list |
| POST /api/admin/ai-discovery/discover | Empty prompt | 400/422 validation error |
| POST /api/admin/ai-discovery/import | Import sources | 200 + imported count |
| GET /api/admin/ai-discovery/examples | Get examples | 200 + example prompts |

#### Smart Query API

| Endpoint | Test Case | Expected Result |
|----------|-----------|-----------------|
| POST /api/v1/smart-query/execute | discover_sources intent | Returns discovered sources |
| POST /api/v1/smart-query/execute | start_crawl with tags | Filters sources by tag |
| POST /api/v1/smart-query/execute | create_category_setup | Creates category with tags |

#### DataSource API (Tags)

| Endpoint | Test Case | Expected Result |
|----------|-----------|-----------------|
| GET /api/admin/sources/tags | List all tags | Returns unique tags |
| GET /api/admin/sources?tags=nrw | Filter by tag | Returns matching sources |
| POST /api/admin/sources | Create with tags | Tags saved correctly |
| PUT /api/admin/sources/{id} | Update tags | Tags updated |
| POST /api/admin/categories/{id}/assign-by-tags | Assign by tags | Sources linked to category |

#### Multi-EntityType API

| Endpoint | Test Case | Expected Result |
|----------|-----------|-----------------|
| POST /api/admin/categories/{id}/entity-types | Add entity type | Association created |
| GET /api/admin/categories/{id}/entity-types | List entity types | Returns configured types |
| DELETE /api/admin/categories/{id}/entity-types/{type_id} | Remove type | Association deleted |

### 3. End-to-End Tests

#### User Workflows

##### Workflow 1: AI-Powered Source Discovery
```
1. User opens Sources view
2. Clicks "Import" -> "AI Search"
3. Enters prompt: "Bundesliga Vereine"
4. Selects search depth "standard"
5. Clicks "Start Search"
6. Views results with auto-generated tags
7. Selects sources to import
8. Clicks "Import"
9. Verifies sources appear in list with tags
```

##### Workflow 2: Tag-Based Category Assignment
```
1. Admin opens Category dialog
2. Switches to "Data Sources" tab
3. Selects tags: ["nrw", "kommunal"]
4. Chooses match mode "AND"
5. Previews matching sources
6. Clicks "Assign"
7. Verifies sources linked to category
```

##### Workflow 3: Multi-EntityType Category Setup
```
1. Admin creates new category
2. Adds EntityType "Person" (primary)
3. Adds EntityType "Event"
4. Configures relation: Person attends Event
5. Saves category
6. Runs crawl
7. Verifies entities and relations created
```

##### Workflow 4: Smart Query Source Discovery
```
1. User opens Smart Query
2. Enters: "Finde Datenquellen für Universitäten"
3. System recognizes discover_sources intent
4. Results displayed with tags
5. User confirms import
6. Sources added to system
```

##### Workflow 5: Assistant Tag Query
```
1. User opens Assistant
2. Asks: "Welche Tags gibt es?"
3. Assistant returns tag list
4. User asks: "Zeige Quellen mit Tag bayern"
5. Assistant returns filtered sources
```

### 4. Performance Tests

| Test | Criteria | Target |
|------|----------|--------|
| Source list with 10k sources | Load time | < 2s |
| Tag filtering (complex) | Response time | < 500ms |
| AI Discovery (quick) | Total time | < 15s |
| AI Discovery (deep) | Total time | < 60s |
| Multi-entity extraction | Per document | < 5s |

### 5. Security Tests

| Test | Description |
|------|-------------|
| Auth Required | All admin endpoints require authentication |
| Rate Limiting | AI Discovery limited to 10 req/min |
| Input Validation | Prompts sanitized, max length enforced |
| SQL Injection | Tag filters properly escaped |

## Test Execution

### Running Unit Tests

```bash
cd backend
pytest tests/test_services/ -v
pytest tests/test_models/ -v
```

### Running Integration Tests

```bash
cd backend
pytest tests/test_api/ -v --cov=app
```

### Running E2E Tests

```bash
cd frontend
npm run test:e2e
```

### Running All Tests

```bash
# Backend
cd backend
pytest tests/ -v --cov=app --cov=services --cov-report=html

# Frontend
cd frontend
npm run test:unit
npm run test:e2e
```

## Test Data

### Fixtures

```python
# conftest.py additions

@pytest.fixture
async def sample_tags():
    return ["de", "nrw", "kommunal", "oparl"]

@pytest.fixture
async def sources_with_tags(session, sample_tags):
    sources = []
    for i, tag in enumerate(sample_tags):
        source = DataSource(
            name=f"Test Source {i}",
            base_url=f"https://test{i}.de",
            tags=[tag, "test"],
        )
        session.add(source)
        sources.append(source)
    await session.commit()
    return sources

@pytest.fixture
async def category_with_entity_types(session, sample_entity_types):
    category = Category(
        name="Test Multi-Type",
        slug="test-multi-type",
        purpose="Testing multi-entity extraction",
    )
    session.add(category)
    await session.flush()

    for i, et in enumerate(sample_entity_types):
        assoc = CategoryEntityType(
            category_id=category.id,
            entity_type_id=et.id,
            is_primary=(i == 0),
            extraction_order=i,
        )
        session.add(assoc)

    await session.commit()
    return category
```

## Coverage Requirements

| Component | Minimum Coverage |
|-----------|------------------|
| Backend API | 80% |
| Backend Services | 75% |
| Frontend Components | 70% |
| E2E Critical Paths | 100% |

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio httpx

      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov=services

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Run unit tests
        run: |
          cd frontend
          npm run test:unit

      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e
```

## Test Reporting

### Metrics to Track

- Total test count
- Pass/Fail ratio
- Code coverage %
- Test execution time
- Flaky test rate

### Reporting Tools

- pytest-html for HTML reports
- coverage.py for coverage reports
- Allure for comprehensive test reporting
