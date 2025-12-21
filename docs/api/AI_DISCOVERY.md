# AI Source Discovery API

The AI Source Discovery API enables intelligent, AI-powered discovery of data sources from the internet based on natural language prompts.

## Overview

This feature allows users to:
- Search the internet for data sources using natural language queries
- **KI-First Discovery (V2)**: AI suggests APIs directly, validates them, then falls back to web search
- Automatically generate tags based on the search context
- Preview discovered sources before importing
- **Save successful API discoveries as reusable templates**
- Bulk import selected sources with category assignments

## Architecture (V2 - KI-First)

The V2 discovery follows this flow:

```
[User Prompt: "Alle Bundesliga-Vereine"]
         ↓
1. Check saved templates (keyword matching)
         ↓ (no match)
2. AI generates API suggestions
   [OpenLigaDB, Football-Data.org, ...]
         ↓
3. Validate API suggestions (HTTP tests)
   ✓ OpenLigaDB → 200 OK, 18 items
   ✗ Football-Data.org → 401 Unauthorized
         ↓
4. Extract data from valid APIs
         ↓ (no valid APIs)
5. Fallback to SERP-based web search
         ↓
[Result: API sources + Web sources]
```

---

## V2 Endpoints (KI-First)

### POST /api/admin/ai-discovery/discover-v2

KI-First discovery: AI suggests APIs, validates them, extracts data.

**Request Body:**
```json
{
  "prompt": "Alle deutschen Bundesliga-Fußballvereine",
  "max_results": 50,
  "search_depth": "standard",
  "skip_api_discovery": false
}
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| prompt | string | Yes | - | Natural language search query |
| max_results | integer | No | 50 | Maximum sources to return (10-200) |
| search_depth | string | No | "standard" | Search intensity: "quick", "standard", "deep" |
| skip_api_discovery | boolean | No | false | Skip AI API suggestions, go directly to web search |

**Response:**
```json
{
  "api_sources": [
    {
      "api_name": "OpenLigaDB",
      "api_url": "https://api.openligadb.de/getavailableteams/bl1/2024",
      "api_type": "REST",
      "item_count": 18,
      "sample_items": [
        {"teamId": 40, "teamName": "FC Bayern München", "shortName": "Bayern"},
        {"teamId": 7, "teamName": "Borussia Dortmund", "shortName": "Dortmund"}
      ],
      "tags": ["bundesliga", "fußball", "rest"],
      "field_mapping": {"teamName": "name", "teamIconUrl": "icon_url"}
    }
  ],
  "web_sources": [],
  "api_suggestions": [
    {
      "api_name": "OpenLigaDB",
      "base_url": "https://api.openligadb.de",
      "endpoint": "/getavailableteams/bl1/2024",
      "description": "German football leagues data",
      "api_type": "REST",
      "auth_required": false,
      "confidence": 0.9
    },
    {
      "api_name": "Football-Data.org",
      "base_url": "https://api.football-data.org",
      "endpoint": "/v4/competitions/BL1/teams",
      "api_type": "REST",
      "auth_required": true,
      "confidence": 0.7
    }
  ],
  "api_validations": [
    {
      "api_name": "OpenLigaDB",
      "is_valid": true,
      "status_code": 200,
      "item_count": 18,
      "field_mapping": {"teamName": "name"}
    },
    {
      "api_name": "Football-Data.org",
      "is_valid": false,
      "status_code": 401,
      "error_message": "Authentication required"
    }
  ],
  "stats": {
    "pages_searched": 0,
    "sources_extracted": 18,
    "sources_validated": 1
  },
  "warnings": [],
  "used_fallback": false,
  "from_template": false
}
```

### POST /api/admin/ai-discovery/import-api-data

Import data from a validated API as DataSources.

**Request Body:**
```json
{
  "api_name": "OpenLigaDB",
  "api_url": "https://api.openligadb.de/getavailableteams/bl1/2024",
  "field_mapping": {
    "teamName": "name",
    "teamIconUrl": "icon_url"
  },
  "items": [
    {"teamId": 40, "teamName": "FC Bayern München"},
    {"teamId": 7, "teamName": "Borussia Dortmund"}
  ],
  "category_ids": ["uuid-of-category"],
  "tags": ["de", "bundesliga", "fußball"],
  "skip_duplicates": true
}
```

**Response:**
```json
{
  "imported": 18,
  "skipped": 0,
  "errors": []
}
```

---

## API Templates

Templates store validated API configurations for reuse. When a user searches for "Bundesliga teams" and a matching template exists, it's used directly without AI generation.

### GET /api/admin/api-templates

List all API templates.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by status: ACTIVE, INACTIVE, FAILED, PENDING |
| api_type | string | Filter by type: REST, GRAPHQL, SPARQL, OPARL |
| limit | integer | Max results (default: 50) |
| offset | integer | Pagination offset |

**Response:**
```json
{
  "templates": [
    {
      "id": "uuid",
      "name": "OpenLigaDB Bundesliga",
      "description": "18 Bundesliga teams",
      "api_type": "REST",
      "base_url": "https://api.openligadb.de",
      "endpoint": "/getavailableteams/bl1/2024",
      "keywords": ["bundesliga", "fußball", "vereine"],
      "default_tags": ["de", "bundesliga"],
      "status": "ACTIVE",
      "usage_count": 5,
      "last_validated": "2024-12-21T10:30:00Z",
      "validation_item_count": 18
    }
  ],
  "total": 1
}
```

### POST /api/admin/api-templates

Create a new API template manually.

**Request Body:**
```json
{
  "name": "OpenLigaDB Bundesliga",
  "description": "All 18 current Bundesliga teams",
  "api_type": "REST",
  "base_url": "https://api.openligadb.de",
  "endpoint": "/getavailableteams/bl1/2024",
  "documentation_url": "https://www.openligadb.de/Help",
  "auth_required": false,
  "field_mapping": {
    "teamName": "name",
    "teamIconUrl": "icon_url"
  },
  "keywords": ["bundesliga", "fußball", "vereine", "sport"],
  "default_tags": ["de", "bundesliga", "sport"]
}
```

### POST /api/admin/api-templates/save-from-discovery

Save a successful discovery result as a template.

**Request Body:**
```json
{
  "name": "OpenLigaDB Bundesliga",
  "description": "From AI Discovery",
  "api_type": "REST",
  "base_url": "https://api.openligadb.de",
  "endpoint": "/getavailableteams/bl1/2024",
  "field_mapping": {"teamName": "name"},
  "keywords": ["bundesliga", "fußball"],
  "default_tags": ["de", "bundesliga"],
  "confidence": 0.9,
  "validation_item_count": 18
}
```

### POST /api/admin/api-templates/{id}/test

Test/validate an existing template.

**Response:**
```json
{
  "is_valid": true,
  "status_code": 200,
  "item_count": 18,
  "sample_items": [...],
  "validation_time_ms": 245
}
```

### GET /api/admin/api-templates/match/{prompt}

Find templates matching a search prompt.

**Example:** `GET /api/admin/api-templates/match/bundesliga%20vereine`

**Response:**
```json
{
  "matched_templates": [
    {
      "template_id": "uuid",
      "name": "OpenLigaDB Bundesliga",
      "match_score": 0.85,
      "keywords_matched": ["bundesliga", "vereine"]
    }
  ]
}
```

---

## V1 Endpoints (Legacy)

### POST /api/admin/ai-discovery/discover

SERP-based discovery (web search only).

**Request Body:**
```json
{
  "prompt": "All German Bundesliga football clubs",
  "max_results": 50,
  "search_depth": "standard"
}
```

**Response:**
```json
{
  "sources": [
    {
      "name": "FC Bayern München",
      "base_url": "https://fcbayern.com",
      "source_type": "WEBSITE",
      "tags": ["de", "bundesliga", "fußball", "fc-bayern"],
      "confidence": 0.95
    }
  ],
  "search_strategy": {
    "search_queries": ["Bundesliga Vereine Liste"],
    "base_tags": ["de", "bundesliga", "fußball"]
  },
  "stats": {
    "pages_searched": 15,
    "sources_extracted": 25,
    "duplicates_removed": 7,
    "sources_validated": 18
  },
  "warnings": []
}
```

### POST /api/admin/ai-discovery/import

Import discovered web sources.

### GET /api/admin/ai-discovery/examples

Get example prompts.

---

## Search Depths

| Depth | Queries | Description |
|-------|---------|-------------|
| quick | 3 | Fast results, basic coverage |
| standard | 5 | Balanced approach, recommended |
| deep | 8 | Thorough search, slower |

## API Types

| Type | Description |
|------|-------------|
| REST | Standard REST API with JSON response |
| GRAPHQL | GraphQL API |
| SPARQL | SPARQL endpoint (e.g., Wikidata) |
| OPARL | OParl API for German council systems |

## Template Status

| Status | Description |
|--------|-------------|
| ACTIVE | Template is active and can be used |
| INACTIVE | Disabled by admin |
| FAILED | Last validation failed |
| PENDING | Awaiting initial validation |

## Configuration

Required environment variables:

| Variable | Description |
|----------|-------------|
| SERPER_API_KEY | API key for Serper.dev (SERP fallback) |
| AZURE_OPENAI_ENDPOINT | OpenAI endpoint for AI suggestions |
| AI_DISCOVERY_USE_CLAUDE | Use Claude for better API knowledge (optional) |
| ANTHROPIC_API_ENDPOINT | Claude API endpoint (optional) |

## Rate Limits

- Discovery requests (V1 & V2): 10 per minute
- Import requests: 20 per minute
- Template operations: 30 per minute

## cURL Examples

**V2 Discovery:**
```bash
curl -X POST "http://localhost:8000/api/admin/ai-discovery/discover-v2" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Bundesliga Vereine", "max_results": 20}'
```

**Save as Template:**
```bash
curl -X POST "http://localhost:8000/api/admin/api-templates/save-from-discovery" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenLigaDB Bundesliga",
    "base_url": "https://api.openligadb.de",
    "endpoint": "/getavailableteams/bl1/2024",
    "keywords": ["bundesliga", "fußball"],
    "field_mapping": {"teamName": "name"}
  }'
```

**Test Template:**
```bash
curl -X POST "http://localhost:8000/api/admin/api-templates/TEMPLATE_ID/test" \
  -H "Authorization: Bearer YOUR_TOKEN"
```
