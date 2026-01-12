"""Tests for file validation utilities."""

import io
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.utils.file_validation import (
    FileValidationError,
    StreamingUploadHandler,
    detect_mime_type,
    validate_file_type,
)

# Test data: actual magic bytes for supported file types
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG_HEADER = b"\xff\xd8\xff\xe0" + b"\x00" * 100
GIF87A_HEADER = b"GIF87a" + b"\x00" * 100
GIF89A_HEADER = b"GIF89a" + b"\x00" * 100
WEBP_HEADER = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
PDF_HEADER = b"%PDF-1.4" + b"\x00" * 100
UNKNOWN_HEADER = b"not a valid file format" + b"\x00" * 100

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf"}


class TestDetectMimeType:
    """Tests for detect_mime_type function."""

    def test_detect_png(self):
        """PNG files should be correctly detected."""
        assert detect_mime_type(PNG_HEADER) == "image/png"

    def test_detect_jpeg(self):
        """JPEG files should be correctly detected."""
        assert detect_mime_type(JPEG_HEADER) == "image/jpeg"

    def test_detect_gif87a(self):
        """GIF87a files should be correctly detected."""
        assert detect_mime_type(GIF87A_HEADER) == "image/gif"

    def test_detect_gif89a(self):
        """GIF89a files should be correctly detected."""
        assert detect_mime_type(GIF89A_HEADER) == "image/gif"

    def test_detect_webp(self):
        """WebP files should be correctly detected."""
        assert detect_mime_type(WEBP_HEADER) == "image/webp"

    def test_detect_pdf(self):
        """PDF files should be correctly detected."""
        assert detect_mime_type(PDF_HEADER) == "application/pdf"

    def test_detect_unknown(self):
        """Unknown file formats should return None."""
        assert detect_mime_type(UNKNOWN_HEADER) is None

    def test_detect_empty(self):
        """Empty content should return None."""
        assert detect_mime_type(b"") is None

    def test_detect_short_header(self):
        """Very short content should return None (not crash)."""
        assert detect_mime_type(b"\x89P") is None

    def test_detect_from_file_object(self):
        """Should work with file-like objects."""
        file_obj = io.BytesIO(PNG_HEADER)
        assert detect_mime_type(file_obj) == "image/png"
        # Position should be restored
        assert file_obj.tell() == 0


class TestValidateFileType:
    """Tests for validate_file_type function."""

    def test_validate_png_correct_claim(self):
        """Valid PNG with correct claimed type should pass."""
        result = validate_file_type(PNG_HEADER, "image/png", ALLOWED_TYPES)
        assert result == "image/png"

    def test_validate_jpeg_correct_claim(self):
        """Valid JPEG with correct claimed type should pass."""
        result = validate_file_type(JPEG_HEADER, "image/jpeg", ALLOWED_TYPES)
        assert result == "image/jpeg"

    def test_validate_pdf_correct_claim(self):
        """Valid PDF with correct claimed type should pass."""
        result = validate_file_type(PDF_HEADER, "application/pdf", ALLOWED_TYPES)
        assert result == "application/pdf"

    def test_validate_spoofed_content_type(self):
        """Spoofed content type should still pass but return actual type."""
        # Claim PDF but send PNG - should detect actual type
        result = validate_file_type(PNG_HEADER, "application/pdf", ALLOWED_TYPES)
        assert result == "image/png"  # Returns actual detected type

    def test_validate_unknown_type_rejected(self):
        """Unknown file types should be rejected."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_type(UNKNOWN_HEADER, "application/octet-stream", ALLOWED_TYPES)
        assert "Unbekannter Dateityp" in str(exc_info.value)

    def test_validate_disallowed_type_rejected(self):
        """Detected types not in allowed set should be rejected."""
        # Only allow PNG, try to upload JPEG
        allowed = {"image/png"}
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_type(JPEG_HEADER, "image/jpeg", allowed)
        assert "nicht erlaubt" in str(exc_info.value)
        assert "image/jpeg" in str(exc_info.value)

    def test_validate_with_none_claimed_type(self):
        """Should handle None claimed type gracefully."""
        result = validate_file_type(PNG_HEADER, None, ALLOWED_TYPES)
        assert result == "image/png"

    def test_validate_with_empty_string_claimed_type(self):
        """Should handle empty string claimed type."""
        result = validate_file_type(PNG_HEADER, "", ALLOWED_TYPES)
        assert result == "image/png"


class TestStreamingUploadHandler:
    """Tests for StreamingUploadHandler class."""

    @pytest.fixture
    def mock_upload_file(self):
        """Create a mock UploadFile for testing."""

        def _create(content: bytes):
            mock = MagicMock()
            buffer = io.BytesIO(content)
            mock.read = AsyncMock(side_effect=lambda size: buffer.read(size))
            return mock

        return _create

    @pytest.mark.asyncio
    async def test_process_small_file(self, mock_upload_file):
        """Small files should stay in memory."""
        content = b"x" * (100 * 1024)  # 100KB
        handler = StreamingUploadHandler(threshold_bytes=1024 * 1024)  # 1MB threshold

        await handler.process_upload(mock_upload_file(content))

        assert handler.size == len(content)
        assert handler.get_content() == content
        assert not handler.is_spooled_to_disk
        handler.cleanup()

    @pytest.mark.asyncio
    async def test_process_large_file(self, mock_upload_file):
        """Large files should be spooled to disk."""
        content = b"x" * (100 * 1024)  # 100KB
        handler = StreamingUploadHandler(threshold_bytes=1024)  # 1KB threshold

        await handler.process_upload(mock_upload_file(content))

        assert handler.size == len(content)
        assert handler.get_content() == content
        assert handler.is_spooled_to_disk
        handler.cleanup()

    @pytest.mark.asyncio
    async def test_get_header(self, mock_upload_file):
        """get_header should return first N bytes without reading entire file."""
        content = PNG_HEADER
        handler = StreamingUploadHandler()

        await handler.process_upload(mock_upload_file(content))

        header = handler.get_header(16)
        assert header == content[:16]
        # Position should be reset - content still accessible
        assert handler.get_content() == content
        handler.cleanup()

    @pytest.mark.asyncio
    async def test_save_to(self, mock_upload_file, tmp_path):
        """save_to should write content to target path."""
        content = b"test content for saving"
        handler = StreamingUploadHandler()

        await handler.process_upload(mock_upload_file(content))

        target = tmp_path / "saved_file.bin"
        handler.save_to(target)

        assert target.exists()
        assert target.read_bytes() == content
        handler.cleanup()

    @pytest.mark.asyncio
    async def test_save_to_creates_parent_dirs(self, mock_upload_file, tmp_path):
        """save_to should create parent directories if needed."""
        content = b"test content"
        handler = StreamingUploadHandler()

        await handler.process_upload(mock_upload_file(content))

        target = tmp_path / "nested" / "path" / "file.bin"
        handler.save_to(target)

        assert target.exists()
        assert target.read_bytes() == content
        handler.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_upload_file):
        """cleanup should close the temporary file."""
        handler = StreamingUploadHandler()
        await handler.process_upload(mock_upload_file(b"test"))

        handler.cleanup()

        assert handler._temp_file is None

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_upload_file):
        """Handler should work as context manager."""
        async with StreamingUploadHandler() as handler:
            await handler.process_upload(mock_upload_file(b"test"))
            assert handler.size == 4

        # After context, should be cleaned up
        assert handler._temp_file is None

    def test_get_content_before_process_raises(self):
        """get_content before process_upload should raise."""
        handler = StreamingUploadHandler()
        with pytest.raises(ValueError, match="No file processed"):
            handler.get_content()

    def test_get_header_before_process_raises(self):
        """get_header before process_upload should raise."""
        handler = StreamingUploadHandler()
        with pytest.raises(ValueError, match="No file processed"):
            handler.get_header()

    def test_save_to_before_process_raises(self, tmp_path):
        """save_to before process_upload should raise."""
        handler = StreamingUploadHandler()
        with pytest.raises(ValueError, match="No file processed"):
            handler.save_to(tmp_path / "test_file")


class TestIntegrationMimeAndStreaming:
    """Integration tests combining MIME validation with streaming handler."""

    @pytest.fixture
    def mock_upload_file(self):
        def _create(content: bytes):
            mock = MagicMock()
            buffer = io.BytesIO(content)
            mock.read = AsyncMock(side_effect=lambda size: buffer.read(size))
            return mock

        return _create

    @pytest.mark.asyncio
    async def test_validate_after_streaming(self, mock_upload_file):
        """Should be able to validate MIME type from streamed content."""
        handler = StreamingUploadHandler()

        await handler.process_upload(mock_upload_file(PNG_HEADER))

        # Validate using header only (efficient)
        mime_type = detect_mime_type(handler.get_header())
        assert mime_type == "image/png"

        # Full validation also works
        validated = validate_file_type(handler.get_content(), "image/png", ALLOWED_TYPES)
        assert validated == "image/png"

        handler.cleanup()

    @pytest.mark.asyncio
    async def test_reject_spoofed_file_after_streaming(self, mock_upload_file):
        """Spoofed files should be rejected even after streaming."""
        handler = StreamingUploadHandler()

        await handler.process_upload(mock_upload_file(UNKNOWN_HEADER))

        with pytest.raises(FileValidationError):
            validate_file_type(
                handler.get_header(16),
                "image/png",  # Claimed type
                ALLOWED_TYPES,
            )

        handler.cleanup()
