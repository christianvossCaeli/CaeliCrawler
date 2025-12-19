"""Admin API endpoints for data source management."""

import ipaddress
import socket
import uuid as uuid_module
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import DataSource, Document, Category, SourceStatus, SourceType, DataSourceCategory
from app.models.location import Location
from app.schemas.data_source import (
    CategoryLink,
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    DataSourceListResponse,
    DataSourceBulkImport,
    DataSourceBulkImportResult,
)
from app.schemas.common import MessageResponse
from app.core.exceptions import NotFoundError, ConflictError


# =============================================================================
# SSRF Protection for Crawler URLs
# =============================================================================

# IP ranges that should NOT be crawled (internal networks, cloud metadata, etc.)
BLOCKED_CRAWLER_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # Localhost
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local (cloud metadata)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
]

# Hostnames that should never be crawled
BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "metadata.google.com",
}


def validate_crawler_url(url: str, allow_http: bool = True) -> Tuple[bool, str]:
    """
    Validate a URL for safe crawling (SSRF protection).

    Args:
        url: The URL to validate
        allow_http: Whether to allow HTTP (not just HTTPS)

    Returns:
        Tuple of (is_safe, error_message)
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        allowed_schemes = ["https"]
        if allow_http:
            allowed_schemes.append("http")

        if parsed.scheme not in allowed_schemes:
            return False, f"URL scheme must be one of: {', '.join(allowed_schemes)}"

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: no hostname"

        # Check blocked hostnames
        if hostname.lower() in BLOCKED_HOSTNAMES:
            return False, f"Hostname '{hostname}' is not allowed"

        # Check for internal hostnames
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return False, "Internal hostnames are not allowed"

        # Try to resolve and check IP
        try:
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            for blocked_range in BLOCKED_CRAWLER_IP_RANGES:
                if ip_obj in blocked_range:
                    return False, f"URL resolves to blocked IP range (internal network)"
        except socket.gaierror:
            # Can't resolve - allow for now, will fail at crawl time
            pass

        return True, ""

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


async def get_or_create_location(
    session: AsyncSession,
    name: str,
    admin_level_1: Optional[str] = None,
    country: str = "DE",
) -> UUID:
    """Get existing location by name or create a new one."""
    name_normalized = Location.normalize_name(name, country)

    # Try to find existing location in the same country
    result = await session.execute(
        select(Location).where(
            Location.country == country,
            Location.name_normalized == name_normalized,
            Location.is_active == True,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing.id

    # Create new location
    location = Location(
        id=uuid_module.uuid4(),
        name=name,
        name_normalized=name_normalized,
        country=country,
        admin_level_1=admin_level_1,
        is_active=True,
    )
    session.add(location)
    await session.flush()

    return location.id


async def get_categories_for_source(
    session: AsyncSession,
    source_id: UUID,
) -> list[CategoryLink]:
    """Load all categories linked to a data source."""
    result = await session.execute(
        select(DataSourceCategory, Category)
        .join(Category, DataSourceCategory.category_id == Category.id)
        .where(DataSourceCategory.data_source_id == source_id)
        .order_by(DataSourceCategory.is_primary.desc(), Category.name)
    )
    links = []
    for dsc, cat in result.all():
        links.append(CategoryLink(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            is_primary=dsc.is_primary,
        ))
    return links


async def get_categories_for_sources_bulk(
    session: AsyncSession,
    source_ids: List[UUID],
) -> Dict[UUID, List[CategoryLink]]:
    """
    Bulk-load all categories for multiple data sources.

    Returns a dict mapping source_id -> list of CategoryLink.
    This avoids N+1 queries when listing multiple sources.
    """
    if not source_ids:
        return {}

    result = await session.execute(
        select(DataSourceCategory, Category)
        .join(Category, DataSourceCategory.category_id == Category.id)
        .where(DataSourceCategory.data_source_id.in_(source_ids))
        .order_by(DataSourceCategory.is_primary.desc(), Category.name)
    )

    categories_by_source: Dict[UUID, List[CategoryLink]] = defaultdict(list)
    for dsc, cat in result.all():
        categories_by_source[dsc.data_source_id].append(CategoryLink(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            is_primary=dsc.is_primary,
        ))

    return categories_by_source


async def sync_source_categories(
    session: AsyncSession,
    source: DataSource,
    category_ids: list[UUID],
    primary_category_id: UUID | None = None,
) -> None:
    """Sync categories for a data source (replace existing)."""
    # Delete existing links
    await session.execute(
        select(DataSourceCategory).where(
            DataSourceCategory.data_source_id == source.id
        )
    )
    existing = (await session.execute(
        select(DataSourceCategory).where(DataSourceCategory.data_source_id == source.id)
    )).scalars().all()
    for link in existing:
        await session.delete(link)

    # Create new links (N:M via junction table only)
    for i, cat_id in enumerate(category_ids):
        is_primary = cat_id == primary_category_id if primary_category_id else (i == 0)
        link = DataSourceCategory(
            data_source_id=source.id,
            category_id=cat_id,
            is_primary=is_primary,
        )
        session.add(link)

    await session.flush()


def build_source_response(
    source: DataSource,
    categories: list[CategoryLink],
    document_count: int = 0,
    job_count: int = 0,
) -> DataSourceResponse:
    """Build a DataSourceResponse from a DataSource model."""
    category_name = None
    primary_category_id = None
    if categories:
        primary = next((c for c in categories if c.is_primary), categories[0])
        category_name = primary.name
        primary_category_id = primary.id

    return DataSourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        base_url=source.base_url,
        api_endpoint=source.api_endpoint,
        category_id=primary_category_id,  # From junction table, not legacy field
        location_id=getattr(source, 'location_id', None),
        country=source.country,
        location_name=source.location_name,
        region=source.region,
        admin_level_1=source.admin_level_1,
        crawl_config=source.crawl_config,
        extra_data=source.extra_data,
        priority=source.priority,
        status=source.status,
        last_crawl=source.last_crawl,
        last_change_detected=source.last_change_detected,
        error_message=source.error_message,
        created_at=source.created_at,
        updated_at=source.updated_at,
        document_count=document_count,
        job_count=job_count,
        category_name=category_name,
        categories=categories,
    )


router = APIRouter()


@router.get("", response_model=DataSourceListResponse)
async def list_sources(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=10000),
    category_id: Optional[UUID] = Query(default=None, description="Filter by category (N:M)"),
    entity_id: Optional[UUID] = Query(default=None, description="Filter by entity ID"),
    status: Optional[SourceStatus] = Query(default=None),
    source_type: Optional[SourceType] = Query(default=None),
    search: Optional[str] = Query(default=None),
    location_name: Optional[str] = Query(default=None, description="Filter by location name"),
    location_id: Optional[UUID] = Query(default=None, description="Filter by location ID"),
    country: Optional[str] = Query(default=None, description="Filter by country code"),
    session: AsyncSession = Depends(get_session),
):
    """List all data sources with pagination and filters."""
    query = select(DataSource)

    # Filter by category via N:M junction table
    if category_id:
        source_ids_in_cat = (
            select(DataSourceCategory.data_source_id)
            .where(DataSourceCategory.category_id == category_id)
        )
        query = query.where(DataSource.id.in_(source_ids_in_cat))

    # Filter by entity
    if entity_id:
        query = query.where(DataSource.entity_id == entity_id)

    if status:
        query = query.where(DataSource.status == status)
    if source_type:
        query = query.where(DataSource.source_type == source_type)
    if country:
        query = query.where(func.upper(DataSource.country) == country.upper())
    if location_name:
        query = query.where(func.lower(DataSource.location_name) == location_name.lower())
    if location_id:
        query = query.where(DataSource.location_id == location_id)
    if search:
        query = query.where(
            DataSource.name.ilike(f"%{search}%") |
            DataSource.base_url.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Paginate
    query = query.order_by(DataSource.name).offset((page - 1) * per_page).limit(per_page)
    result = await session.execute(query)
    sources = result.scalars().all()

    # Bulk-load document counts and categories to avoid N+1 queries
    source_ids = [s.id for s in sources]

    # Single query for all document counts
    doc_counts_result = await session.execute(
        select(Document.source_id, func.count(Document.id))
        .where(Document.source_id.in_(source_ids))
        .group_by(Document.source_id)
    )
    doc_counts = dict(doc_counts_result.all())

    # Bulk-load all categories
    categories_by_source = await get_categories_for_sources_bulk(session, source_ids)

    # Build responses
    items = []
    for source in sources:
        doc_count = doc_counts.get(source.id, 0)
        categories = categories_by_source.get(source.id, [])

        # Build response using helper to avoid lazy-loading issues
        item = build_source_response(source, categories, document_count=doc_count)
        items.append(item)

    return DataSourceListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )


@router.post("", response_model=DataSourceResponse, status_code=201)
async def create_source(
    data: DataSourceCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new data source.

    **Security**: URL is validated against SSRF attacks (internal networks blocked).
    """
    # SSRF Protection: Validate URL before creating source
    is_safe, error_msg = validate_crawler_url(data.base_url)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL: {error_msg}",
        )

    # Also validate API endpoint if provided
    if data.api_endpoint:
        is_safe, error_msg = validate_crawler_url(data.api_endpoint)
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid API endpoint URL: {error_msg}",
            )

    # Determine category IDs - support both legacy single and new multi-category
    category_ids = data.category_ids or []
    if data.category_id and data.category_id not in category_ids:
        category_ids.insert(0, data.category_id)

    if not category_ids:
        raise NotFoundError("Category", "No category specified")

    # Verify all categories exist
    for cat_id in category_ids:
        category = await session.get(Category, cat_id)
        if not category:
            raise NotFoundError("Category", str(cat_id))

    # Primary category is the first one
    primary_category_id = category_ids[0]

    # Check for duplicate URL (globally now, not per-category)
    existing = await session.execute(
        select(DataSource).where(DataSource.base_url == data.base_url)
    )
    if existing.scalar():
        raise ConflictError(
            "Data source already exists",
            detail=f"A source with URL '{data.base_url}' already exists",
        )

    # Get or default country
    country = data.country or "DE"

    # Auto-link or create location if name is provided
    location_id = data.location_id
    if not location_id and data.location_name:
        location_id = await get_or_create_location(
            session, data.location_name, data.admin_level_1, country
        )

    source = DataSource(
        category_id=primary_category_id,  # Legacy field
        name=data.name,
        source_type=data.source_type,
        base_url=data.base_url,
        api_endpoint=data.api_endpoint,
        country=country,
        location_id=location_id,
        location_name=data.location_name,
        region=data.region,
        admin_level_1=data.admin_level_1,
        crawl_config=data.crawl_config.model_dump() if data.crawl_config else {},
        auth_config=data.auth_config,
        extra_data=data.extra_data,
        priority=data.priority,
    )
    session.add(source)
    await session.flush()  # Get ID

    # Create N:M category links
    await sync_source_categories(session, source, category_ids, primary_category_id)

    await session.commit()
    await session.refresh(source)

    # Load categories for response
    categories = await get_categories_for_source(session, source.id)

    return build_source_response(source, categories)


@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_source(
    source_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single data source by ID."""
    source = await session.get(DataSource, source_id)
    if not source:
        raise NotFoundError("Data Source", str(source_id))

    doc_count = (await session.execute(
        select(func.count()).where(Document.source_id == source.id)
    )).scalar()

    # Load categories via N:M
    categories = await get_categories_for_source(session, source.id)

    return build_source_response(source, categories, document_count=doc_count)


@router.put("/{source_id}", response_model=DataSourceResponse)
async def update_source(
    source_id: UUID,
    data: DataSourceUpdate,
    session: AsyncSession = Depends(get_session),
):
    """
    Update a data source.

    **Security**: URL changes are validated against SSRF attacks.
    """
    source = await session.get(DataSource, source_id)
    if not source:
        raise NotFoundError("Data Source", str(source_id))

    update_data = data.model_dump(exclude_unset=True)

    # SSRF Protection: Validate URLs if being updated
    if "base_url" in update_data:
        is_safe, error_msg = validate_crawler_url(update_data["base_url"])
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid URL: {error_msg}",
            )

    if "api_endpoint" in update_data and update_data["api_endpoint"]:
        is_safe, error_msg = validate_crawler_url(update_data["api_endpoint"])
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid API endpoint URL: {error_msg}",
            )

    # Handle N:M category updates
    category_ids = update_data.pop("category_ids", None)
    primary_category_id = update_data.pop("primary_category_id", None)

    if category_ids is not None:
        # Verify all categories exist
        for cat_id in category_ids:
            category = await session.get(Category, cat_id)
            if not category:
                raise NotFoundError("Category", str(cat_id))

        await sync_source_categories(session, source, category_ids, primary_category_id)

    # Handle crawl_config specially
    if "crawl_config" in update_data and update_data["crawl_config"]:
        update_data["crawl_config"] = update_data["crawl_config"].model_dump()

    # Auto-link location if name is provided but no ID
    if "location_name" in update_data and update_data.get("location_name"):
        if not update_data.get("location_id") and not source.location_id:
            country = update_data.get("country") or source.country or "DE"
            update_data["location_id"] = await get_or_create_location(
                session,
                update_data["location_name"],
                update_data.get("admin_level_1") or source.admin_level_1,
                country,
            )

    for field, value in update_data.items():
        setattr(source, field, value)

    await session.commit()
    await session.refresh(source)

    # Load categories for response
    categories = await get_categories_for_source(session, source.id)

    return build_source_response(source, categories)


@router.delete("/{source_id}", response_model=MessageResponse)
async def delete_source(
    source_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a data source and all related data."""
    source = await session.get(DataSource, source_id)
    if not source:
        raise NotFoundError("Data Source", str(source_id))

    name = source.name
    await session.delete(source)
    await session.commit()

    return MessageResponse(message=f"Data source '{name}' deleted successfully")


@router.post("/bulk-import", response_model=DataSourceBulkImportResult)
async def bulk_import_sources(
    data: DataSourceBulkImport,
    session: AsyncSession = Depends(get_session),
):
    """Bulk import data sources from a list."""
    # Verify category exists
    category = await session.get(Category, data.category_id)
    if not category:
        raise NotFoundError("Category", str(data.category_id))

    imported = 0
    skipped = 0
    errors = []

    for item in data.sources:
        try:
            # Check for duplicate
            if data.skip_duplicates:
                existing = await session.execute(
                    select(DataSource).where(
                        DataSource.category_id == data.category_id,
                        DataSource.base_url == item.base_url,
                    )
                )
                if existing.scalar():
                    skipped += 1
                    continue

            source = DataSource(
                category_id=data.category_id,
                name=item.name,
                source_type=item.source_type,
                base_url=item.base_url,
                extra_data=item.extra_data,
            )
            session.add(source)
            imported += 1

        except Exception as e:
            errors.append({
                "url": item.base_url,
                "error": str(e),
            })

    await session.commit()

    return DataSourceBulkImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors,
    )


@router.get("/meta/countries")
async def get_source_countries(
    session: AsyncSession = Depends(get_session),
):
    """Get list of countries that have data sources."""
    query = (
        select(DataSource.country, func.count(DataSource.id).label("count"))
        .where(DataSource.country.isnot(None))
        .group_by(DataSource.country)
        .order_by(func.count(DataSource.id).desc())
    )
    result = await session.execute(query)

    # Map country codes to names
    country_names = {
        "DE": "Deutschland",
        "GB": "United Kingdom",
        "AT": "Österreich",
        "CH": "Schweiz",
        "FR": "Frankreich",
        "NL": "Niederlande",
        "BE": "Belgien",
        "PL": "Polen",
        "CZ": "Tschechien",
        "DK": "Dänemark",
    }

    countries = []
    for row in result.all():
        if row.country:
            countries.append({
                "code": row.country,
                "name": country_names.get(row.country, row.country),
                "source_count": row.count,
            })

    return countries


@router.get("/meta/locations")
async def get_source_locations(
    country: Optional[str] = Query(None, description="Filter by country code"),
    search: Optional[str] = Query(None, min_length=2, description="Search location name"),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Get list of locations that have data sources (for filtering)."""
    query = (
        select(
            DataSource.location_name,
            DataSource.country,
            func.count(DataSource.id).label("count")
        )
        .where(
            DataSource.location_name.isnot(None),
            DataSource.location_name != "",
        )
        .group_by(DataSource.location_name, DataSource.country)
        .order_by(func.count(DataSource.id).desc())
    )

    if country:
        query = query.where(DataSource.country == country.upper())

    if search:
        query = query.where(DataSource.location_name.ilike(f"%{search}%"))

    query = query.limit(limit)
    result = await session.execute(query)

    locations = []
    for row in result.all():
        locations.append({
            "name": row.location_name,
            "country": row.country,
            "source_count": row.count,
        })

    return locations


@router.post("/{source_id}/reset", response_model=MessageResponse)
async def reset_source(
    source_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Reset a source status (clear errors, set to pending)."""
    source = await session.get(DataSource, source_id)
    if not source:
        raise NotFoundError("Data Source", str(source_id))

    source.status = SourceStatus.PENDING
    source.error_message = None
    await session.commit()

    return MessageResponse(message=f"Source '{source.name}' reset to pending")
