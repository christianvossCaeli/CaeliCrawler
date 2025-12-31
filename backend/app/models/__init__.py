"""SQLAlchemy Models."""

from app.models.ai_task import AITask, AITaskStatus, AITaskType
from app.models.analysis_template import AnalysisTemplate

# API Configuration (unified API integration)
from app.models.api_configuration import (
    APIConfiguration,
    APIType,
    AuthType,
    ImportMode,
    SyncStatus,
)
from app.models.api_export import ApiExport, ExportType

# Audit & Versioning
from app.models.audit_log import AuditAction, AuditLog
from app.models.category import Category
from app.models.category_entity_type import CategoryEntityType
from app.models.change_log import ChangeLog, ChangeType
from app.models.crawl_job import CrawlJob, JobStatus

# Crawl Presets
from app.models.crawl_preset import CrawlPreset, PresetStatus

# Custom Summaries
from app.models.custom_summary import CustomSummary, SummaryStatus, SummaryTriggerType
from app.models.data_source import DataSource, SourceStatus, SourceType
from app.models.data_source_category import DataSourceCategory
from app.models.device_token import DevicePlatform, DeviceToken
from app.models.document import Document, ProcessingStatus
from app.models.entity import Entity
from app.models.entity_attachment import AttachmentAnalysisStatus, EntityAttachment
from app.models.entity_relation import EntityRelation

# New Entity-Facet System
from app.models.entity_type import EntityType
from app.models.entity_version import EntityVersion

# Export Jobs
from app.models.export_job import ExportJob
from app.models.extracted_data import ExtractedData
from app.models.facet_type import AggregationMethod, FacetType, TimeFilter, ValueType
from app.models.facet_value import FacetValue, FacetValueSourceType
from app.models.facet_value_history import FacetValueHistory
from app.models.llm_budget import (
    BudgetType,
    LLMBudgetAlert,
    LLMBudgetConfig,
)

# LLM Usage Tracking
from app.models.llm_usage import (
    LLMProvider,
    LLMTaskType,
    LLMUsageMonthlyAggregate,
    LLMUsageRecord,
)
from app.models.location import Location  # Legacy - will be replaced by Entity
from app.models.mixins import TimestampMixin, VersionedMixin

# Notifications
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationStatus,
)
from app.models.notification_rule import NotificationRule
from app.models.pysis import (
    PySisFieldTemplate,
    PySisProcess,
    PySisProcessField,
    SyncStatus,  # noqa: F811
    ValueSource,
)
from app.models.relation_type import Cardinality, RelationType

# Assistant
from app.models.reminder import Reminder, ReminderRepeat, ReminderStatus

# Smart Query History
from app.models.smart_query_operation import OperationType, SmartQueryOperation
from app.models.summary_execution import ExecutionStatus, SummaryExecution
from app.models.summary_share import SummaryShare
from app.models.summary_widget import SummaryWidget, SummaryWidgetType

# Authentication & Authorization
from app.models.user import User, UserRole

# Dashboard
from app.models.user_dashboard import UserDashboardPreference
from app.models.user_email import UserEmailAddress

# User Favorites
from app.models.user_favorite import UserFavorite
from app.models.user_session import DeviceType, UserSession, parse_user_agent

# Sync Records (for API synchronization tracking)
from external_apis.models.sync_record import RecordStatus, SyncRecord

__all__ = [
    # Core models
    "Category",
    "DataSourceCategory",
    "DataSource",
    "SourceStatus",
    "SourceType",
    "CrawlJob",
    "JobStatus",
    "Document",
    "ProcessingStatus",
    "ExtractedData",
    "ChangeLog",
    "ChangeType",
    "ApiExport",
    "ExportType",
    # PySis models
    "PySisFieldTemplate",
    "PySisProcess",
    "PySisProcessField",
    "SyncStatus",
    "ValueSource",
    # AI Task models
    "AITask",
    "AITaskStatus",
    "AITaskType",
    # Legacy
    "Location",
    # Entity-Facet System
    "EntityType",
    "Entity",
    "CategoryEntityType",
    "EntityAttachment",
    "AttachmentAnalysisStatus",
    "FacetType",
    "ValueType",
    "AggregationMethod",
    "TimeFilter",
    "FacetValue",
    "FacetValueSourceType",
    "FacetValueHistory",
    "RelationType",
    "Cardinality",
    "EntityRelation",
    "AnalysisTemplate",
    # Authentication & Authorization
    "User",
    "UserRole",
    "UserEmailAddress",
    "UserSession",
    "DeviceType",
    "parse_user_agent",
    "DeviceToken",
    "DevicePlatform",
    # Notifications
    "Notification",
    "NotificationChannel",
    "NotificationEventType",
    "NotificationStatus",
    "NotificationRule",
    # Audit & Versioning
    "AuditLog",
    "AuditAction",
    "EntityVersion",
    "VersionedMixin",
    "TimestampMixin",
    # Assistant
    "Reminder",
    "ReminderRepeat",
    "ReminderStatus",
    # Dashboard
    "UserDashboardPreference",
    # Export Jobs
    "ExportJob",
    # User Favorites
    "UserFavorite",
    # Smart Query History
    "SmartQueryOperation",
    "OperationType",
    # API Configuration (unified API integration)
    "APIConfiguration",
    "APIType",
    "AuthType",
    "ImportMode",
    "SyncStatus",
    # Crawl Presets
    "CrawlPreset",
    "PresetStatus",
    # Custom Summaries
    "CustomSummary",
    "SummaryStatus",
    "SummaryTriggerType",
    "SummaryWidget",
    "SummaryWidgetType",
    "SummaryExecution",
    "ExecutionStatus",
    "SummaryShare",
    # Sync Records
    "SyncRecord",
    "RecordStatus",
    # LLM Usage Tracking
    "LLMUsageRecord",
    "LLMUsageMonthlyAggregate",
    "LLMProvider",
    "LLMTaskType",
    "LLMBudgetConfig",
    "LLMBudgetAlert",
    "BudgetType",
]
