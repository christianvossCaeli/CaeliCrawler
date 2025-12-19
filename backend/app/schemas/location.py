"""Location schemas for API validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.countries import is_country_supported


class LocationBase(BaseModel):
    """Base location schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Location name")
    country: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code (DE, GB, AT, etc.)",
    )
    official_code: Optional[str] = Field(
        None,
        max_length=50,
        description="Country-specific official code (AGS for DE, GSS for GB, etc.)",
    )
    admin_level_1: Optional[str] = Field(
        None,
        max_length=100,
        description="State/Region/Bundesland/County",
    )
    admin_level_2: Optional[str] = Field(
        None,
        max_length=255,
        description="District/Landkreis/Province",
    )
    locality_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Type of locality (municipality, city, town, parish, etc.)",
    )
    country_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Country-specific metadata (e.g., rs for DE, gss_code for GB)",
    )
    population: Optional[int] = Field(None, ge=0, description="Population")
    area_km2: Optional[float] = Field(None, ge=0, description="Area in km2")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate and uppercase country code."""
        v = v.upper()
        if not is_country_supported(v):
            raise ValueError(f"Unsupported country code: {v}")
        return v


class LocationCreate(LocationBase):
    """Schema for creating a location."""

    pass


class LocationUpdate(BaseModel):
    """Schema for updating a location (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    official_code: Optional[str] = Field(None, max_length=50)
    admin_level_1: Optional[str] = Field(None, max_length=100)
    admin_level_2: Optional[str] = Field(None, max_length=255)
    locality_type: Optional[str] = Field(None, max_length=50)
    country_metadata: Optional[Dict[str, Any]] = None
    population: Optional[int] = Field(None, ge=0)
    area_km2: Optional[float] = Field(None, ge=0)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_active: Optional[bool] = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate and uppercase country code if provided."""
        if v is None:
            return v
        v = v.upper()
        if not is_country_supported(v):
            raise ValueError(f"Unsupported country code: {v}")
        return v


class LocationResponse(LocationBase):
    """Schema for location response."""

    id: UUID
    name_normalized: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields
    source_count: int = Field(default=0, description="Number of data sources")
    pysis_process_count: int = Field(default=0, description="Number of PySis processes")

    model_config = {"from_attributes": True}


class LocationListResponse(BaseModel):
    """Schema for location list response."""

    items: List[LocationResponse]
    total: int
    page: int
    per_page: int
    pages: int


class LocationSearchResult(BaseModel):
    """Lightweight schema for autocomplete search results."""

    id: UUID
    name: str
    country: str
    admin_level_1: Optional[str] = None
    admin_level_2: Optional[str] = None
    official_code: Optional[str] = None

    model_config = {"from_attributes": True}


class LocationSearchResponse(BaseModel):
    """Schema for search response."""

    items: List[LocationSearchResult]
    total: int


class CountryInfo(BaseModel):
    """Schema for country information."""

    code: str = Field(..., description="ISO 3166-1 alpha-2 code")
    name: str = Field(..., description="English name")
    name_de: str = Field(..., description="German name")
    location_count: int = Field(default=0, description="Number of locations in this country")


class AdminLevelInfo(BaseModel):
    """Schema for admin level information."""

    value: str = Field(..., description="Admin level value")
    count: int = Field(default=0, description="Number of locations with this value")


class AdminLevelsResponse(BaseModel):
    """Schema for admin levels response."""

    country: str
    level: int
    parent: Optional[str] = None
    items: List[AdminLevelInfo]
