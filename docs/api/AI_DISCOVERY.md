# AI Source Discovery API

The AI Source Discovery API enables intelligent, AI-powered discovery of data sources from the internet based on natural language prompts.

## Overview

This feature allows users to:
- Search the internet for data sources using natural language queries
- Automatically generate tags based on the search context
- Preview discovered sources before importing
- Bulk import selected sources with category assignments

## Endpoints

### POST /api/admin/ai-discovery/discover

Discover data sources based on a natural language prompt.

**Request Body:**
```json
{
  "prompt": "All German Bundesliga football clubs",
  "max_results": 50,
  "search_depth": "standard"
}
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| prompt | string | Yes | - | Natural language search query |
| max_results | integer | No | 50 | Maximum sources to return (10-200) |
| search_depth | string | No | "standard" | Search intensity: "quick", "standard", or "deep" |

**Response:**
```json
{
  "sources": [
    {
      "name": "FC Bayern München",
      "base_url": "https://fcbayern.com",
      "source_type": "WEBSITE",
      "tags": ["de", "bundesliga", "fußball", "fc-bayern"],
      "confidence": 0.95,
      "metadata": {
        "city": "München",
        "founded": "1900"
      }
    }
  ],
  "search_strategy": {
    "search_queries": ["Bundesliga Vereine Liste", "German football clubs websites"],
    "base_tags": ["de", "bundesliga", "fußball"],
    "expected_data_type": "sports_teams"
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

Import discovered sources into the system.

**Request Body:**
```json
{
  "sources": [
    {
      "name": "FC Bayern München",
      "base_url": "https://fcbayern.com",
      "source_type": "WEBSITE",
      "tags": ["de", "bundesliga", "fußball"]
    }
  ],
  "category_ids": ["uuid-of-category"],
  "skip_duplicates": true
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sources | array | Yes | Array of source objects to import |
| category_ids | array | No | Category IDs to assign to imported sources |
| skip_duplicates | boolean | No | Skip sources with existing URLs (default: true) |

**Response:**
```json
{
  "imported": 15,
  "skipped": 3,
  "errors": []
}
```

### GET /api/admin/ai-discovery/examples

Get example prompts for discovery.

**Response:**
```json
[
  {"prompt": "All German Bundesliga football clubs"},
  {"prompt": "Municipalities in Saxony"},
  {"prompt": "German universities"},
  {"prompt": "DAX companies"}
]
```

## Search Depths

| Depth | Queries | Description |
|-------|---------|-------------|
| quick | 3 | Fast results, basic coverage |
| standard | 5 | Balanced approach, recommended |
| deep | 8 | Thorough search, slower |

## Smart Query Integration

The AI Discovery can also be triggered via Smart Query:

```
"Find data sources for Bundesliga clubs"
"Search websites of municipalities in Bavaria"
"Import DAX companies as data sources"
```

The Smart Query system recognizes these patterns and executes the `discover_sources` operation.

## Configuration

Required environment variables:

| Variable | Description |
|----------|-------------|
| SERPER_API_KEY | API key for Serper.dev (Google Search API) |
| AI_DISCOVERY_MAX_SEARCH_RESULTS | Max search results per query (default: 20) |
| AI_DISCOVERY_MAX_EXTRACTION_PAGES | Max pages to extract from (default: 10) |
| AI_DISCOVERY_TIMEOUT | Request timeout in seconds (default: 60) |

## Error Handling

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Invalid request (e.g., empty prompt) |
| 401 | Unauthorized |
| 422 | Validation error |
| 500 | Server error |

## Rate Limits

- Discovery requests: 10 per minute
- Import requests: 5 per minute

## Examples

### cURL Examples

**Discover sources:**
```bash
curl -X POST "http://localhost:8000/api/admin/ai-discovery/discover" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "German universities", "max_results": 20, "search_depth": "standard"}'
```

**Import sources:**
```bash
curl -X POST "http://localhost:8000/api/admin/ai-discovery/import" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sources": [...], "category_ids": [], "skip_duplicates": true}'
```
