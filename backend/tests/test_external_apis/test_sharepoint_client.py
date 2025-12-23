"""Tests for SharePoint client functionality."""

from datetime import datetime, timezone

import pytest

from external_apis.clients.sharepoint_client import (
    SharePointError,
    SharePointAuthError,
    SharePointConfigError,
    SharePointNotFoundError,
    SharePointPermissionError,
    SharePointRateLimitError,
    SharePointFile,
    SharePointSite,
    SharePointDrive,
    SharePointTokenCache,
    parse_sharepoint_site_url,
)


class TestParseSharePointSiteUrl:
    """Tests for parse_sharepoint_site_url function."""

    def test_parse_graph_api_format(self):
        """Test parsing Graph API format with :/ separator."""
        hostname, path = parse_sharepoint_site_url("contoso.sharepoint.com:/sites/Documents")
        assert hostname == "contoso.sharepoint.com"
        assert path == "/sites/Documents"

    def test_parse_standard_url_format(self):
        """Test parsing standard SharePoint URL format."""
        hostname, path = parse_sharepoint_site_url("contoso.sharepoint.com/sites/Documents")
        assert hostname == "contoso.sharepoint.com"
        assert path == "/sites/Documents"

    def test_parse_https_url(self):
        """Test parsing URL with https:// prefix."""
        hostname, path = parse_sharepoint_site_url("https://contoso.sharepoint.com/sites/Documents")
        assert hostname == "contoso.sharepoint.com"
        assert path == "/sites/Documents"

    def test_parse_http_url(self):
        """Test parsing URL with http:// prefix (should work but not recommended)."""
        hostname, path = parse_sharepoint_site_url("http://contoso.sharepoint.com/sites/Documents")
        assert hostname == "contoso.sharepoint.com"
        assert path == "/sites/Documents"

    def test_parse_nested_site_path(self):
        """Test parsing URL with nested site path."""
        hostname, path = parse_sharepoint_site_url("contoso.sharepoint.com:/sites/Projects/Wind")
        assert hostname == "contoso.sharepoint.com"
        assert path == "/sites/Projects/Wind"

    def test_parse_empty_url_raises_error(self):
        """Test that empty URL raises SharePointConfigError."""
        with pytest.raises(SharePointConfigError) as exc_info:
            parse_sharepoint_site_url("")
        assert "empty" in str(exc_info.value).lower()

    def test_parse_none_url_raises_error(self):
        """Test that None URL raises SharePointConfigError."""
        with pytest.raises(SharePointConfigError):
            parse_sharepoint_site_url(None)

    def test_parse_invalid_format_raises_error(self):
        """Test that invalid URL format raises SharePointConfigError."""
        with pytest.raises(SharePointConfigError) as exc_info:
            parse_sharepoint_site_url("invalid-url-format")
        assert "Invalid SharePoint site URL format" in str(exc_info.value)

    def test_parse_non_sharepoint_url_raises_error(self):
        """Test that non-SharePoint URL raises SharePointConfigError."""
        with pytest.raises(SharePointConfigError):
            parse_sharepoint_site_url("https://example.com/path")


class TestSharePointExceptions:
    """Tests for SharePoint exception hierarchy."""

    def test_sharepoint_error_base(self):
        """Test base SharePointError."""
        error = SharePointError("Test error", details={"code": "TestCode"})
        assert error.message == "Test error"
        assert error.details == {"code": "TestCode"}
        assert str(error) == "Test error"

    def test_sharepoint_error_default_details(self):
        """Test SharePointError with default empty details."""
        error = SharePointError("Test error")
        assert error.details == {}

    def test_sharepoint_auth_error_inheritance(self):
        """Test SharePointAuthError inherits from SharePointError."""
        error = SharePointAuthError("Auth failed")
        assert isinstance(error, SharePointError)
        assert error.message == "Auth failed"

    def test_sharepoint_config_error_inheritance(self):
        """Test SharePointConfigError inherits from SharePointError."""
        error = SharePointConfigError("Config missing")
        assert isinstance(error, SharePointError)

    def test_sharepoint_not_found_error_inheritance(self):
        """Test SharePointNotFoundError inherits from SharePointError."""
        error = SharePointNotFoundError("Resource not found")
        assert isinstance(error, SharePointError)

    def test_sharepoint_permission_error_inheritance(self):
        """Test SharePointPermissionError inherits from SharePointError."""
        error = SharePointPermissionError("Access denied")
        assert isinstance(error, SharePointError)

    def test_sharepoint_rate_limit_error(self):
        """Test SharePointRateLimitError with retry_after."""
        error = SharePointRateLimitError("Rate limit exceeded", retry_after=60)
        assert isinstance(error, SharePointError)
        assert error.retry_after == 60
        assert error.message == "Rate limit exceeded"

    def test_sharepoint_rate_limit_error_default_retry(self):
        """Test SharePointRateLimitError without retry_after."""
        error = SharePointRateLimitError("Rate limit exceeded")
        assert error.retry_after is None


class TestSharePointDataclasses:
    """Tests for SharePoint dataclasses."""

    def test_sharepoint_token_cache(self):
        """Test SharePointTokenCache dataclass."""
        expires = datetime.now(timezone.utc)
        cache = SharePointTokenCache(
            access_token="test_token",
            expires_at=expires,
        )
        assert cache.access_token == "test_token"
        assert cache.expires_at == expires

    def test_sharepoint_site(self):
        """Test SharePointSite dataclass."""
        site = SharePointSite(
            id="site-123",
            name="TestSite",
            display_name="Test Site",
            web_url="https://contoso.sharepoint.com/sites/TestSite",
        )
        assert site.id == "site-123"
        assert site.name == "TestSite"
        assert site.display_name == "Test Site"
        assert site.web_url == "https://contoso.sharepoint.com/sites/TestSite"

    def test_sharepoint_drive(self):
        """Test SharePointDrive dataclass."""
        drive = SharePointDrive(
            id="drive-123",
            name="Shared Documents",
            drive_type="documentLibrary",
            web_url="https://contoso.sharepoint.com/sites/TestSite/Shared%20Documents",
            site_id="site-123",
        )
        assert drive.id == "drive-123"
        assert drive.name == "Shared Documents"
        assert drive.drive_type == "documentLibrary"
        assert drive.site_id == "site-123"

    def test_sharepoint_file(self):
        """Test SharePointFile dataclass."""
        created = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        modified = datetime(2024, 3, 20, 14, 45, 0, tzinfo=timezone.utc)

        file = SharePointFile(
            id="file-123",
            name="report.pdf",
            size=1048576,
            mime_type="application/pdf",
            web_url="https://contoso.sharepoint.com/sites/TestSite/report.pdf",
            download_url="https://contoso.sharepoint.com/download/report.pdf",
            created_at=created,
            modified_at=modified,
            created_by="Max Mustermann",
            modified_by="Erika Musterfrau",
            parent_path="/Documents",
            site_id="site-123",
            drive_id="drive-456",
        )
        assert file.id == "file-123"
        assert file.name == "report.pdf"
        assert file.size == 1048576
        assert file.mime_type == "application/pdf"
        assert file.created_at == created
        assert file.modified_at == modified
        assert file.created_by == "Max Mustermann"
        assert file.modified_by == "Erika Musterfrau"
        assert file.parent_path == "/Documents"

    def test_sharepoint_file_optional_fields(self):
        """Test SharePointFile with optional fields as None."""
        file = SharePointFile(
            id="file-123",
            name="report.pdf",
            size=0,
            mime_type="application/octet-stream",
            web_url="",
            download_url=None,
            created_at=None,
            modified_at=None,
            created_by=None,
            modified_by=None,
            parent_path="",
            site_id="site-123",
            drive_id="drive-456",
        )
        assert file.download_url is None
        assert file.created_at is None
        assert file.modified_at is None
        assert file.created_by is None
        assert file.modified_by is None
