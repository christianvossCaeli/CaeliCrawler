"""Pydantic Schemas for API request/response validation."""

from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
)
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    DataSourceListResponse,
    DataSourceBulkImport,
)
from app.schemas.crawl_job import (
    CrawlJobCreate,
    CrawlJobResponse,
    CrawlJobListResponse,
    CrawlJobStats,
)
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentSearchParams,
)
from app.schemas.extracted_data import (
    ExtractedDataResponse,
    ExtractedDataUpdate,
    ExtractedDataVerify,
)
from app.schemas.common import (
    PaginationParams,
    PaginatedResponse,
    MessageResponse,
    ErrorResponse,
)
from app.schemas.location import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    LocationListResponse,
    LocationSearchResult,
    LocationSearchResponse,
    CountryInfo,
    AdminLevelInfo,
    AdminLevelsResponse,
)

# New Entity-Facet System
from app.schemas.entity_type import (
    EntityTypeCreate,
    EntityTypeUpdate,
    EntityTypeResponse,
    EntityTypeListResponse,
)
from app.schemas.entity import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    EntityListResponse,
    EntityBrief,
    EntityHierarchy,
)
from app.schemas.facet_type import (
    FacetTypeCreate,
    FacetTypeUpdate,
    FacetTypeResponse,
    FacetTypeListResponse,
)
from app.schemas.facet_value import (
    FacetValueCreate,
    FacetValueUpdate,
    FacetValueResponse,
    FacetValueListResponse,
    FacetValueAggregated,
    EntityFacetsSummary,
)
from app.schemas.relation import (
    RelationTypeCreate,
    RelationTypeUpdate,
    RelationTypeResponse,
    RelationTypeListResponse,
    EntityRelationCreate,
    EntityRelationUpdate,
    EntityRelationResponse,
    EntityRelationListResponse,
    EntityRelationsGraph,
)
from app.schemas.analysis_template import (
    AnalysisTemplateCreate,
    AnalysisTemplateUpdate,
    AnalysisTemplateResponse,
    AnalysisTemplateListResponse,
    FacetConfig,
    AggregationConfig,
    DisplayConfig,
)

__all__ = [
    # Category
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "CategoryListResponse",
    # DataSource
    "DataSourceCreate",
    "DataSourceUpdate",
    "DataSourceResponse",
    "DataSourceListResponse",
    "DataSourceBulkImport",
    # CrawlJob
    "CrawlJobCreate",
    "CrawlJobResponse",
    "CrawlJobListResponse",
    "CrawlJobStats",
    # Document
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentSearchParams",
    # ExtractedData
    "ExtractedDataResponse",
    "ExtractedDataUpdate",
    "ExtractedDataVerify",
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    # Location (legacy)
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    "LocationListResponse",
    "LocationSearchResult",
    "LocationSearchResponse",
    "CountryInfo",
    "AdminLevelInfo",
    "AdminLevelsResponse",
    # Entity-Facet System - EntityType
    "EntityTypeCreate",
    "EntityTypeUpdate",
    "EntityTypeResponse",
    "EntityTypeListResponse",
    # Entity-Facet System - Entity
    "EntityCreate",
    "EntityUpdate",
    "EntityResponse",
    "EntityListResponse",
    "EntityBrief",
    "EntityHierarchy",
    # Entity-Facet System - FacetType
    "FacetTypeCreate",
    "FacetTypeUpdate",
    "FacetTypeResponse",
    "FacetTypeListResponse",
    # Entity-Facet System - FacetValue
    "FacetValueCreate",
    "FacetValueUpdate",
    "FacetValueResponse",
    "FacetValueListResponse",
    "FacetValueAggregated",
    "EntityFacetsSummary",
    # Entity-Facet System - Relations
    "RelationTypeCreate",
    "RelationTypeUpdate",
    "RelationTypeResponse",
    "RelationTypeListResponse",
    "EntityRelationCreate",
    "EntityRelationUpdate",
    "EntityRelationResponse",
    "EntityRelationListResponse",
    "EntityRelationsGraph",
    # Entity-Facet System - AnalysisTemplate
    "AnalysisTemplateCreate",
    "AnalysisTemplateUpdate",
    "AnalysisTemplateResponse",
    "AnalysisTemplateListResponse",
    "FacetConfig",
    "AggregationConfig",
    "DisplayConfig",
]
