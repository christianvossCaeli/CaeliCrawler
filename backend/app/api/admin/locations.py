"""Location management API endpoints (internationalized municipalities)."""

import math
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.countries import get_country_config, get_supported_countries, is_country_supported
from app.database import get_session
from app.core.deps import require_editor, require_admin
from app.models import User
from app.models.location import Location
from app.schemas.location import (
    LocationCreate,
    LocationListResponse,
    LocationResponse,
    LocationSearchResponse,
    LocationSearchResult,
    LocationUpdate,
    CountryInfo,
    AdminLevelInfo,
    AdminLevelsResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter()


@router.get("/countries", response_model=List[CountryInfo])
async def list_countries(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Get list of supported countries with location counts.
    """
    # Get counts per country from database
    count_query = (
        select(Location.country, func.count(Location.id).label("count"))
        .where(Location.is_active.is_(True))
        .group_by(Location.country)
    )
    result = await session.execute(count_query)
    counts = {row.country: row.count for row in result.all()}

    # Build response with all supported countries
    countries = []
    for country_data in get_supported_countries():
        countries.append(CountryInfo(
            code=country_data["code"],
            name=country_data["name"],
            name_de=country_data["name_de"],
            location_count=counts.get(country_data["code"], 0),
        ))

    # Sort by location_count desc, then by name
    countries.sort(key=lambda x: (-x.location_count, x.name))
    return countries


@router.get("/admin-levels", response_model=AdminLevelsResponse)
async def get_admin_levels(
    country: str = Query(..., min_length=2, max_length=2, description="Country code"),
    level: int = Query(1, ge=1, le=2, description="Admin level (1 or 2)"),
    parent: Optional[str] = Query(None, description="Parent admin level value (for level 2)"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Get distinct admin level values for a country.

    - level=1: Returns all admin_level_1 values (e.g., Bundesländer for DE)
    - level=2 with parent: Returns admin_level_2 values within that parent
    """
    country = country.upper()
    if not is_country_supported(country):
        raise HTTPException(status_code=400, detail=f"Unsupported country: {country}")

    if level == 1:
        query = (
            select(Location.admin_level_1, func.count(Location.id).label("count"))
            .where(
                Location.is_active.is_(True),
                Location.country == country,
                Location.admin_level_1.isnot(None),
            )
            .group_by(Location.admin_level_1)
            .order_by(Location.admin_level_1)
        )
    else:  # level == 2
        query = (
            select(Location.admin_level_2, func.count(Location.id).label("count"))
            .where(
                Location.is_active.is_(True),
                Location.country == country,
                Location.admin_level_2.isnot(None),
            )
            .group_by(Location.admin_level_2)
            .order_by(Location.admin_level_2)
        )
        if parent:
            query = query.where(Location.admin_level_1 == parent)

    result = await session.execute(query)
    items = [
        AdminLevelInfo(value=row[0], count=row[1])
        for row in result.all()
    ]

    return AdminLevelsResponse(
        country=country,
        level=level,
        parent=parent,
        items=items,
    )


@router.post("/link-sources", response_model=dict)
async def link_all_sources(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    Legacy endpoint - DataSources are no longer linked to locations directly.

    DataSources are now linked to Categories, and Entities are created
    via AI analysis. The linkage is:
    DataSource -> Category -> AI Analysis -> Entity + FacetValues

    This endpoint is kept for backwards compatibility but returns no-op.
    """
    return {
        "sources_linked": 0,
        "processes_linked": 0,
        "message": "DataSources are no longer linked to locations directly. Use Categories for grouping."
    }


@router.get("/with-sources")
async def list_locations_with_sources(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=1, le=10000),
    country: Optional[str] = Query(None, min_length=2, max_length=2, description="Filter by country"),
    admin_level_1: Optional[str] = Query(None, description="Filter by admin level 1 (e.g., Bundesland)"),
    admin_level_2: Optional[str] = Query(None, description="Filter by admin level 2 (e.g., Landkreis)"),
    search: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    List all locations.

    Note: DataSources are no longer directly linked to Locations.
    Source counts are no longer available via this endpoint.
    Use the Entity system for geographic data.
    """
    from sqlalchemy import func as sql_func, literal

    # Normalize country filter
    if country:
        country = country.upper()

    # Main query - all locations
    main_query = (
        select(
            Location.id,
            Location.name,
            Location.country,
            Location.admin_level_1,
            Location.admin_level_2,
            Location.official_code,
            Location.population,
            literal(0).label("source_count"),  # Legacy - no longer tracked
            literal(0).label("document_count"),  # Legacy - no longer tracked
            literal(0).label("extracted_count"),
            literal(True).label("has_location_record"),
        )
        .where(Location.is_active.is_(True))
    )

    # Apply filters
    if country:
        main_query = main_query.where(Location.country == country)
    if admin_level_1:
        main_query = main_query.where(Location.admin_level_1 == admin_level_1)
    if admin_level_2:
        main_query = main_query.where(Location.admin_level_2 == admin_level_2)
    if search:
        search_normalized = Location.normalize_name(search, country or "DE")
        main_query = main_query.where(
            or_(
                Location.name.ilike(f"%{search}%"),
                Location.name_normalized.ilike(f"%{search_normalized}%"),
            )
        )

    # Get total count first (without pagination)
    count_query = select(sql_func.count(Location.id)).where(Location.is_active.is_(True))
    if country:
        count_query = count_query.where(Location.country == country)
    if admin_level_1:
        count_query = count_query.where(Location.admin_level_1 == admin_level_1)
    if admin_level_2:
        count_query = count_query.where(Location.admin_level_2 == admin_level_2)
    if search:
        search_normalized = Location.normalize_name(search, country or "DE")
        count_query = count_query.where(
            or_(
                Location.name.ilike(f"%{search}%"),
                Location.name_normalized.ilike(f"%{search_normalized}%"),
            )
        )
    total = (await session.execute(count_query)).scalar() or 0

    # Add ordering and pagination
    main_query = (
        main_query
        .order_by(Location.name)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    # Execute main query
    result = await session.execute(main_query)
    rows = result.all()

    # Build results
    items = []
    for row in rows:
        items.append({
            "id": str(row.id),
            "name": row.name,
            "country": row.country,
            "admin_level_1": row.admin_level_1,
            "admin_level_2": row.admin_level_2,
            "official_code": row.official_code,
            "population": row.population,
            "source_count": row.source_count,
            "document_count": row.document_count,
            "extracted_count": row.extracted_count,
            "has_location_record": row.has_location_record,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page if per_page > 0 else 1,
    }


@router.get("/search", response_model=LocationSearchResponse)
async def search_locations(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    country: Optional[str] = Query(None, min_length=2, max_length=2, description="Filter by country"),
    admin_level_1: Optional[str] = Query(None, description="Filter by state/region"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """
    Search locations by name for autocomplete.

    Searches both original name and normalized name.
    """
    # Normalize country filter
    if country:
        country = country.upper()

    # Normalize the search query
    search_normalized = Location.normalize_name(q, country or "DE")

    # Build query
    query = select(Location).where(
        Location.is_active.is_(True),
        or_(
            Location.name.ilike(f"%{q}%"),
            Location.name_normalized.ilike(f"%{search_normalized}%"),
        ),
    )

    # Country filter
    if country:
        query = query.where(Location.country == country)

    # Admin level 1 filter
    if admin_level_1:
        query = query.where(Location.admin_level_1 == admin_level_1)

    # Order by relevance
    query = query.order_by(
        Location.name_normalized.ilike(search_normalized).desc(),
        Location.name_normalized.ilike(f"{search_normalized}%").desc(),
        Location.name,
    ).limit(limit)

    result = await session.execute(query)
    locations = result.scalars().all()

    # Count total
    count_query = select(func.count(Location.id)).where(
        Location.is_active.is_(True),
        or_(
            Location.name.ilike(f"%{q}%"),
            Location.name_normalized.ilike(f"%{search_normalized}%"),
        ),
    )
    if country:
        count_query = count_query.where(Location.country == country)
    if admin_level_1:
        count_query = count_query.where(Location.admin_level_1 == admin_level_1)

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    return LocationSearchResponse(
        items=[LocationSearchResult.model_validate(loc) for loc in locations],
        total=total,
    )


@router.get("", response_model=LocationListResponse)
async def list_locations(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, ge=1, le=200, description="Items per page"),
    country: Optional[str] = Query(None, min_length=2, max_length=2, description="Filter by country"),
    admin_level_1: Optional[str] = Query(None, description="Filter by state/region"),
    search: Optional[str] = Query(None, description="Search by name"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """List all locations with pagination."""
    # Normalize country filter
    if country:
        country = country.upper()

    # Base query
    query = select(Location).where(Location.is_active.is_(True))
    count_query = select(func.count(Location.id)).where(Location.is_active.is_(True))

    # Country filter
    if country:
        query = query.where(Location.country == country)
        count_query = count_query.where(Location.country == country)

    # Admin level 1 filter
    if admin_level_1:
        query = query.where(Location.admin_level_1 == admin_level_1)
        count_query = count_query.where(Location.admin_level_1 == admin_level_1)

    # Search filter
    if search:
        search_normalized = Location.normalize_name(search, country or "DE")
        search_filter = or_(
            Location.name.ilike(f"%{search}%"),
            Location.name_normalized.ilike(f"%{search_normalized}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Pagination
    pages = math.ceil(total / per_page) if total > 0 else 1
    offset = (page - 1) * per_page

    # Get locations
    query = query.order_by(Location.country, Location.name).offset(offset).limit(per_page)
    result = await session.execute(query)
    locations = result.scalars().all()

    # Build response
    # Note: DataSources are no longer linked to Locations directly.
    # source_count is set to 0 for backwards compatibility.
    items = []
    for loc in locations:
        item = LocationResponse.model_validate(loc)
        item.source_count = 0  # Legacy - DataSources no longer linked to Locations
        item.pysis_process_count = 0  # PySisProcess links via Entity
        items.append(item)

    return LocationListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/states", response_model=List[str])
async def list_states(
    country: str = Query(default="DE", min_length=2, max_length=2),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get list of all admin_level_1 values (states/regions) for a country."""
    country = country.upper()
    query = (
        select(Location.admin_level_1)
        .where(
            Location.is_active.is_(True),
            Location.country == country,
            Location.admin_level_1.isnot(None),
        )
        .distinct()
        .order_by(Location.admin_level_1)
    )
    result = await session.execute(query)
    return [row[0] for row in result.all()]


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Get a specific location by ID."""
    result = await session.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Note: DataSources are no longer linked to Locations directly.
    response = LocationResponse.model_validate(location)
    response.source_count = 0  # Legacy - DataSources no longer linked to Locations
    response.pysis_process_count = 0  # PySisProcess links via Entity
    return response


@router.post("", response_model=LocationResponse, status_code=201)
async def create_location(
    data: LocationCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Create a new location."""
    # Validate country
    if not is_country_supported(data.country):
        raise HTTPException(status_code=400, detail=f"Unsupported country: {data.country}")

    # Validate official_code format if provided
    if data.official_code:
        config = get_country_config(data.country)
        if not config.validate_official_code(data.official_code):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {config.official_code_name} format for {data.country}",
            )

        # Check for duplicate
        existing = await session.execute(
            select(Location).where(
                Location.country == data.country,
                Location.official_code == data.official_code,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Location with {config.official_code_name} {data.official_code} already exists in {data.country}",
            )

    # Check for duplicate name within country
    name_normalized = Location.normalize_name(data.name, data.country)
    existing_name = await session.execute(
        select(Location).where(
            Location.country == data.country,
            Location.name_normalized == name_normalized,
        )
    )
    if existing_name.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Location '{data.name}' already exists in {data.country}",
        )

    location = Location(
        name=data.name,
        name_normalized=name_normalized,
        country=data.country.upper(),
        official_code=data.official_code,
        admin_level_1=data.admin_level_1,
        admin_level_2=data.admin_level_2,
        locality_type=data.locality_type,
        country_metadata=data.country_metadata or {},
        population=data.population,
        area_km2=data.area_km2,
        latitude=data.latitude,
        longitude=data.longitude,
        is_active=True,
    )
    session.add(location)
    await session.flush()
    await session.refresh(location)

    # Note: DataSources are no longer linked to Locations directly.
    # The relationship is now: DataSource -> Category -> AI Analysis -> Entity + FacetValues
    response = LocationResponse.model_validate(location)
    response.source_count = 0
    response.pysis_process_count = 0
    return response


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID,
    data: LocationUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Update a location."""
    result = await session.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    update_data = data.model_dump(exclude_unset=True)

    # If name or country is updated, update normalized name
    if "name" in update_data or "country" in update_data:
        new_name = update_data.get("name", location.name)
        new_country = update_data.get("country", location.country)
        update_data["name_normalized"] = Location.normalize_name(new_name, new_country)

    for field, value in update_data.items():
        setattr(location, field, value)

    await session.flush()
    await session.refresh(location)

    # Note: DataSources are no longer linked to Locations directly.
    response = LocationResponse.model_validate(location)
    response.source_count = 0
    response.pysis_process_count = 0
    return response


@router.delete("/{location_id}", response_model=MessageResponse)
async def delete_location(
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Delete a location (soft delete)."""
    result = await session.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Note: DataSources are no longer linked to Locations directly.
    # Locations can be freely deleted (soft delete).
    name = location.name
    location.is_active = False
    await session.commit()

    return MessageResponse(message=f"Location '{name}' deleted successfully")


@router.post("/enrich-admin-levels", response_model=dict)
async def enrich_admin_levels(
    country: str = Query(default="DE", min_length=2, max_length=2),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    """
    Enrich locations without admin_level_2 using Nominatim API.

    Rate limited to 1 request/second per Nominatim policy.
    """
    import asyncio
    import httpx

    country = country.upper()
    if not is_country_supported(country):
        raise HTTPException(status_code=400, detail=f"Unsupported country: {country}")

    config = get_country_config(country)

    # Get locations without admin_level_2
    query = (
        select(Location)
        .where(
            Location.is_active.is_(True),
            Location.country == country,
            Location.admin_level_2.is_(None),
        )
        .limit(limit)
    )
    result = await session.execute(query)
    locations = result.scalars().all()

    if not locations:
        return {"enriched": 0, "message": "No locations need enrichment"}

    enriched = 0
    errors = []

    async with httpx.AsyncClient() as client:
        for loc in locations:
            try:
                await asyncio.sleep(1.1)  # Rate limit

                search_parts = [loc.name]
                if loc.admin_level_1:
                    search_parts.append(loc.admin_level_1)
                search_parts.append(config.name)

                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": ", ".join(search_parts),
                        "format": "json",
                        "addressdetails": 1,
                        "limit": 1,
                        "countrycodes": config.nominatim_country_code,
                    },
                    headers={"User-Agent": "CaeliCrawler/1.0"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data:
                        address = data[0].get("address", {})
                        admin_level_2 = (
                            address.get("county") or
                            address.get("city_district") or
                            address.get("state_district") or
                            address.get("district")
                        )
                        if admin_level_2:
                            loc.admin_level_2 = admin_level_2
                            enriched += 1
            except Exception as e:
                errors.append(f"{loc.name}: {str(e)}")

    await session.flush()

    return {
        "enriched": enriched,
        "total_processed": len(locations),
        "errors": errors[:10] if errors else [],
        "message": f"Enriched {enriched} of {len(locations)} locations",
    }
