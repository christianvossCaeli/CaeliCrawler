"""Location model for international locations (municipalities, cities, towns, etc.)."""

import unicodedata
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import String, Integer, Float, Boolean, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.data_source import DataSource


class Location(Base):
    """
    International location (municipality, city, town, parish, etc.).

    Supports multiple countries with a generic 4-level hierarchy:
    - Country (ISO 3166-1 alpha-2)
    - Admin Level 1 (State/Region/Bundesland/County)
    - Admin Level 2 (District/Landkreis/Province)
    - Locality (the actual place name)
    """

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Country (required)
    country: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
        comment="ISO 3166-1 alpha-2 country code (DE, GB, AT, CH, etc.)",
    )

    # Official identifier (country-specific)
    official_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Country-specific code (AGS for DE, GSS for GB, etc.)",
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    name_normalized: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Lowercase, ASCII-normalized for search",
    )

    # Administrative hierarchy
    admin_level_1: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="State/Region/Bundesland/County",
    )
    admin_level_2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="District/Landkreis/Province",
    )

    # Locality type
    locality_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of locality (municipality, city, town, parish, etc.)",
    )

    # Country-specific metadata (JSONB)
    country_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Country-specific data (e.g., rs for DE, gss_code for GB)",
    )

    # Statistics (optional)
    population: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    area_km2: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Geographic coordinates (optional)
    latitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    longitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    data_sources: Mapped[List["DataSource"]] = relationship(
        "DataSource",
        back_populates="location",
    )

    # Composite unique constraint: official_code must be unique within a country
    __table_args__ = (
        Index(
            "ix_locations_country_official_code",
            "country",
            "official_code",
            unique=True,
            postgresql_where=(official_code.isnot(None)),
        ),
        Index(
            "ix_locations_country_admin_level_1",
            "country",
            "admin_level_1",
        ),
    )

    def __repr__(self) -> str:
        return f"<Location {self.name} ({self.country}, {self.admin_level_1})>"

    @staticmethod
    def normalize_name(name: str, country: str = "DE") -> str:
        """
        Normalize location name for search.

        Country-specific normalization rules:
        - DE: German umlauts (ä→ae, ö→oe, ü→ue, ß→ss)
        - GB: British variations (Saint→St)
        - All: Remove diacritics, lowercase
        """
        result = name.lower()

        # Country-specific replacements
        if country == "DE":
            replacements = {
                "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
            }
            for old, new in replacements.items():
                result = result.replace(old, new)
        elif country == "GB":
            # British name variations
            result = result.replace("saint ", "st ")
            result = result.replace("-upon-", " upon ")
            result = result.replace("-on-", " on ")

        # Remove diacritics for all countries
        result = unicodedata.normalize("NFD", result)
        result = "".join(c for c in result if not unicodedata.combining(c))

        return result
