"""Service for managing entity attachments."""

import hashlib
import uuid
from io import BytesIO
from pathlib import Path
from uuid import UUID

import structlog
from PIL import Image
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.entity import Entity
from app.models.entity_attachment import AttachmentAnalysisStatus, EntityAttachment

logger = structlog.get_logger()

# Thumbnail settings
THUMBNAIL_SIZE = (200, 200)
THUMBNAIL_QUALITY = 85


class AttachmentService:
    """Service for uploading, storing, and managing entity attachments."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage_path = Path(settings.attachment_storage_path)
        self.max_size = settings.attachment_max_size_mb * 1024 * 1024
        self.allowed_types = set(settings.attachment_allowed_types.split(","))

    async def upload_attachment(
        self,
        entity_id: UUID,
        filename: str,
        content: bytes,
        content_type: str,
        user_id: UUID | None = None,
        description: str | None = None,
    ) -> EntityAttachment:
        """
        Upload and store a new attachment for an entity.

        Args:
            entity_id: Target entity UUID
            filename: Original filename
            content: File bytes
            content_type: MIME type
            user_id: Uploading user (optional)
            description: Optional description

        Returns:
            Created EntityAttachment

        Raises:
            ValueError: If file type not allowed or size exceeded
        """
        # Validate content type
        if content_type not in self.allowed_types:
            raise ValueError(f"Nicht erlaubter Dateityp: {content_type}")

        # Validate file size
        if len(content) > self.max_size:
            raise ValueError(
                f"Datei zu gross. Maximum: {settings.attachment_max_size_mb}MB"
            )

        # Check entity exists
        entity = await self.db.get(Entity, entity_id)
        if not entity:
            raise ValueError(f"Entity nicht gefunden: {entity_id}")

        # Calculate hash for deduplication
        file_hash = hashlib.sha256(content).hexdigest()

        # Check for duplicate
        existing = await self.db.execute(
            select(EntityAttachment).where(
                and_(
                    EntityAttachment.entity_id == entity_id,
                    EntityAttachment.file_hash == file_hash,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Diese Datei ist bereits an dieser Entity angehaengt")

        # Generate storage path: attachments/{entity_id}/{uuid}.{ext}
        attachment_id = uuid.uuid4()
        ext = self._get_extension(filename, content_type)
        relative_path = f"{entity_id}/{attachment_id}.{ext}"
        full_path = self.storage_path / relative_path

        # Create directory
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        full_path.write_bytes(content)

        # Generate thumbnail for images
        if content_type.startswith("image/"):
            self._create_thumbnail(full_path, content)

        # Create database record
        attachment = EntityAttachment(
            id=attachment_id,
            entity_id=entity_id,
            filename=filename,
            content_type=content_type,
            file_size=len(content),
            file_path=relative_path,
            file_hash=file_hash,
            uploaded_by_id=user_id,
            description=description,
            analysis_status=AttachmentAnalysisStatus.PENDING,
        )

        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)

        logger.info(
            "Attachment uploaded",
            attachment_id=str(attachment_id),
            entity_id=str(entity_id),
            filename=filename,
            size=len(content),
        )

        return attachment

    async def get_attachments(
        self,
        entity_id: UUID,
    ) -> list[EntityAttachment]:
        """Get all attachments for an entity."""
        query = (
            select(EntityAttachment)
            .where(EntityAttachment.entity_id == entity_id)
            .order_by(EntityAttachment.created_at.desc())
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_attachment(self, attachment_id: UUID) -> EntityAttachment | None:
        """Get a single attachment by ID."""
        return await self.db.get(EntityAttachment, attachment_id)

    async def delete_attachment(self, attachment_id: UUID) -> bool:
        """Delete an attachment and its files."""
        attachment = await self.db.get(EntityAttachment, attachment_id)
        if not attachment:
            return False

        # Delete files
        full_path = self.storage_path / attachment.file_path
        if full_path.exists():
            full_path.unlink()

        # Delete thumbnail if exists
        if attachment.is_image:
            thumb_path = self._get_thumbnail_path(full_path)
            if thumb_path.exists():
                thumb_path.unlink()

        # Delete database record
        await self.db.delete(attachment)
        await self.db.commit()

        logger.info("Attachment deleted", attachment_id=str(attachment_id))
        return True

    async def get_file_content(self, attachment: EntityAttachment) -> bytes:
        """Read attachment file content."""
        full_path = self.storage_path / attachment.file_path
        if not full_path.exists():
            raise FileNotFoundError(
                f"Attachment file not found: {attachment.file_path}"
            )
        return full_path.read_bytes()

    def get_file_path(self, attachment: EntityAttachment) -> Path:
        """Get full file path for an attachment."""
        return self.storage_path / attachment.file_path

    def get_thumbnail_path_for_attachment(
        self, attachment: EntityAttachment
    ) -> Path | None:
        """Get thumbnail path for an attachment if it's an image."""
        if not attachment.is_image:
            return None

        full_path = self.storage_path / attachment.file_path
        thumb_path = self._get_thumbnail_path(full_path)

        if thumb_path.exists():
            return thumb_path

        # Fall back to original if no thumbnail
        return full_path if full_path.exists() else None

    async def update_description(
        self, attachment_id: UUID, description: str
    ) -> EntityAttachment | None:
        """Update attachment description."""
        attachment = await self.db.get(EntityAttachment, attachment_id)
        if not attachment:
            return None

        attachment.description = description
        await self.db.commit()
        await self.db.refresh(attachment)
        return attachment

    def _create_thumbnail(self, file_path: Path, content: bytes) -> None:
        """Create thumbnail for image attachments."""
        try:
            img = Image.open(BytesIO(content))
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            thumb_path = self._get_thumbnail_path(file_path)
            img.save(thumb_path, quality=THUMBNAIL_QUALITY, optimize=True)

            logger.debug("Thumbnail created", path=str(thumb_path))
        except Exception as e:
            logger.warning("Failed to create thumbnail", error=str(e))

    def _get_thumbnail_path(self, file_path: Path) -> Path:
        """Get thumbnail path from original file path."""
        return file_path.parent / f"{file_path.stem}_thumb{file_path.suffix}"

    def _get_extension(self, filename: str, content_type: str) -> str:
        """Get file extension from filename or content type."""
        if "." in filename:
            return filename.rsplit(".", 1)[-1].lower()

        type_map = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/gif": "gif",
            "image/webp": "webp",
            "application/pdf": "pdf",
        }
        return type_map.get(content_type, "bin")
