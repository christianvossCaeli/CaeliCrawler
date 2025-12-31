#!/usr/bin/env python3
"""
Seed script to populate the database with UK-specific categories and data sources
for Wind Energy Sales Intelligence.

Use Case:
- Monitor UK council publications (local council meetings, planning decisions, news)
- Identify pain points and positive signals regarding wind energy
- Enable personalized outreach to UK local authorities

Run with: python -m scripts.seed_uk_data
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import get_session_context
from app.models import Category, DataSource, SourceStatus, SourceType

# =============================================================================
# UK CATEGORIES - Organized by Sales Intelligence Goals
# =============================================================================

UK_CATEGORIES = [
    # -------------------------------------------------------------------------
    # 1. UK LOCAL COUNCIL INFORMATION
    # -------------------------------------------------------------------------
    {
        "name": "UK Council Information",
        "slug": "uk-council-information",
        "description": "Local council meetings, planning decisions and documents from UK municipalities",
        "purpose": """Monitoring local council decisions on wind energy:
- Local development plans and wind farm zones
- Planning applications and objections
- Public consultations and opposition
- Planning policy decisions""",
        "languages": ["en"],
        "search_terms": [
            "wind farm", "wind energy", "wind turbine", "wind power",
            "renewable energy", "onshore wind", "offshore wind",
            "planning application", "planning permission", "local plan",
            "green energy", "clean energy", "net zero",
            "repowering", "setback distance", "noise impact"
        ],
        "url_include_patterns": [
            "/(council|planning|committee|agenda|minutes|decision|meeting|document)/",
            "/(environment|energy|climate|sustainability)/",
            "/planning[-_]?application/",
            "/local[-_]?plan/",
        ],
        "url_exclude_patterns": [
            "/(login|register|contact|privacy|terms|cookie|accessibility)/",
            "/(jobs|careers|vacancies)/",
            "/\\?page=",
            "/search/",
        ],
        "ai_extraction_prompt": """Analyze this UK council document for Sales Intelligence in the wind energy sector.

IMPORTANT: Extract ONLY information that DIRECTLY relates to wind energy, wind farms, or renewable energy!
- Ignore general council matters (budget, personnel, traffic, etc.) COMPLETELY
- Pain points and positive signals must relate to wind energy/renewables
- If the document has NO wind energy relevant content, set is_relevant=false and leave pain_points/positive_signals EMPTY

EXTRACT IN JSON FORMAT:
{
  "is_relevant": true/false (ONLY true if wind energy/renewable energy is explicitly discussed),
  "relevance": "high|medium|low|none",
  "municipality": "Name of the council/local authority",
  "document_type": "Planning Decision|Council Minutes|Committee Report|Consultation|Other",
  "document_date": "YYYY-MM-DD or null",

  "pain_points": [
    ONLY wind energy related issues! Examples:
    - Community opposition to wind farms
    - Environmental/wildlife concerns for wind projects
    - Setback distance regulations for wind turbines
    - Noise complaints about turbines
    - Planning application rejections
    {
      "type": "Community Opposition|Environmental|Setback Distance|Planning|Noise|Visual Impact|Wildlife",
      "description": "Specific description of the wind energy issue",
      "severity": "high|medium|low",
      "quote": "Original quote from document"
    }
  ],

  "positive_signals": [
    ONLY wind energy related positive signals! Examples:
    - Interest in wind energy development
    - Planning approvals for wind farms
    - Community wind farm initiatives
    - Climate targets with wind energy focus
    - Site allocations for wind development
    {
      "type": "Interest|Planning|Approval|Community Project|Climate Target|Site Allocation",
      "description": "Specific description of the positive wind energy signal",
      "quote": "Original quote"
    }
  ],

  "decision_makers": [
    ONLY persons involved in energy/wind decisions
    {
      "name": "Person's name",
      "role": "Councillor|Planning Officer|Cabinet Member|Officer|Executive Director",
      "stance": "positive|neutral|negative|unknown (towards wind energy)"
    }
  ],

  "current_status": "Planning|Under Review|Approved|Rejected|Consultation|Unknown",
  "timeline": "Mentioned deadlines or timelines for wind projects",
  "next_steps": ["Next planned steps regarding wind energy"],

  "outreach_recommendation": {
    "priority": "high|medium|low",
    "approach": "Recommended engagement strategy",
    "key_message": "Core message for outreach",
    "contact_timing": "Optimal timing for contact"
  },

  "summary": "Brief summary focusing on wind energy aspects (2-3 sentences)"
}

REMEMBER: If no wind energy content is present -> is_relevant=false, pain_points=[], positive_signals=[]""",
        "schedule_cron": "0 6 * * *",  # Daily at 6 AM
    },

    # -------------------------------------------------------------------------
    # 2. UK LOCAL AUTHORITY NEWS & PRESS RELEASES
    # -------------------------------------------------------------------------
    {
        "name": "UK Council News & Press",
        "slug": "uk-council-news",
        "description": "News and press releases from UK local authorities",
        "purpose": """Monitoring public communications on wind energy:
- Press releases about energy projects
- News about community engagement
- Announcements of public consultations
- Statements from councillors and officers""",
        "languages": ["en"],
        "search_terms": [
            "wind farm", "wind energy", "renewable energy",
            "energy transition", "climate action", "community energy",
            "wind turbine", "public consultation"
        ],
        "url_include_patterns": [
            "/(news|press|media|announcement|update)/",
            "/(climate|environment|energy|sustainability)/",
        ],
        "url_exclude_patterns": [
            "/(login|register|contact|privacy|terms)/",
            "/(jobs|careers)/",
            "/\\?page=",
        ],
        "ai_extraction_prompt": """Analyze this UK council press release/news for Sales Intelligence.

EXTRACT IN JSON FORMAT:
{
  "is_relevant": true/false,
  "municipality": "Name of the council/local authority",
  "publication_date": "YYYY-MM-DD",
  "news_type": "Press Release|Announcement|Report|Statement",

  "topic": "Main topic of the news item",
  "sentiment": "positive|neutral|negative|mixed",

  "decision_makers": [
    {
      "person": "Name",
      "role": "Position",
      "statement": "Quote",
      "sentiment": "positive|neutral|negative"
    }
  ],

  "events_mentioned": [
    {
      "type": "Public Consultation|Council Meeting|Community Event",
      "date": "YYYY-MM-DD or null",
      "location": "Location"
    }
  ],

  "positive_signals": ["Identified opportunities for engagement"],
  "pain_points": ["Mentioned concerns or problems"],

  "contact_opportunity": {
    "exists": true/false,
    "type": "Event|Meeting|Consultation",
    "timing": "Time window"
  },

  "summary": "Brief summary"
}""",
        "schedule_cron": "0 8 * * *",
    },

    # -------------------------------------------------------------------------
    # 3. UK PARLIAMENTARY & GOVERNMENT
    # -------------------------------------------------------------------------
    {
        "name": "UK Parliamentary Energy Questions",
        "slug": "uk-parliamentary-questions",
        "description": "Parliamentary questions and debates on energy topics",
        "purpose": """Monitoring the political landscape:
- Parliamentary questions on wind energy regulation
- Legislative initiatives
- Statistical queries on planning approvals
- Political positions""",
        "languages": ["en"],
        "search_terms": [
            "wind energy", "wind farm", "renewable energy",
            "planning permission", "onshore wind", "offshore wind",
            "energy security", "net zero"
        ],
        "url_include_patterns": [
            "/(hansard|parliament|debate|question|motion)/",
            "/(commons|lords)/",
            "/(legislation|bill|act)/",
        ],
        "url_exclude_patterns": [
            "/(login|register)/",
            "/\\?page=",
        ],
        "ai_extraction_prompt": """Analyze this UK parliamentary document for Market Intelligence.

EXTRACT IN JSON FORMAT:
{
  "is_relevant": true/false,
  "document_type": "Written Question|Oral Question|Debate|Motion|Bill",
  "parliamentary_session": "Session period",
  "date": "YYYY-MM-DD",

  "initiators": [
    {
      "name": "Name",
      "party": "Party",
      "role": "MP|Lord|Minister"
    }
  ],

  "main_topic": "Main topic",
  "sub_topics": ["Sub-topics"],

  "regulatory_changes": [
    {
      "type": "Planned|Discussed|Enacted",
      "description": "Description of change",
      "impact": "Impact on wind energy"
    }
  ],

  "statistics_mentioned": [
    {
      "metric": "What is measured",
      "value": "Value",
      "region": "Affected region"
    }
  ],

  "political_positions": {
    "pro_wind": ["Arguments/positions"],
    "contra_wind": ["Arguments/positions"]
  },

  "market_implications": "Market impact",
  "summary": "Brief summary"
}""",
        "schedule_cron": "0 9 * * 1-5",
    },

    # -------------------------------------------------------------------------
    # 4. UK FOI REQUESTS
    # -------------------------------------------------------------------------
    {
        "name": "UK FOI Requests - Wind Energy",
        "slug": "uk-foi-requests",
        "description": "Freedom of Information requests on wind energy topics",
        "purpose": """Insights into governmental processes:
- Planning application processes
- Internal authority communications
- Reports and studies
- Refusal reasons""",
        "languages": ["en"],
        "search_terms": [
            "wind farm", "wind energy", "planning application",
            "wind turbine", "environmental impact", "noise assessment"
        ],
        "url_include_patterns": [
            "/(foi|freedom-of-information|disclosure|request)/",
            "/(whatdotheyknow)/",
        ],
        "url_exclude_patterns": [
            "/(login|register)/",
        ],
        "ai_extraction_prompt": """Analyze this UK FOI request/response for Business Intelligence.

EXTRACT IN JSON FORMAT:
{
  "is_relevant": true/false,
  "request_topic": "Topic of the request",
  "authority": "Authority requested from",
  "status": "successful|partially_successful|refused|pending",

  "information_revealed": [
    {
      "type": "Report|Correspondence|Statistics|Decision",
      "description": "What was disclosed",
      "relevance": "high|medium|low"
    }
  ],

  "approval_barriers": ["Identified barriers in the planning process"],
  "processing_times": "Mentioned processing times",
  "refusal_reasons": ["Refusal reasons if mentioned"],

  "business_insights": ["Business-relevant insights"],
  "summary": "Brief summary"
}""",
        "schedule_cron": "0 10 * * 3",
    },

    # -------------------------------------------------------------------------
    # 5. UK OPEN DATA - SITE ANALYSIS
    # -------------------------------------------------------------------------
    {
        "name": "UK Site Data - Wind Energy",
        "slug": "uk-site-data",
        "description": "Open data for wind energy site assessment",
        "purpose": """Data foundation for site analysis:
- Wind potential areas
- Protected areas and restrictions
- Existing installations
- Grid infrastructure""",
        "languages": ["en"],
        "search_terms": [
            "wind energy", "wind potential", "designated area",
            "conservation area", "landscape protection", "grid connection"
        ],
        "url_include_patterns": [
            "/(data|dataset|download|resource)/",
            "/(energy|environment|planning)/",
        ],
        "url_exclude_patterns": [
            "/(login|register)/",
        ],
        "ai_extraction_prompt": """Describe this dataset for site analysis.

EXTRACT IN JSON FORMAT:
{
  "dataset_name": "Dataset name",
  "publisher": "Publisher",
  "geographic_coverage": "Geographic coverage",
  "temporal_coverage": "Temporal coverage",
  "update_frequency": "Update frequency",

  "data_type": "Geodata|Statistics|Register|Report",
  "relevance_for": ["Site Search", "Restriction Analysis", "Potential Analysis"],

  "key_attributes": ["Key attributes included"],
  "data_quality": "high|medium|low|unknown",
  "access_type": "Download|API|WMS|WFS",

  "use_cases": ["Possible use cases"],
  "summary": "Brief description"
}""",
        "schedule_cron": "0 2 * * 0",
    },

    # -------------------------------------------------------------------------
    # 6. UK LEAD QUALIFICATION (Meta-Category)
    # -------------------------------------------------------------------------
    {
        "name": "UK Lead Qualification",
        "slug": "uk-lead-qualification",
        "description": "Aggregated assessment of UK local authorities as potential leads",
        "purpose": """Consolidated lead assessment:
- Consolidation of all signals per local authority
- Lead scoring based on activity
- Sales prioritization
- Personalized engagement recommendations""",
        "languages": ["en"],
        "search_terms": [],  # Meta-category, no direct search
        "url_include_patterns": [],
        "url_exclude_patterns": [],
        "ai_extraction_prompt": """Create a lead assessment for this UK local authority based on all available information.

EXTRACT IN JSON FORMAT:
{
  "municipality": "Name of the local authority",
  "region": "Region/County",
  "population": "Population if known",

  "lead_score": {
    "total": 0-100,
    "interest_level": 0-100,
    "urgency": 0-100,
    "accessibility": 0-100,
    "fit": 0-100
  },

  "classification": "Hot Lead|Warm Lead|Cold Lead|Not Qualified",

  "wind_energy_status": {
    "existing_turbines": "Number or unknown",
    "planned_projects": "Yes|No|Unknown",
    "general_stance": "Positive|Neutral|Negative|Mixed"
  },

  "pain_points_summary": [
    {
      "pain_point": "Description",
      "our_solution": "How we can help",
      "priority": "high|medium|low"
    }
  ],

  "positive_signals_summary": ["Identified opportunities"],

  "key_contacts": [
    {
      "name": "Name",
      "role": "Position",
      "stance": "positive|neutral|negative",
      "contact_priority": "high|medium|low"
    }
  ],

  "recommended_approach": {
    "channel": "In-person|Phone|Email|Event",
    "timing": "Immediate|This Week|This Month|Monitor",
    "key_message": "Core message",
    "talking_points": ["Discussion points"],
    "avoid": ["What to avoid"]
  },

  "next_actions": [
    {
      "action": "Recommended action",
      "deadline": "Timeframe",
      "responsible": "Sales|Marketing|Management"
    }
  ],

  "data_sources": ["List of sources used"],
  "confidence": "high|medium|low",
  "last_updated": "YYYY-MM-DD"
}""",
        "schedule_cron": "0 7 * * 1",  # Mondays for weekly update
    },
]


# =============================================================================
# UK DATA SOURCES - Per Category
# =============================================================================

UK_DATA_SOURCES = {
    # -------------------------------------------------------------------------
    # UK Council Information (Website Sitemaps)
    # -------------------------------------------------------------------------
    "uk-council-information": [
        # Example UK councils - can be extended
        {
            "name": "Manchester City Council",
            "source_type": SourceType.WEBSITE,
            "base_url": "https://www.manchester.gov.uk/sitemap.xml",
            "api_endpoint": None,
            "country": "GB",
            "location_name": "Manchester",
            "admin_level_1": "Greater Manchester",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["wind", "energy", "climate", "planning", "renewable"],
            },
            "extra_data": {
                "population": 547627,
                "region": "North West England"
            },
            "priority": 10,
        },
        {
            "name": "Birmingham City Council",
            "source_type": SourceType.WEBSITE,
            "base_url": "https://www.birmingham.gov.uk/sitemap.xml",
            "api_endpoint": None,
            "country": "GB",
            "location_name": "Birmingham",
            "admin_level_1": "West Midlands",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["wind", "energy", "climate", "planning", "renewable"],
            },
            "extra_data": {
                "population": 1141816,
                "region": "West Midlands"
            },
            "priority": 10,
        },
        {
            "name": "Leeds City Council",
            "source_type": SourceType.WEBSITE,
            "base_url": "https://www.leeds.gov.uk/sitemap.xml",
            "api_endpoint": None,
            "country": "GB",
            "location_name": "Leeds",
            "admin_level_1": "West Yorkshire",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["wind", "energy", "climate", "planning", "renewable"],
            },
            "extra_data": {
                "population": 792525,
                "region": "Yorkshire and the Humber"
            },
            "priority": 10,
        },
        {
            "name": "Glasgow City Council",
            "source_type": SourceType.WEBSITE,
            "base_url": "https://www.glasgow.gov.uk/sitemap.xml",
            "api_endpoint": None,
            "country": "GB",
            "location_name": "Glasgow",
            "admin_level_1": "Scotland",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["wind", "energy", "climate", "planning", "renewable"],
            },
            "extra_data": {
                "population": 635640,
                "region": "Scotland"
            },
            "priority": 10,
        },
        {
            "name": "Edinburgh City Council",
            "source_type": SourceType.WEBSITE,
            "base_url": "https://www.edinburgh.gov.uk/sitemap.xml",
            "api_endpoint": None,
            "country": "GB",
            "location_name": "Edinburgh",
            "admin_level_1": "Scotland",
            "crawl_config": {
                "max_pages": 100,
                "filter_keywords": ["wind", "energy", "climate", "planning", "renewable"],
            },
            "extra_data": {
                "population": 524930,
                "region": "Scotland"
            },
            "priority": 10,
        },
    ],

    # -------------------------------------------------------------------------
    # UK Council News (RSS Feeds)
    # -------------------------------------------------------------------------
    "uk-council-news": [
        {
            "name": "UK Government - Energy News",
            "source_type": SourceType.RSS,
            "base_url": "https://www.gov.uk/search/news-and-communications",
            "api_endpoint": "https://www.gov.uk/search/news-and-communications.atom?topics%5B%5D=energy",
            "country": "GB",
            "crawl_config": {
                "filter_keywords": ["wind", "energy", "renewable"],
            },
            "extra_data": {"type": "Government", "scope": "national"},
            "priority": 9,
        },
        {
            "name": "BEIS/DESNZ - Press Releases",
            "source_type": SourceType.RSS,
            "base_url": "https://www.gov.uk/government/organisations/department-for-energy-security-and-net-zero",
            "api_endpoint": "https://www.gov.uk/government/organisations/department-for-energy-security-and-net-zero.atom",
            "country": "GB",
            "crawl_config": {
                "filter_keywords": ["wind", "energy", "renewable", "power"],
            },
            "extra_data": {"type": "Department", "scope": "national"},
            "priority": 10,
        },
    ],

    # -------------------------------------------------------------------------
    # UK Parliamentary Questions
    # -------------------------------------------------------------------------
    "uk-parliamentary-questions": [
        {
            "name": "UK Parliament - Written Questions Energy",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://questions-statements.parliament.uk/",
            "api_endpoint": "https://questions-statements.parliament.uk/api/writtenquestions/questions",
            "country": "GB",
            "crawl_config": {
                "api_type": "uk_parliament",
                "search_query": "wind energy renewable",
                "max_results": 300,
            },
            "extra_data": {"document_type": "Written Question"},
            "priority": 10,
        },
    ],

    # -------------------------------------------------------------------------
    # UK FOI Requests (WhatDoTheyKnow)
    # -------------------------------------------------------------------------
    "uk-foi-requests": [
        {
            "name": "WhatDoTheyKnow - Wind Farm Planning",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://www.whatdotheyknow.com/search/wind%20farm%20planning",
            "api_endpoint": "https://www.whatdotheyknow.com/feed/search/wind%20farm%20planning",
            "country": "GB",
            "crawl_config": {
                "api_type": "whatdotheyknow",
                "search_query": "wind farm planning",
                "max_results": 200,
            },
            "extra_data": {"topic": "Planning"},
            "priority": 10,
        },
        {
            "name": "WhatDoTheyKnow - Wind Energy",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://www.whatdotheyknow.com/search/wind%20energy",
            "api_endpoint": "https://www.whatdotheyknow.com/feed/search/wind%20energy",
            "country": "GB",
            "crawl_config": {
                "api_type": "whatdotheyknow",
                "search_query": "wind energy",
                "max_results": 200,
            },
            "extra_data": {"topic": "Wind Energy"},
            "priority": 8,
        },
    ],

    # -------------------------------------------------------------------------
    # UK Site Data (data.gov.uk)
    # -------------------------------------------------------------------------
    "uk-site-data": [
        {
            "name": "data.gov.uk - Renewable Energy Sites",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://ckan.publishing.service.gov.uk/api/3/action/package_search?q=renewable+energy+wind",
            "api_endpoint": "https://ckan.publishing.service.gov.uk/api/3/action/package_search",
            "country": "GB",
            "crawl_config": {
                "api_type": "ckan",
                "search_query": "renewable energy wind",
                "max_results": 200,
            },
            "extra_data": {"category": "Renewable Sites"},
            "priority": 10,
        },
        {
            "name": "data.gov.uk - Protected Areas",
            "source_type": SourceType.CUSTOM_API,
            "base_url": "https://ckan.publishing.service.gov.uk/api/3/action/package_search?q=protected+area+conservation",
            "api_endpoint": "https://ckan.publishing.service.gov.uk/api/3/action/package_search",
            "country": "GB",
            "crawl_config": {
                "api_type": "ckan",
                "search_query": "protected area conservation SSSI",
                "max_results": 300,
            },
            "extra_data": {"category": "Protected Areas"},
            "priority": 9,
        },
    ],

    # UK Lead Qualification has no direct data sources
    # (aggregated from other categories)
    "uk-lead-qualification": [],
}


async def seed_uk_database():
    """Seed the database with UK-specific example data."""

    async with get_session_context() as session:
        categories_created = 0
        categories_updated = 0
        sources_created = 0

        for cat_data in UK_CATEGORIES:
            # Check if category already exists
            existing = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            existing_cat = existing.scalar()

            if existing_cat:
                # Update existing category
                existing_cat.name = cat_data["name"]
                existing_cat.description = cat_data["description"]
                existing_cat.purpose = cat_data["purpose"]
                existing_cat.search_terms = cat_data["search_terms"]
                existing_cat.languages = cat_data["languages"]
                existing_cat.url_include_patterns = cat_data.get("url_include_patterns", [])
                existing_cat.url_exclude_patterns = cat_data.get("url_exclude_patterns", [])
                existing_cat.ai_extraction_prompt = cat_data["ai_extraction_prompt"]
                existing_cat.schedule_cron = cat_data["schedule_cron"]
                categories_updated += 1
                category = existing_cat
            else:
                # Create new category
                category = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data["description"],
                    purpose=cat_data["purpose"],
                    search_terms=cat_data["search_terms"],
                    languages=cat_data["languages"],
                    url_include_patterns=cat_data.get("url_include_patterns", []),
                    url_exclude_patterns=cat_data.get("url_exclude_patterns", []),
                    ai_extraction_prompt=cat_data["ai_extraction_prompt"],
                    schedule_cron=cat_data["schedule_cron"],
                    is_active=True,
                )
                session.add(category)
                await session.flush()
                categories_created += 1

            # Create data sources for this category
            source_configs = UK_DATA_SOURCES.get(cat_data["slug"], [])
            for src_data in source_configs:
                # Check if source already exists
                existing_src = await session.execute(
                    select(DataSource).where(
                        DataSource.category_id == category.id,
                        DataSource.base_url == src_data["base_url"],
                    )
                )
                if existing_src.scalar():
                    continue

                source = DataSource(
                    category_id=category.id,
                    name=src_data["name"],
                    source_type=src_data["source_type"],
                    base_url=src_data["base_url"],
                    api_endpoint=src_data.get("api_endpoint"),
                    country=src_data.get("country", "GB"),
                    location_name=src_data.get("location_name"),
                    admin_level_1=src_data.get("admin_level_1"),
                    crawl_config=src_data.get("crawl_config", {}),
                    extra_data=src_data.get("extra_data", {}),
                    priority=src_data.get("priority", 0),
                    status=SourceStatus.ACTIVE,
                )
                session.add(source)
                sources_created += 1

        await session.commit()



async def main():
    """Main entry point."""
    await seed_uk_database()


if __name__ == "__main__":
    asyncio.run(main())
