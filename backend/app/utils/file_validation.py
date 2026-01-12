"""
File validation utilities for secure upload handling.

Uses magic bytes to validate actual file content type,
preventing content_type header spoofing attacks.
"""

import contextlib
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO

import structlog
from starlette.datastructures import UploadFile

logger = structlog.get_logger()

# Maximum bytes to read for magic detection
MAX_MAGIC_BYTES = 16


class FileValidationError(Exception):
    """Raised when file validation fails."""

    pass


def detect_mime_type(content: bytes | BinaryIO) -> str | None:
    """
    Detect MIME type from file content using magic bytes.

    Args:
        content: File content as bytes or file-like object

    Returns:
        Detected MIME type or None if unknown
    """
    if isinstance(content, bytes):
        header = content[:MAX_MAGIC_BYTES]
    else:
        pos = content.tell()
        header = content.read(MAX_MAGIC_BYTES)
        content.seek(pos)

    # Check PNG: 89 50 4E 47 0D 0A 1A 0A
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # Check JPEG: FF D8 FF
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # Check GIF: GIF87a or GIF89a
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "image/gif"

    # Check WebP: RIFF....WEBP
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image/webp"

    # Check PDF: %PDF
    if header.startswith(b"%PDF"):
        return "application/pdf"

    return None


def validate_file_type(
    content: bytes | BinaryIO,
    claimed_type: str,
    allowed_types: set[str],
) -> str:
    """
    Validate that file content matches claimed MIME type.

    Args:
        content: File content (bytes or file-like object)
        claimed_type: MIME type from HTTP header
        allowed_types: Set of allowed MIME types

    Returns:
        Validated MIME type (the detected type, not the claimed type)

    Raises:
        FileValidationError: If validation fails
    """
    # Detect actual type from content
    detected_type = detect_mime_type(content)

    if detected_type is None:
        raise FileValidationError(f"Unbekannter Dateityp. Erlaubt: {', '.join(sorted(allowed_types))}")

    if detected_type not in allowed_types:
        raise FileValidationError(
            f"Dateityp nicht erlaubt: {detected_type}. Erlaubt: {', '.join(sorted(allowed_types))}"
        )

    # Warn if claimed type differs (potential spoofing attempt)
    if claimed_type and claimed_type != detected_type:
        logger.warning(
            "MIME type mismatch detected - possible spoofing attempt",
            claimed_type=claimed_type,
            detected_type=detected_type,
        )

    return detected_type


class StreamingUploadHandler:
    """
    Handle large file uploads with streaming to avoid memory issues.

    Files smaller than threshold are kept in memory.
    Larger files are streamed to a temporary file on disk.

    Usage:
        handler = StreamingUploadHandler(threshold_bytes=5*1024*1024)
        try:
            await handler.process_upload(file)
            mime_type = validate_file_type(handler.get_header(), ...)
            content = handler.get_content()
        finally:
            handler.cleanup()
    """

    def __init__(
        self,
        threshold_bytes: int = 5 * 1024 * 1024,  # 5MB default
        temp_dir: str | None = None,
    ):
        """
        Initialize handler.

        Args:
            threshold_bytes: Files larger than this are spooled to disk
            temp_dir: Directory for temp files (None = system default)
        """
        self.threshold_bytes = threshold_bytes
        self.temp_dir = temp_dir
        self._temp_file: tempfile.SpooledTemporaryFile | None = None
        self._size: int = 0

    async def process_upload(self, file: UploadFile) -> "StreamingUploadHandler":
        """
        Process an upload file with streaming.

        For small files: keeps content in memory (SpooledTemporaryFile)
        For large files: streams to temporary file on disk

        Args:
            file: FastAPI/Starlette UploadFile

        Returns:
            Self for chaining
        """
        self._temp_file = tempfile.SpooledTemporaryFile(  # noqa: SIM115
            max_size=self.threshold_bytes,
            dir=self.temp_dir,
            mode="w+b",
        )

        chunk_size = 64 * 1024  # 64KB chunks
        self._size = 0

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            self._temp_file.write(chunk)
            self._size += len(chunk)

        self._temp_file.seek(0)
        return self

    @property
    def size(self) -> int:
        """Get total file size in bytes."""
        return self._size

    @property
    def is_spooled_to_disk(self) -> bool:
        """Check if file was spooled to disk (exceeded threshold)."""
        if self._temp_file is None:
            return False
        # SpooledTemporaryFile has _rolled attribute
        return getattr(self._temp_file, "_rolled", False)

    def get_content(self) -> bytes:
        """
        Get file content as bytes.

        Note: For very large files, consider using save_to() instead
        to avoid loading entire content into memory.
        """
        if self._temp_file is None:
            raise ValueError("No file processed - call process_upload first")

        self._temp_file.seek(0)
        return self._temp_file.read()

    def get_header(self, size: int = MAX_MAGIC_BYTES) -> bytes:
        """
        Get first N bytes for magic detection without reading entire file.

        Args:
            size: Number of bytes to read (default: 16)

        Returns:
            First N bytes of the file
        """
        if self._temp_file is None:
            raise ValueError("No file processed - call process_upload first")

        self._temp_file.seek(0)
        header = self._temp_file.read(size)
        self._temp_file.seek(0)
        return header

    def get_file_object(self) -> BinaryIO:
        """
        Get file-like object for streaming reads.

        Returns:
            File object positioned at start
        """
        if self._temp_file is None:
            raise ValueError("No file processed - call process_upload first")

        self._temp_file.seek(0)
        return self._temp_file

    def save_to(self, path: Path) -> None:
        """
        Save content directly to target path.

        More efficient for large files than get_content() + write.

        Args:
            path: Target file path
        """
        if self._temp_file is None:
            raise ValueError("No file processed - call process_upload first")

        self._temp_file.seek(0)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as target:
            shutil.copyfileobj(self._temp_file, target)

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        if self._temp_file:
            with contextlib.suppress(Exception):
                self._temp_file.close()
            self._temp_file = None

    def __enter__(self) -> "StreamingUploadHandler":
        return self

    def __exit__(self, *args) -> None:
        self.cleanup()

    async def __aenter__(self) -> "StreamingUploadHandler":
        return self

    async def __aexit__(self, *args) -> None:
        self.cleanup()
