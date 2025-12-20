"""SQLAlchemy Models."""

from app.models.category import Category
from app.models.data_source_category import DataSourceCategory
from app.models.data_source import DataSource, SourceStatus, SourceType
from app.models.crawl_job import CrawlJob, JobStatus
from app.models.document import Document, ProcessingStatus
from app.models.extracted_data import ExtractedData
from app.models.change_log import ChangeLog, ChangeType
from app.models.api_export import ApiExport, ExportType
from app.models.pysis import (
    PySisFieldTemplate,
    PySisProcess,
    PySisProcessField,
    SyncStatus,
    ValueSource,
)
from app.models.ai_task import AITask, AITaskStatus, AITaskType
from app.models.location import Location  # Legacy - will be replaced by Entity

# New Entity-Facet System
from app.models.entity_type import EntityType
from app.models.entity import Entity
from app.models.entity_attachment import EntityAttachment, AttachmentAnalysisStatus
from app.models.facet_type import FacetType, ValueType, AggregationMethod, TimeFilter
from app.models.facet_value import FacetValue, FacetValueSourceType
from app.models.relation_type import RelationType, Cardinality
from app.models.entity_relation import EntityRelation
from app.models.analysis_template import AnalysisTemplate

# Authentication & Authorization
from app.models.user import User, UserRole
from app.models.user_email import UserEmailAddress
from app.models.user_session import UserSession, DeviceType, parse_user_agent

# Notifications
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationStatus,
)
from app.models.notification_rule import NotificationRule

# Audit & Versioning
from app.models.audit_log import AuditLog, AuditAction
from app.models.entity_version import EntityVersion
from app.models.mixins import VersionedMixin, TimestampMixin

# Assistant
from app.models.reminder import Reminder, ReminderRepeat, ReminderStatus

# Dashboard
from app.models.user_dashboard import UserDashboardPreference

# Export Jobs
from app.models.export_job import ExportJob

# External API Integration
from external_apis.models.external_api_config import ExternalAPIConfig, AuthType, SyncStatus
from external_apis.models.sync_record import SyncRecord, RecordStatus

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
    "EntityAttachment",
    "AttachmentAnalysisStatus",
    "FacetType",
    "ValueType",
    "AggregationMethod",
    "TimeFilter",
    "FacetValue",
    "FacetValueSourceType",
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
    # External API Integration
    "ExternalAPIConfig",
    "AuthType",
    "SyncStatus",
    "SyncRecord",
    "RecordStatus",
]
