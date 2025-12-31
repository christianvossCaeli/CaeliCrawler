"""SQLAlchemy models for external API integration."""

from external_apis.models.sync_record import RecordStatus, SyncRecord

__all__ = [
    "SyncRecord",
    "RecordStatus",
]
