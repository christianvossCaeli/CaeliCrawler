"""
FragDenStaat API Client.

FragDenStaat is the German Freedom of Information (FOI) portal.
It enables citizens to request public documents from authorities.

API Documentation: https://fragdenstaat.de/api/
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from crawlers.api_clients.base_api import APIDocument, APIResponse, BaseAPIClient


class FOIRequestStatus(str, Enum):
    """Status of a FOI request."""

    AWAITING_RESPONSE = "awaiting_response"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    AWAITING_USER_CONFIRMATION = "awaiting_user_confirmation"
    ASLEEP = "asleep"
    RESOLVED = "resolved"
    SUCCESSFUL = "successful"
    PARTIALLY_SUCCESSFUL = "partially_successful"
    NOT_HELD = "not_held"
    REFUSED = "refused"
    USER_WITHDREW = "user_withdrew"
    USER_WITHDREW_COSTS = "user_withdrew_costs"


@dataclass
class FOIRequest:
    """Freedom of Information request."""

    id: int
    url: str
    title: str
    slug: str
    status: str
    resolution: str | None = None
    description: str | None = None

    # Public body
    public_body_id: int | None = None
    public_body_name: str | None = None
    public_body_jurisdiction: str | None = None

    # Requestor
    user_id: int | None = None
    user_name: str | None = None

    # Dates
    created_at: datetime | None = None
    last_message: datetime | None = None
    due_date: datetime | None = None
    resolved_on: datetime | None = None

    # Costs
    costs: float = 0.0

    # Law used
    law_id: int | None = None
    law_name: str | None = None

    # Messages and documents
    messages_count: int = 0
    attachments_count: int = 0

    # Classification
    campaign: str | None = None
    tags: list[str] = field(default_factory=list)

    # Links
    same_as: list[int] = field(default_factory=list)


@dataclass
class PublicBody:
    """Government body/authority."""

    id: int
    url: str
    name: str
    slug: str

    # Organization details
    classification: str | None = None
    email: str | None = None
    contact: str | None = None
    address: str | None = None
    website: str | None = None

    # Jurisdiction
    jurisdiction_id: int | None = None
    jurisdiction_name: str | None = None
    jurisdiction_level: str | None = None  # bund, land, kommune

    # Categories
    categories: list[dict[str, Any]] = field(default_factory=list)

    # Statistics
    request_count: int = 0
    request_count_year: int = 0
    request_success_rate: float = 0.0

    # FOI law
    default_law_id: int | None = None
    laws: list[dict[str, Any]] = field(default_factory=list)

    # Geographic
    geo: dict[str, Any] | None = None
    region: str | None = None

    created_at: datetime | None = None


@dataclass
class FOIMessage:
    """A message within a FOI request."""

    id: int
    request_id: int
    sender: str  # "user" or "public_body"
    subject: str
    content: str
    timestamp: datetime

    # Attachments
    attachments: list[dict[str, Any]] = field(default_factory=list)

    # Redactions
    is_redacted: bool = False


@dataclass
class FOIAttachment:
    """Document attachment."""

    id: int
    name: str
    url: str
    file_url: str
    size: int
    filetype: str

    approved: bool = True
    is_redacted: bool = False
    can_approve: bool = False

    created_at: datetime | None = None


class FragDenStaatClient(BaseAPIClient):
    """
    Client for the FragDenStaat API.

    Example usage:
        async with FragDenStaatClient() as client:
            # Search FOI requests
            results = await client.search_requests("Windkraft")

            # Get requests to specific authority
            requests = await client.get_requests_by_public_body(public_body_id=123)

            # Search public bodies
            bodies = await client.search_public_bodies("Bundesministerium")

            # Get requests by status
            successful = await client.search_requests(
                status=FOIRequestStatus.SUCCESSFUL
            )
    """

    BASE_URL = "https://fragdenstaat.de/api/v1"
    API_NAME = "FragDenStaat"
    DEFAULT_DELAY = 0.5

    # === FOI Requests ===

    async def search_requests(
        self,
        query: str | None = None,
        status: FOIRequestStatus | None = None,
        public_body: int | None = None,
        jurisdiction: str | None = None,
        campaign: str | None = None,
        tags: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> APIResponse[APIDocument]:
        """
        Search for FOI requests.

        Args:
            query: Full-text search query
            status: Filter by request status
            public_body: Filter by public body ID
            jurisdiction: Filter by jurisdiction slug
            campaign: Filter by campaign
            tags: Filter by tags
            created_after: Only requests created after this date
            created_before: Only requests created before this date
            limit: Results per page
            offset: Pagination offset
        """
        params = {
            "limit": min(limit, 200),
            "offset": offset,
        }

        if query:
            params["q"] = query
        if status:
            params["status"] = status.value if isinstance(status, FOIRequestStatus) else status
        if public_body:
            params["public_body"] = public_body
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if campaign:
            params["campaign"] = campaign
        if tags:
            params["tags"] = ",".join(tags)
        if created_after:
            params["created_at_after"] = created_after.isoformat()
        if created_before:
            params["created_at_before"] = created_before.isoformat()

        data = await self.get("request/", params)

        if not data:
            return APIResponse(data=[], total_count=0)

        requests = [self._parse_request(r) for r in data.get("objects", [])]
        documents = [self._request_to_document(r) for r in requests]

        meta = data.get("meta", {})

        return APIResponse(
            data=documents,
            total_count=meta.get("total_count", len(documents)),
            page=(offset // limit) + 1,
            per_page=limit,
            has_more=meta.get("next") is not None,
            next_url=meta.get("next"),
            raw_response=data,
        )

    async def get_request(self, request_id: int) -> FOIRequest | None:
        """Get a specific FOI request by ID."""
        data = await self.get(f"request/{request_id}/")
        if data:
            return self._parse_request(data)
        return None

    async def get_request_messages(self, request_id: int) -> list[FOIMessage]:
        """Get all messages for a FOI request."""
        data = await self.get(f"request/{request_id}/")
        if not data:
            return []

        messages = []
        for msg in data.get("messages", []):
            messages.append(self._parse_message(msg, request_id))
        return messages

    async def iterate_requests(
        self,
        query: str | None = None,
        status: FOIRequestStatus | None = None,
        batch_size: int = 100,
        max_requests: int = 10000,
        **kwargs,
    ) -> AsyncIterator[FOIRequest]:
        """Iterate through all FOI requests matching criteria."""
        offset = 0
        total = 0

        while total < max_requests:
            response = await self.search_requests(
                query=query,
                status=status,
                limit=batch_size,
                offset=offset,
                **kwargs,
            )

            if not response.raw_response:
                break

            for req_data in response.raw_response.get("objects", []):
                yield self._parse_request(req_data)
                total += 1
                if total >= max_requests:
                    return

            if not response.has_more:
                break

            offset += batch_size

    # === Public Bodies ===

    async def search_public_bodies(
        self,
        query: str | None = None,
        jurisdiction: str | None = None,
        classification: str | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PublicBody]:
        """
        Search for public bodies (authorities).

        Args:
            query: Search query
            jurisdiction: Filter by jurisdiction slug (e.g., "bund", "nordrhein-westfalen")
            classification: Filter by classification
            categories: Filter by category slugs
            limit: Results per page
            offset: Pagination offset
        """
        params = {
            "limit": min(limit, 200),
            "offset": offset,
        }

        if query:
            params["q"] = query
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if classification:
            params["classification"] = classification
        if categories:
            params["categories"] = ",".join(categories)

        data = await self.get("publicbody/", params)

        if not data:
            return []

        return [self._parse_public_body(pb) for pb in data.get("objects", [])]

    async def get_public_body(self, public_body_id: int) -> PublicBody | None:
        """Get a specific public body by ID."""
        data = await self.get(f"publicbody/{public_body_id}/")
        if data:
            return self._parse_public_body(data)
        return None

    async def iterate_public_bodies(
        self,
        jurisdiction: str | None = None,
        batch_size: int = 100,
        max_bodies: int = 50000,
    ) -> AsyncIterator[PublicBody]:
        """Iterate through all public bodies."""
        offset = 0
        total = 0

        while total < max_bodies:
            bodies = await self.search_public_bodies(
                jurisdiction=jurisdiction,
                limit=batch_size,
                offset=offset,
            )

            if not bodies:
                break

            for body in bodies:
                yield body
                total += 1
                if total >= max_bodies:
                    return

            if len(bodies) < batch_size:
                break

            offset += batch_size

    # === Jurisdictions ===

    async def get_jurisdictions(self) -> list[dict[str, Any]]:
        """Get all available jurisdictions."""
        data = await self.get("jurisdiction/")
        if data:
            return data.get("objects", [])
        return []

    # === Campaigns ===

    async def get_campaigns(self) -> list[dict[str, Any]]:
        """Get all campaigns."""
        data = await self.get("campaign/")
        if data:
            return data.get("objects", [])
        return []

    # === Laws ===

    async def get_laws(self, jurisdiction: str | None = None) -> list[dict[str, Any]]:
        """Get FOI laws."""
        params = {}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction

        data = await self.get("law/", params)
        if data:
            return data.get("objects", [])
        return []

    # === Generic Search Interface ===

    async def search(
        self,
        query: str,
        **kwargs,
    ) -> APIResponse[APIDocument]:
        """Generic search interface."""
        return await self.search_requests(query=query, **kwargs)

    async def get_document(self, document_id: str) -> APIDocument | None:
        """Get document by ID."""
        request = await self.get_request(int(document_id))
        if request:
            return self._request_to_document(request)
        return None

    # === Parsers ===

    def _parse_request(self, data: dict[str, Any]) -> FOIRequest:
        """Parse FOI request from API response."""
        public_body = data.get("public_body") or {}

        return FOIRequest(
            id=data.get("id", 0),
            url=data.get("url", ""),
            title=data.get("title", ""),
            slug=data.get("slug", ""),
            status=data.get("status", ""),
            resolution=data.get("resolution"),
            description=data.get("description"),
            public_body_id=public_body.get("id"),
            public_body_name=public_body.get("name"),
            public_body_jurisdiction=public_body.get("jurisdiction", {}).get("name")
            if isinstance(public_body.get("jurisdiction"), dict)
            else public_body.get("jurisdiction"),
            user_id=data.get("user", {}).get("id") if isinstance(data.get("user"), dict) else None,
            user_name=data.get("user", {}).get("username") if isinstance(data.get("user"), dict) else None,
            created_at=self.parse_datetime(data.get("created_at")),
            last_message=self.parse_datetime(data.get("last_message")),
            due_date=self.parse_datetime(data.get("due_date")),
            resolved_on=self.parse_datetime(data.get("resolved_on")),
            costs=float(data.get("costs", 0) or 0),
            law_id=data.get("law", {}).get("id") if isinstance(data.get("law"), dict) else None,
            law_name=data.get("law", {}).get("name") if isinstance(data.get("law"), dict) else None,
            messages_count=data.get("messages_count", 0),
            attachments_count=data.get("attachments_count", 0),
            campaign=data.get("campaign"),
            tags=[t.get("name", t) if isinstance(t, dict) else t for t in data.get("tags", [])],
            same_as=data.get("same_as", []),
        )

    def _parse_public_body(self, data: dict[str, Any]) -> PublicBody:
        """Parse public body from API response."""
        jurisdiction = data.get("jurisdiction") or {}

        return PublicBody(
            id=data.get("id", 0),
            url=data.get("url", ""),
            name=data.get("name", ""),
            slug=data.get("slug", ""),
            classification=data.get("classification"),
            email=data.get("email"),
            contact=data.get("contact"),
            address=data.get("address"),
            website=data.get("website"),
            jurisdiction_id=jurisdiction.get("id") if isinstance(jurisdiction, dict) else None,
            jurisdiction_name=jurisdiction.get("name") if isinstance(jurisdiction, dict) else jurisdiction,
            jurisdiction_level=jurisdiction.get("slug") if isinstance(jurisdiction, dict) else None,
            categories=data.get("categories", []),
            request_count=data.get("request_count", 0),
            request_count_year=data.get("request_count_year", 0),
            request_success_rate=float(data.get("request_success_rate", 0) or 0),
            default_law_id=data.get("default_law", {}).get("id")
            if isinstance(data.get("default_law"), dict)
            else data.get("default_law"),
            laws=data.get("laws", []),
            geo=data.get("geo"),
            region=data.get("region"),
            created_at=self.parse_datetime(data.get("created_at")),
        )

    def _parse_message(self, data: dict[str, Any], request_id: int) -> FOIMessage:
        """Parse FOI message from API response."""
        return FOIMessage(
            id=data.get("id", 0),
            request_id=request_id,
            sender=data.get("sender", ""),
            subject=data.get("subject", ""),
            content=data.get("content", ""),
            timestamp=self.parse_datetime(data.get("timestamp")) or datetime.now(),
            attachments=data.get("attachments", []),
            is_redacted=data.get("is_redacted", False),
        )

    def _request_to_document(self, req: FOIRequest) -> APIDocument:
        """Convert FOIRequest to generic APIDocument."""
        return APIDocument(
            source_id=str(req.id),
            external_id=req.slug,
            title=req.title,
            url=req.url or f"https://fragdenstaat.de/anfrage/{req.slug}/",
            content=req.description,
            document_type="IFG-Anfrage",
            published_date=req.created_at,
            modified_date=req.last_message,
            tags=req.tags,
            categories=[req.status] if req.status else [],
            metadata={
                "status": req.status,
                "resolution": req.resolution,
                "public_body": req.public_body_name,
                "public_body_id": req.public_body_id,
                "jurisdiction": req.public_body_jurisdiction,
                "law": req.law_name,
                "costs": req.costs,
                "messages_count": req.messages_count,
                "attachments_count": req.attachments_count,
                "campaign": req.campaign,
            },
        )
