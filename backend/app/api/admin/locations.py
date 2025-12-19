"""Location management API endpoints (internationalized municipalities)."""

import math
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.countries import get_country_config, get_supported_countries, is_country_supported
from app.database import get_session
from app.models.location import Location
from app.models.data_source import DataSource
from app.models.pysis import PySisProcess
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

router = APIRouter()


@router.get("/countries", response_model=List[CountryInfo])
async def list_countries(
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of supported countries with location counts.
    """
    # Get counts per country from database
    count_query = (
        select(Location.country, func.count(Location.id).label("count"))
        .where(Location.is_active == True)
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
                Location.is_active == True,
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
                Location.is_active == True,
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
):
    """
    Link all unlinked DataSources and PySis processes to their locations.

    Matches by location name (case-insensitive).
    """
    # Get all locations
    locations_result = await session.execute(
        select(Location).where(Location.is_active == True)
    )
    locations = {
        loc.name.lower(): loc.id
        for loc in locations_result.scalars().all()
    }

    # Link DataSources
    unlinked_sources = await session.execute(
        select(DataSource).where(
            DataSource.location_id.is_(None),
            DataSource.location_name.is_not(None)
        )
    )
    sources_linked = 0
    for source in unlinked_sources.scalars().all():
        if source.location_name and source.location_name.lower() in locations:
            source.location_id = locations[source.location_name.lower()]
            sources_linked += 1

    # Note: PySisProcess links via entity_id, not location_id
    # PySis process linking would require entity-based matching
    processes_linked = 0

    await session.flush()

    return {
        "sources_linked": sources_linked,
        "processes_linked": processes_linked,
        "message": f"Linked {sources_linked} sources"
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
):
    """
    List all locations that have data sources assigned.

    Optimized version using aggregated queries to avoid N+1 problems.
    """
    from sqlalchemy import func as sql_func, literal, case
    from sqlalchemy.orm import aliased
    from app.models.document import Document

    # Normalize country filter
    if country:
        country = country.upper()

    # Build optimized query with aggregations using subqueries
    # Subquery for source count per location
    source_count_subq = (
        select(
            DataSource.location_id,
            sql_func.count(DataSource.id).label("source_count")
        )
        .where(DataSource.location_id.isnot(None))
        .group_by(DataSource.location_id)
    ).subquery()

    # Subquery for document count per location
    doc_count_subq = (
        select(
            DataSource.location_id,
            sql_func.count(Document.id).label("document_count")
        )
        .join(Document, Document.source_id == DataSource.id)
        .where(DataSource.location_id.isnot(None))
        .group_by(DataSource.location_id)
    ).subquery()

    # Main query - locations with sources using LEFT JOINs for counts
    main_query = (
        select(
            Location.id,
            Location.name,
            Location.country,
            Location.admin_level_1,
            Location.admin_level_2,
            Location.official_code,
            Location.population,
            sql_func.coalesce(source_count_subq.c.source_count, 0).label("source_count"),
            sql_func.coalesce(doc_count_subq.c.document_count, 0).label("document_count"),
            literal(0).label("extracted_count"),  # Skip extracted_count for performance
            literal(True).label("has_location_record"),
        )
        .join(source_count_subq, Location.id == source_count_subq.c.location_id)
        .outerjoin(doc_count_subq, Location.id == doc_count_subq.c.location_id)
        .where(Location.is_active == True)
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
    count_subq = main_query.subquery()
    total_query = select(sql_func.count()).select_from(count_subq)
    total = (await session.execute(total_query)).scalar() or 0

    # Add ordering and pagination
    main_query = (
        main_query
        .order_by(sql_func.coalesce(source_count_subq.c.source_count, 0).desc(), Location.name)
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

    # Also check for legacy locations (unlinked) - only if we have room on the page
    # This is a simpler query since we're just getting aggregates
    legacy_total = 0
    if total < per_page or page == 1:
        # Count legacy locations
        legacy_count_q = (
            select(sql_func.count(sql_func.distinct(DataSource.location_name)))
            .where(
                DataSource.location_name.isnot(None),
                DataSource.location_name != "",
                DataSource.location_id.is_(None),
            )
        )
        if country:
            legacy_count_q = legacy_count_q.where(DataSource.country == country)
        if admin_level_1:
            legacy_count_q = legacy_count_q.where(DataSource.admin_level_1 == admin_level_1)
        if search:
            legacy_count_q = legacy_count_q.where(
                DataSource.location_name.ilike(f"%{search}%")
            )
        legacy_total = (await session.execute(legacy_count_q)).scalar() or 0

    # If we need legacy items to fill the page
    if len(items) < per_page and legacy_total > 0:
        # Get seen names to exclude
        seen_names = {item["name"].lower() for item in items}

        legacy_query = (
            select(
                DataSource.location_name,
                DataSource.country,
                sql_func.count(DataSource.id).label("source_count"),
            )
            .where(
                DataSource.location_name.isnot(None),
                DataSource.location_name != "",
                DataSource.location_id.is_(None),
            )
            .group_by(DataSource.location_name, DataSource.country)
            .order_by(sql_func.count(DataSource.id).desc())
            .limit(per_page - len(items) + 100)  # Get extra to filter seen names
        )
        if country:
            legacy_query = legacy_query.where(DataSource.country == country)
        if admin_level_1:
            legacy_query = legacy_query.where(DataSource.admin_level_1 == admin_level_1)
        if search:
            legacy_query = legacy_query.where(
                DataSource.location_name.ilike(f"%{search}%")
            )

        legacy_result = await session.execute(legacy_query)
        legacy_rows = legacy_result.all()

        for row in legacy_rows:
            if len(items) >= per_page:
                break
            if row.location_name.lower() in seen_names:
                continue

            items.append({
                "id": None,
                "name": row.location_name,
                "country": row.country or "DE",
                "admin_level_1": None,
                "admin_level_2": None,
                "official_code": None,
                "population": None,
                "source_count": row.source_count,
                "document_count": 0,  # Skip for performance
                "extracted_count": 0,
                "has_location_record": False,
            })
            seen_names.add(row.location_name.lower())

    # Combine totals (subtract duplicates approximately)
    combined_total = total + legacy_total

    return {
        "items": items,
        "total": combined_total,
        "page": page,
        "per_page": per_page,
        "pages": (combined_total + per_page - 1) // per_page if per_page > 0 else 1,
    }


@router.get("/search", response_model=LocationSearchResponse)
async def search_locations(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    country: Optional[str] = Query(None, min_length=2, max_length=2, description="Filter by country"),
    admin_level_1: Optional[str] = Query(None, description="Filter by state/region"),
    session: AsyncSession = Depends(get_session),
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
        Location.is_active == True,
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
        Location.is_active == True,
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
):
    """List all locations with pagination."""
    # Normalize country filter
    if country:
        country = country.upper()

    # Base query
    query = select(Location).where(Location.is_active == True)
    count_query = select(func.count(Location.id)).where(Location.is_active == True)

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

    # Build response with counts
    items = []
    for loc in locations:
        source_count_q = select(func.count(DataSource.id)).where(
            DataSource.location_id == loc.id
        )
        source_count = (await session.execute(source_count_q)).scalar() or 0

        # PySisProcess links via entity_id, not location_id
        # For now, set to 0 - would need Entity join for accurate count
        pysis_count = 0

        item = LocationResponse.model_validate(loc)
        item.source_count = source_count
        item.pysis_process_count = pysis_count
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
):
    """Get list of all admin_level_1 values (states/regions) for a country."""
    country = country.upper()
    query = (
        select(Location.admin_level_1)
        .where(
            Location.is_active == True,
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
):
    """Get a specific location by ID."""
    result = await session.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Get counts
    source_count = (await session.execute(
        select(func.count(DataSource.id)).where(DataSource.location_id == location.id)
    )).scalar() or 0

    # PySisProcess links via entity_id, not location_id
    pysis_count = 0

    response = LocationResponse.model_validate(location)
    response.source_count = source_count
    response.pysis_process_count = pysis_count
    return response


@router.post("", response_model=LocationResponse, status_code=201)
async def create_location(
    data: LocationCreate,
    session: AsyncSession = Depends(get_session),
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

    # Auto-link existing DataSources
    from sqlalchemy import func as sql_func
    sources_to_link = await session.execute(
        select(DataSource).where(
            DataSource.location_id.is_(None),
            sql_func.lower(DataSource.location_name) == data.name.lower(),
        )
    )
    linked_sources = 0
    for source in sources_to_link.scalars().all():
        source.location_id = location.id
        if not source.country:
            source.country = data.country
        linked_sources += 1

    # Note: PySisProcess links via entity_id, not location_id
    linked_processes = 0

    await session.flush()

    response = LocationResponse.model_validate(location)
    response.source_count = linked_sources
    response.pysis_process_count = linked_processes
    return response


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID,
    data: LocationUpdate,
    session: AsyncSession = Depends(get_session),
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

    # Get counts
    source_count = (await session.execute(
        select(func.count(DataSource.id)).where(DataSource.location_id == location.id)
    )).scalar() or 0

    # PySisProcess links via entity_id, not location_id
    pysis_count = 0

    response = LocationResponse.model_validate(location)
    response.source_count = source_count
    response.pysis_process_count = pysis_count
    return response


@router.delete("/{location_id}", status_code=204)
async def delete_location(
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a location (soft delete)."""
    result = await session.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    # Check for linked sources
    source_count = (await session.execute(
        select(func.count(DataSource.id)).where(DataSource.location_id == location.id)
    )).scalar() or 0

    if source_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete location with {source_count} linked data sources",
        )

    location.is_active = False
    await session.flush()


@router.post("/enrich-admin-levels", response_model=dict)
async def enrich_admin_levels(
    country: str = Query(default="DE", min_length=2, max_length=2),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
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
            Location.is_active == True,
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
