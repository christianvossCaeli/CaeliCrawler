"""Admin API endpoints for SharePoint Online integration."""


from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.core.deps import require_editor
from app.core.exceptions import ValidationError
from app.models import User
from external_apis.clients.sharepoint_client import (
    SharePointClient,
    SharePointConfigError,
    SharePointError,
    parse_sharepoint_site_url,
)

router = APIRouter()


# === Response Models ===

class SharePointConnectionStatus(BaseModel):
    """SharePoint connection status response."""

    connected: bool = Field(description="Whether connection to SharePoint is successful")
    configured: bool = Field(description="Whether SharePoint credentials are configured")
    tenant_id: str | None = Field(default=None, description="Partial tenant ID (for verification)")
    error: str | None = Field(default=None, description="Error message if connection failed")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "connected": True,
                    "configured": True,
                    "tenant_id": "a1b2c3d4...",
                    "error": None
                },
                {
                    "connected": False,
                    "configured": False,
                    "tenant_id": None,
                    "error": "SharePoint credentials not configured. Set SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, and SHAREPOINT_CLIENT_SECRET."
                }
            ]
        }
    }


class SharePointSiteResponse(BaseModel):
    """SharePoint site response."""

    id: str = Field(description="Unique site ID", example="contoso.sharepoint.com,abc123,def456")
    name: str = Field(description="Site name", example="Documents")
    display_name: str = Field(description="Display name", example="Team Documents")
    web_url: str = Field(description="Web URL", example="https://contoso.sharepoint.com/sites/Documents")


class SharePointSitesResponse(BaseModel):
    """List of SharePoint sites response."""

    items: list[SharePointSiteResponse] = Field(description="List of sites")
    total: int = Field(description="Total number of sites", example=5)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [
                        {
                            "id": "contoso.sharepoint.com,abc123,def456",
                            "name": "Documents",
                            "display_name": "Team Documents",
                            "web_url": "https://contoso.sharepoint.com/sites/Documents"
                        }
                    ],
                    "total": 1
                }
            ]
        }
    }


class SharePointDriveResponse(BaseModel):
    """SharePoint drive (document library) response."""

    id: str = Field(description="Unique drive ID", example="b!abc123")
    name: str = Field(description="Drive name", example="Shared Documents")
    drive_type: str = Field(description="Drive type", example="documentLibrary")
    web_url: str = Field(description="Web URL", example="https://contoso.sharepoint.com/sites/Documents/Shared%20Documents")


class SharePointDrivesResponse(BaseModel):
    """List of SharePoint drives response."""

    items: list[SharePointDriveResponse] = Field(description="List of drives")
    total: int = Field(description="Total number of drives", example=2)
    site_id: str = Field(description="Parent site ID")


class SharePointFileResponse(BaseModel):
    """SharePoint file response."""

    id: str = Field(description="Unique file ID", example="01ABC123")
    name: str = Field(description="File name", example="report.pdf")
    size: int = Field(description="File size in bytes", example=1048576)
    mime_type: str = Field(description="MIME type", example="application/pdf")
    web_url: str = Field(description="Web URL for viewing", example="https://contoso.sharepoint.com/sites/Documents/report.pdf")
    parent_path: str = Field(description="Parent folder path", example="/Windprojekte/2024")
    created_at: str | None = Field(default=None, description="Creation timestamp", example="2024-01-15T10:30:00+00:00")
    modified_at: str | None = Field(default=None, description="Last modification timestamp", example="2024-03-20T14:45:00+00:00")
    created_by: str | None = Field(default=None, description="Creator display name", example="Max Mustermann")
    modified_by: str | None = Field(default=None, description="Last modifier display name", example="Erika Musterfrau")


class SharePointFilesResponse(BaseModel):
    """List of SharePoint files response."""

    items: list[SharePointFileResponse] = Field(description="List of files")
    total: int = Field(description="Total number of files returned", example=25)
    site_id: str = Field(description="Site ID")
    drive_id: str = Field(description="Drive ID")
    folder_path: str = Field(description="Folder path that was queried", example="/Windprojekte")


class SharePointConfigExample(BaseModel):
    """Example configuration for SharePoint data source."""

    site_url: str = Field(
        example="contoso.sharepoint.com:/sites/Documents",
        description="SharePoint site URL"
    )
    drive_name: str | None = Field(
        default=None,
        example="Shared Documents",
        description="Document library name"
    )
    folder_path: str | None = Field(
        default="",
        example="/Windprojekte",
        description="Folder path within the library"
    )
    file_extensions: list[str] = Field(
        default=[".pdf", ".docx", ".doc", ".xlsx", ".pptx"],
        description="File extensions to include"
    )
    recursive: bool = Field(
        default=True,
        description="Include files from subfolders"
    )
    exclude_patterns: list[str] = Field(
        default=["~$*", "*.tmp", ".DS_Store"],
        description="File patterns to exclude (glob patterns)"
    )
    max_files: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum files to crawl"
    )
    file_paths_text: str | None = Field(
        default=None,
        example="/Documents/Report.pdf\n/Projects/Analysis.docx",
        description="Explicit file paths to crawl (one per line). If set, these files are fetched in addition to folder crawling."
    )


class SharePointDriveInfo(BaseModel):
    """Drive information in test connection response."""

    id: str
    name: str
    type: str


class SharePointTestConnectionResponse(BaseModel):
    """Response for SharePoint connection test."""

    authentication: bool = Field(description="OAuth2 authentication successful")
    sites_accessible: bool = Field(description="Can list sites")
    sites_found: int = Field(default=0, description="Number of sites found")
    target_site: str | None = Field(default=None, description="Target site URL if specified")
    target_site_accessible: bool = Field(default=False, description="Can access target site")
    target_site_name: str | None = Field(default=None, description="Display name of target site")
    drives: list[SharePointDriveInfo] = Field(default_factory=list, description="Document libraries found")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")


# === Endpoints ===

@router.get("/status", response_model=SharePointConnectionStatus)
async def get_sharepoint_status(
    _: User = Depends(require_editor),
):
    """Get SharePoint connection status and configuration."""
    is_configured = bool(
        settings.sharepoint_tenant_id
        and settings.sharepoint_client_id
        and settings.sharepoint_client_secret
    )

    if not is_configured:
        return SharePointConnectionStatus(
            connected=False,
            configured=False,
            error="SharePoint credentials not configured. Set SHAREPOINT_TENANT_ID, SHAREPOINT_CLIENT_ID, and SHAREPOINT_CLIENT_SECRET.",
        )

    # Test connection
    try:
        async with SharePointClient() as client:
            connected = await client.test_connection()
            return SharePointConnectionStatus(
                connected=connected,
                configured=True,
                tenant_id=settings.sharepoint_tenant_id[:8] + "...",  # Partial for security
            )
    except Exception as e:
        return SharePointConnectionStatus(
            connected=False,
            configured=True,
            tenant_id=settings.sharepoint_tenant_id[:8] + "...",
            error=str(e),
        )


@router.get("/sites", response_model=SharePointSitesResponse)
async def list_sharepoint_sites(
    query: str = Query(default="*", description="Search query for sites"),
    _: User = Depends(require_editor),
):
    """List available SharePoint sites.

    Requires SharePoint credentials to be configured.
    Use query parameter to search for specific sites, or "*" to list all.
    """
    if not settings.sharepoint_tenant_id:
        raise ValidationError("SharePoint credentials not configured")

    try:
        async with SharePointClient() as client:
            sites = await client.search_sites(query)

            return SharePointSitesResponse(
                items=[
                    SharePointSiteResponse(
                        id=s.id,
                        name=s.name,
                        display_name=s.display_name,
                        web_url=s.web_url,
                    )
                    for s in sites
                ],
                total=len(sites),
            )
    except Exception as e:
        raise ValidationError(f"Failed to list SharePoint sites: {e}") from None


@router.get("/sites/{site_id}/drives", response_model=SharePointDrivesResponse)
async def list_sharepoint_drives(
    site_id: str,
    _: User = Depends(require_editor),
):
    """List document libraries (drives) in a SharePoint site.

    Args:
        site_id: SharePoint site ID (from /sites endpoint)
    """
    if not settings.sharepoint_tenant_id:
        raise ValidationError("SharePoint credentials not configured")

    try:
        async with SharePointClient() as client:
            drives = await client.list_drives(site_id)

            return SharePointDrivesResponse(
                items=[
                    SharePointDriveResponse(
                        id=d.id,
                        name=d.name,
                        drive_type=d.drive_type,
                        web_url=d.web_url,
                    )
                    for d in drives
                ],
                total=len(drives),
                site_id=site_id,
            )
    except Exception as e:
        raise ValidationError(f"Failed to list SharePoint drives: {e}") from None


@router.get("/sites/{site_id}/drives/{drive_id}/files", response_model=SharePointFilesResponse)
async def list_sharepoint_files(
    site_id: str,
    drive_id: str,
    folder_path: str = Query(default="", description="Folder path within the drive"),
    recursive: bool = Query(default=False, description="Include files from subfolders"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum files to return"),
    _: User = Depends(require_editor),
):
    """List files in a SharePoint document library.

    Args:
        site_id: SharePoint site ID
        drive_id: Drive (document library) ID
        folder_path: Optional folder path within the drive
        recursive: Whether to include files from subfolders
        limit: Maximum number of files to return
    """
    if not settings.sharepoint_tenant_id:
        raise ValidationError("SharePoint credentials not configured")

    try:
        async with SharePointClient() as client:
            files = await client.list_files(
                site_id=site_id,
                drive_id=drive_id,
                folder_path=folder_path,
                recursive=recursive,
            )

            # Apply limit
            files = files[:limit]

            return SharePointFilesResponse(
                items=[
                    SharePointFileResponse(
                        id=f.id,
                        name=f.name,
                        size=f.size,
                        mime_type=f.mime_type,
                        web_url=f.web_url,
                        parent_path=f.parent_path,
                        created_at=f.created_at.isoformat() if f.created_at else None,
                        modified_at=f.modified_at.isoformat() if f.modified_at else None,
                        created_by=f.created_by,
                        modified_by=f.modified_by,
                    )
                    for f in files
                ],
                total=len(files),
                site_id=site_id,
                drive_id=drive_id,
                folder_path=folder_path,
            )
    except Exception as e:
        raise ValidationError(f"Failed to list SharePoint files: {e}") from None


@router.get("/config-example", response_model=SharePointConfigExample)
async def get_config_example(
    _: User = Depends(require_editor),
):
    """Get an example configuration for a SharePoint data source.

    This shows the available options for crawl_config when creating
    a data source with source_type=SHAREPOINT.
    """
    return SharePointConfigExample()


@router.post("/test-connection", response_model=SharePointTestConnectionResponse)
async def test_sharepoint_connection(
    site_url: str | None = Query(
        default=None,
        description="Optional site URL to test (e.g., 'contoso.sharepoint.com:/sites/Documents')"
    ),
    _: User = Depends(require_editor),
):
    """Test SharePoint connection with optional site URL.

    Tests the OAuth2 authentication and optionally connects to a specific site.

    Returns detailed information about:
    - Authentication status
    - Site accessibility
    - Available document libraries (drives)
    """
    if not settings.sharepoint_tenant_id:
        raise ValidationError("SharePoint credentials not configured")

    result = SharePointTestConnectionResponse(
        authentication=False,
        sites_accessible=False,
        sites_found=0,
        target_site=site_url,
    )

    try:
        async with SharePointClient() as client:
            # Test authentication by listing sites (also validates token)
            sites = await client.search_sites("*")
            result.authentication = True
            result.sites_accessible = True
            result.sites_found = len(sites)

            # Test specific site if provided
            if site_url:
                try:
                    hostname, site_path = parse_sharepoint_site_url(site_url)

                    site = await client.get_site_by_url(hostname, site_path)
                    result.target_site_accessible = True
                    result.target_site_name = site.display_name

                    # List drives
                    drives = await client.list_drives(site.id)
                    result.drives = [
                        SharePointDriveInfo(id=d.id, name=d.name, type=d.drive_type)
                        for d in drives
                    ]
                except SharePointConfigError as e:
                    result.errors.append(f"Invalid site URL: {e.message}")
                except SharePointError as e:
                    result.errors.append(f"Site access error: {e.message}")
                except Exception as e:
                    result.errors.append(f"Site access error: {e}")

    except SharePointError as e:
        result.errors.append(e.message)
    except Exception as e:
        result.errors.append(str(e))

    return result
