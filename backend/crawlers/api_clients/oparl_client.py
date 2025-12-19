"""
OParl API Client for German municipal council information systems.

OParl is a standardized API for accessing parliamentary information from
German municipalities. See: https://oparl.org/

Supports OParl 1.0 and 1.1 specifications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from crawlers.api_clients.base_api import BaseAPIClient, APIResponse, APIDocument


@dataclass
class OparlBody:
    """OParl Body (Körperschaft) representation."""

    id: str
    name: str
    short_name: Optional[str] = None
    website: Optional[str] = None
    license: Optional[str] = None
    license_valid_since: Optional[datetime] = None
    oparl_since: Optional[datetime] = None
    ags: Optional[str] = None  # Amtlicher Gemeindeschlüssel
    rgs: Optional[str] = None  # Regionalschlüssel
    equivalent: List[str] = field(default_factory=list)
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None

    # Navigation URLs
    organization_url: Optional[str] = None
    person_url: Optional[str] = None
    meeting_url: Optional[str] = None
    paper_url: Optional[str] = None
    legislative_term_url: Optional[str] = None
    membership_url: Optional[str] = None
    consultation_url: Optional[str] = None

    location: Optional[Dict[str, Any]] = None
    classification: Optional[str] = None

    created: Optional[datetime] = None
    modified: Optional[datetime] = None


@dataclass
class OparlPaper:
    """OParl Paper (Drucksache) representation."""

    id: str
    name: Optional[str] = None
    reference: Optional[str] = None  # Drucksachennummer
    date: Optional[datetime] = None
    paper_type: Optional[str] = None

    body_id: Optional[str] = None
    body_name: Optional[str] = None

    # Related entities
    originator_persons: List[str] = field(default_factory=list)
    originator_organizations: List[str] = field(default_factory=list)
    consultation_urls: List[str] = field(default_factory=list)
    under_direction_of: List[str] = field(default_factory=list)

    # Files
    main_file: Optional[Dict[str, Any]] = None
    auxiliary_files: List[Dict[str, Any]] = field(default_factory=list)

    # Locations
    locations: List[Dict[str, Any]] = field(default_factory=list)

    # Superordinate/subordinate papers
    superordinate_paper: Optional[str] = None
    subordinate_papers: List[str] = field(default_factory=list)
    related_papers: List[str] = field(default_factory=list)

    keyword: List[str] = field(default_factory=list)
    web: Optional[str] = None

    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    deleted: bool = False


@dataclass
class OparlMeeting:
    """OParl Meeting (Sitzung) representation."""

    id: str
    name: Optional[str] = None
    meeting_state: Optional[str] = None
    cancelled: bool = False

    start: Optional[datetime] = None
    end: Optional[datetime] = None

    location: Optional[Dict[str, Any]] = None
    organization_urls: List[str] = field(default_factory=list)

    # Agenda and results
    agenda_item_urls: List[str] = field(default_factory=list)
    agenda_items: List[Dict[str, Any]] = field(default_factory=list)
    invitation_file: Optional[Dict[str, Any]] = None
    results_protocol_file: Optional[Dict[str, Any]] = None
    verbatim_protocol_file: Optional[Dict[str, Any]] = None
    auxiliary_files: List[Dict[str, Any]] = field(default_factory=list)

    keyword: List[str] = field(default_factory=list)
    web: Optional[str] = None

    created: Optional[datetime] = None
    modified: Optional[datetime] = None


class OparlClient(BaseAPIClient):
    """
    Client for OParl-compliant municipal council APIs.

    Example usage:
        async with OparlClient("https://oparl.stadt-koeln.de/") as client:
            # Get all bodies
            async for body in client.get_bodies():
                print(body.name)

            # Search papers
            papers = await client.search("Windkraft")

            # Get papers modified since date
            async for paper in client.get_papers(
                body_id="...",
                modified_since=datetime(2024, 1, 1)
            ):
                print(paper.name)
    """

    API_NAME = "OParl"
    DEFAULT_DELAY = 0.5  # OParl is usually local government servers

    def __init__(self, system_url: str, **kwargs):
        """
        Initialize OParl client.

        Args:
            system_url: The OParl system endpoint URL
        """
        super().__init__(**kwargs)
        self.system_url = system_url.rstrip("/")
        self.BASE_URL = system_url
        self._system_info: Optional[Dict[str, Any]] = None
        self._bodies_cache: Dict[str, OparlBody] = {}

    async def get_system_info(self) -> Dict[str, Any]:
        """Get OParl system information."""
        if not self._system_info:
            self._system_info = await self.get(self.system_url) or {}
        return self._system_info

    async def get_bodies(self) -> AsyncIterator[OparlBody]:
        """Get all bodies (Körperschaften) from this OParl system."""
        system = await self.get_system_info()
        bodies_url = system.get("body")

        if not bodies_url:
            self.logger.warning("No bodies URL in system info")
            return

        async for page_data in self.paginate(bodies_url):
            items = page_data.get("data", [])
            if isinstance(page_data, list):
                items = page_data

            for item in items:
                body = self._parse_body(item)
                self._bodies_cache[body.id] = body
                yield body

    async def get_body(self, body_id: str) -> Optional[OparlBody]:
        """Get a single body by ID or URL."""
        if body_id in self._bodies_cache:
            return self._bodies_cache[body_id]

        data = await self.get(body_id)
        if data:
            body = self._parse_body(data)
            self._bodies_cache[body.id] = body
            return body
        return None

    async def get_papers(
        self,
        body: OparlBody,
        modified_since: Optional[datetime] = None,
        created_since: Optional[datetime] = None,
        paper_type: Optional[str] = None,
        max_pages: int = 100,
    ) -> AsyncIterator[OparlPaper]:
        """
        Get papers (Drucksachen) from a body.

        Args:
            body: The body to get papers from
            modified_since: Only return papers modified after this date
            created_since: Only return papers created after this date
            paper_type: Filter by paper type
            max_pages: Maximum pages to fetch
        """
        papers_url = body.paper_url
        if not papers_url:
            self.logger.warning("No papers URL for body", body=body.name)
            return

        params = {}
        if modified_since:
            params["modified_since"] = modified_since.isoformat()
        if created_since:
            params["created_since"] = created_since.isoformat()

        page_count = 0
        async for page_data in self.paginate(papers_url, params, max_pages):
            items = page_data.get("data", [])
            if isinstance(page_data, list):
                items = page_data

            for item in items:
                paper = self._parse_paper(item)
                paper.body_id = body.id
                paper.body_name = body.name

                # Filter by paper type if specified
                if paper_type and paper.paper_type != paper_type:
                    continue

                yield paper

            page_count += 1

    async def get_meetings(
        self,
        body: OparlBody,
        modified_since: Optional[datetime] = None,
        start_after: Optional[datetime] = None,
        start_before: Optional[datetime] = None,
        max_pages: int = 50,
    ) -> AsyncIterator[OparlMeeting]:
        """
        Get meetings (Sitzungen) from a body.

        Args:
            body: The body to get meetings from
            modified_since: Only return meetings modified after this date
            start_after: Only return meetings starting after this date
            start_before: Only return meetings starting before this date
            max_pages: Maximum pages to fetch
        """
        meetings_url = body.meeting_url
        if not meetings_url:
            self.logger.warning("No meetings URL for body", body=body.name)
            return

        params = {}
        if modified_since:
            params["modified_since"] = modified_since.isoformat()

        async for page_data in self.paginate(meetings_url, params, max_pages):
            items = page_data.get("data", [])
            if isinstance(page_data, list):
                items = page_data

            for item in items:
                meeting = self._parse_meeting(item)

                # Date filters
                if start_after and meeting.start and meeting.start < start_after:
                    continue
                if start_before and meeting.start and meeting.start > start_before:
                    continue

                yield meeting

    async def get_organizations(
        self,
        body: OparlBody,
        max_pages: int = 20,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Get organizations (Gremien, Fraktionen) from a body."""
        org_url = body.organization_url
        if not org_url:
            return

        async for page_data in self.paginate(org_url, max_pages=max_pages):
            items = page_data.get("data", [])
            if isinstance(page_data, list):
                items = page_data
            for item in items:
                yield item

    async def get_persons(
        self,
        body: OparlBody,
        max_pages: int = 20,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Get persons (Mitglieder) from a body."""
        persons_url = body.person_url
        if not persons_url:
            return

        async for page_data in self.paginate(persons_url, max_pages=max_pages):
            items = page_data.get("data", [])
            if isinstance(page_data, list):
                items = page_data
            for item in items:
                yield item

    async def search(
        self,
        query: str,
        body: Optional[OparlBody] = None,
        object_type: str = "paper",
        **kwargs,
    ) -> APIResponse[APIDocument]:
        """
        Search for documents.

        Note: OParl doesn't have a standardized search endpoint.
        This method fetches all papers and filters locally.
        For large datasets, use get_papers() with date filters instead.
        """
        documents = []

        if body:
            bodies = [body]
        else:
            bodies = [b async for b in self.get_bodies()]

        query_lower = query.lower()

        for b in bodies:
            if object_type == "paper":
                async for paper in self.get_papers(b, max_pages=10):
                    # Check if query matches
                    searchable = f"{paper.name or ''} {paper.reference or ''} {' '.join(paper.keyword)}"
                    if query_lower in searchable.lower():
                        doc = self._paper_to_document(paper)
                        documents.append(doc)
            elif object_type == "meeting":
                async for meeting in self.get_meetings(b, max_pages=10):
                    searchable = f"{meeting.name or ''} {' '.join(meeting.keyword)}"
                    if query_lower in searchable.lower():
                        doc = self._meeting_to_document(meeting)
                        documents.append(doc)

        return APIResponse(
            data=documents,
            total_count=len(documents),
        )

    async def get_document(self, document_id: str) -> Optional[APIDocument]:
        """Get a single document by URL/ID."""
        data = await self.get(document_id)
        if not data:
            return None

        obj_type = data.get("type", "").split("/")[-1].lower()

        if obj_type == "paper":
            paper = self._parse_paper(data)
            return self._paper_to_document(paper)
        elif obj_type == "meeting":
            meeting = self._parse_meeting(data)
            return self._meeting_to_document(meeting)

        return None

    def _extract_pagination_info(
        self,
        response: Dict[str, Any],
        current_params: Dict[str, Any],
    ) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Extract OParl pagination info."""
        # OParl uses links.next pattern
        links = response.get("links", {})
        next_url = links.get("next")
        if next_url:
            return next_url, None

        # Some implementations use pagination object
        pagination = response.get("pagination", {})
        if pagination:
            current_page = pagination.get("currentPage", 1)
            total_pages = pagination.get("totalPages", 1)
            if current_page < total_pages:
                # Need to construct next URL from current
                # This varies by implementation
                pass

        return None, None

    def _parse_body(self, data: Dict[str, Any]) -> OparlBody:
        """Parse body data into OparlBody object."""
        return OparlBody(
            id=data.get("id", ""),
            name=data.get("name", ""),
            short_name=data.get("shortName"),
            website=data.get("website"),
            license=data.get("license"),
            license_valid_since=self.parse_datetime(data.get("licenseValidSince")),
            oparl_since=self.parse_datetime(data.get("oparlSince")),
            ags=data.get("ags"),
            rgs=data.get("rgs"),
            equivalent=data.get("equivalent", []),
            contact_email=data.get("contactEmail"),
            contact_name=data.get("contactName"),
            organization_url=data.get("organization"),
            person_url=data.get("person"),
            meeting_url=data.get("meeting"),
            paper_url=data.get("paper"),
            legislative_term_url=data.get("legislativeTerm"),
            membership_url=data.get("membership"),
            consultation_url=data.get("consultation"),
            location=data.get("location"),
            classification=data.get("classification"),
            created=self.parse_datetime(data.get("created")),
            modified=self.parse_datetime(data.get("modified")),
        )

    def _parse_paper(self, data: Dict[str, Any]) -> OparlPaper:
        """Parse paper data into OparlPaper object."""
        return OparlPaper(
            id=data.get("id", ""),
            name=data.get("name"),
            reference=data.get("reference"),
            date=self.parse_datetime(data.get("date")),
            paper_type=data.get("paperType"),
            originator_persons=data.get("originatorPerson", []),
            originator_organizations=data.get("originatorOrganization", []),
            consultation_urls=data.get("consultation", []),
            under_direction_of=data.get("underDirectionOf", []),
            main_file=data.get("mainFile"),
            auxiliary_files=data.get("auxiliaryFile", []),
            locations=data.get("location", []),
            superordinate_paper=data.get("superordinatedPaper"),
            subordinate_papers=data.get("subordinatedPaper", []),
            related_papers=data.get("relatedPaper", []),
            keyword=data.get("keyword", []),
            web=data.get("web"),
            created=self.parse_datetime(data.get("created")),
            modified=self.parse_datetime(data.get("modified")),
            deleted=data.get("deleted", False),
        )

    def _parse_meeting(self, data: Dict[str, Any]) -> OparlMeeting:
        """Parse meeting data into OparlMeeting object."""
        return OparlMeeting(
            id=data.get("id", ""),
            name=data.get("name"),
            meeting_state=data.get("meetingState"),
            cancelled=data.get("cancelled", False),
            start=self.parse_datetime(data.get("start")),
            end=self.parse_datetime(data.get("end")),
            location=data.get("location"),
            organization_urls=data.get("organization", []),
            agenda_item_urls=data.get("agendaItem", []),
            invitation_file=data.get("invitation"),
            results_protocol_file=data.get("resultsProtocol"),
            verbatim_protocol_file=data.get("verbatimProtocol"),
            auxiliary_files=data.get("auxiliaryFile", []),
            keyword=data.get("keyword", []),
            web=data.get("web"),
            created=self.parse_datetime(data.get("created")),
            modified=self.parse_datetime(data.get("modified")),
        )

    def _paper_to_document(self, paper: OparlPaper) -> APIDocument:
        """Convert OparlPaper to generic APIDocument."""
        # Get primary file URL
        file_url = None
        mime_type = None
        if paper.main_file:
            file_url = paper.main_file.get("accessUrl") or paper.main_file.get("downloadUrl")
            mime_type = paper.main_file.get("mimeType")

        return APIDocument(
            source_id=paper.id,
            external_id=paper.reference,
            title=paper.name or paper.reference or "Untitled",
            url=paper.web or paper.id,
            document_type=paper.paper_type or "Drucksache",
            file_url=file_url,
            mime_type=mime_type,
            published_date=paper.date,
            modified_date=paper.modified,
            tags=paper.keyword,
            categories=[paper.paper_type] if paper.paper_type else [],
            metadata={
                "reference": paper.reference,
                "body_id": paper.body_id,
                "body_name": paper.body_name,
                "originator_persons": paper.originator_persons,
                "originator_organizations": paper.originator_organizations,
                "auxiliary_files_count": len(paper.auxiliary_files),
            },
        )

    def _meeting_to_document(self, meeting: OparlMeeting) -> APIDocument:
        """Convert OparlMeeting to generic APIDocument."""
        file_url = None
        mime_type = None
        if meeting.results_protocol_file:
            file_url = meeting.results_protocol_file.get("accessUrl")
            mime_type = meeting.results_protocol_file.get("mimeType")

        return APIDocument(
            source_id=meeting.id,
            title=meeting.name or "Meeting",
            url=meeting.web or meeting.id,
            document_type="Sitzung",
            file_url=file_url,
            mime_type=mime_type,
            published_date=meeting.start,
            modified_date=meeting.modified,
            tags=meeting.keyword,
            metadata={
                "meeting_state": meeting.meeting_state,
                "cancelled": meeting.cancelled,
                "start": meeting.start.isoformat() if meeting.start else None,
                "end": meeting.end.isoformat() if meeting.end else None,
                "has_invitation": meeting.invitation_file is not None,
                "has_protocol": meeting.results_protocol_file is not None,
            },
        )


# List of known OParl endpoints
KNOWN_OPARL_ENDPOINTS = [
    # NRW
    {"name": "Köln", "url": "https://ratsinformation.stadt-koeln.de/webservice/oparl/v1.0/system", "state": "NRW"},
    {"name": "Düsseldorf", "url": "https://ris-oparl.itk-rheinland.de/Oparl/bodies/0015", "state": "NRW"},
    {"name": "Münster", "url": "https://oparl.stadt-muenster.de/", "state": "NRW"},
    {"name": "Bonn", "url": "https://oparl.kdvz-frechen.de/rim4710/webservice/oparl/v1.1/system", "state": "NRW"},

    # Baden-Württemberg
    {"name": "Stuttgart", "url": "https://www.domino1.stuttgart.de/oparl/system", "state": "BW"},
    {"name": "Karlsruhe", "url": "https://web1.karlsruhe.de/oparl/", "state": "BW"},

    # Bayern
    {"name": "München", "url": "https://www.ris-muenchen.de/oparl/v1.1/system", "state": "BY"},
    {"name": "Nürnberg", "url": "https://online-service.nuernberg.de/oparl/system", "state": "BY"},

    # Hessen
    {"name": "Frankfurt", "url": "https://ris.frankfurt.de/oparl/v1.0/system", "state": "HE"},

    # Niedersachsen
    {"name": "Hannover", "url": "https://e-government.hannover-stadt.de/oparl/system", "state": "NI"},

    # Sachsen
    {"name": "Dresden", "url": "https://ratsinfo.dresden.de/oparl/system", "state": "SN"},
    {"name": "Leipzig", "url": "https://ratsinformation.leipzig.de/oparl/system", "state": "SN"},

    # Schleswig-Holstein
    {"name": "Kiel", "url": "https://ratsinfo.kiel.de/oparl/system", "state": "SH"},

    # More endpoints from OParl resources
    # See: https://github.com/OParl/resources/blob/main/endpoints.yml
]
