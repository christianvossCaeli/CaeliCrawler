"""
DIP Bundestag API Client.

DIP (Dokumentations- und Informationssystem für Parlamentarische Vorgänge)
provides access to all parliamentary documents of the German Bundestag.

API Documentation: https://dip.bundestag.de/über-dip/hilfe/api
Swagger UI: https://search.dip.bundestag.de/api/v1/swagger-ui/
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from crawlers.api_clients.base_api import APIDocument, APIResponse, BaseAPIClient


class DIPDokumentart(str, Enum):
    """Types of documents in DIP."""

    DRUCKSACHE = "Drucksache"
    PLENARPROTOKOLL = "Plenarprotokoll"


class DIPVorgangstyp(str, Enum):
    """Types of parliamentary processes."""

    GESETZGEBUNG = "Gesetzgebung"
    ANTRAG = "Antrag"
    KLEINE_ANFRAGE = "Kleine Anfrage"
    GROSSE_ANFRAGE = "Große Anfrage"
    SCHRIFTLICHE_FRAGE = "Schriftliche Frage"
    MUENDLICHE_FRAGE = "Mündliche Frage"
    PETITION = "Petition"
    EU_VORLAGE = "EU-Vorlage"
    UNTERSUCHUNGSAUSSCHUSS = "Untersuchungsausschuss"
    BERICHT = "Bericht"
    RECHTSVERORDNUNG = "Rechtsverordnung"


@dataclass
class DIPDrucksache:
    """Bundestag printed paper (Drucksache)."""

    id: str
    dokumentnummer: str  # e.g., "20/1234"
    wahlperiode: int  # Legislative period (e.g., 20)
    dokumentart: str
    datum: date | None = None
    titel: str | None = None
    autoren_anzahl: int = 0
    autoren: list[dict[str, Any]] = field(default_factory=list)
    fundstelle: str | None = None
    pdf_url: str | None = None
    drucksachetyp: str | None = None
    herausgeber: str | None = None
    urheber: list[str] = field(default_factory=list)
    vorgangsbezug: list[dict[str, Any]] = field(default_factory=list)
    ressort: list[dict[str, Any]] = field(default_factory=list)
    aktualisiert: datetime | None = None


@dataclass
class DIPPlenarprotokoll:
    """Bundestag plenary protocol."""

    id: str
    dokumentnummer: str  # e.g., "20/100"
    wahlperiode: int
    sitzungsnummer: int
    datum: date | None = None
    titel: str | None = None
    pdf_url: str | None = None
    herausgeber: str | None = None
    aktualisiert: datetime | None = None


@dataclass
class DIPVorgang:
    """Parliamentary process (Vorgang)."""

    id: str
    vorgangstyp: str
    wahlperiode: int
    titel: str
    initiative: list[str] = field(default_factory=list)
    beratungsstand: str | None = None
    abstract: str | None = None
    sachgebiet: list[str] = field(default_factory=list)
    deskriptor: list[dict[str, Any]] = field(default_factory=list)
    gesta: str | None = None  # GESTA-Nummer
    zustimmungsbeduerftigkeit: list[str] = field(default_factory=list)
    kom: str | None = None  # EU-Kommissionsnummer
    ratsdok: str | None = None  # EU-Ratsdokument
    verkuendung: list[dict[str, Any]] = field(default_factory=list)
    inkrafttreten: list[dict[str, Any]] = field(default_factory=list)
    archiv: str | None = None
    mitteilung: str | None = None
    aktualisiert: datetime | None = None


@dataclass
class DIPPerson:
    """Member of Parliament (Abgeordneter)."""

    id: str
    nachname: str
    vorname: str
    namenszusatz: str | None = None
    titel: str | None = None
    fraktion: str | None = None
    wahlperiode: list[int] = field(default_factory=list)
    basisdatum: date | None = None
    aktualisiert: datetime | None = None


@dataclass
class DIPAktivitaet:
    """Parliamentary activity."""

    id: str
    aktivitaetsart: str
    wahlperiode: int
    datum: date | None = None
    titel: str | None = None
    dokumentart: str | None = None
    drucksache: str | None = None
    plenarprotokoll: str | None = None
    vorgang_id: str | None = None
    fundstelle: dict[str, Any] | None = None
    aktualisiert: datetime | None = None


class DIPBundestagClient(BaseAPIClient):
    """
    Client for the DIP Bundestag API.

    Example usage:
        async with DIPBundestagClient() as client:
            # Search printed papers
            results = await client.search_drucksachen("Windenergie", wahlperiode=20)

            # Get specific Drucksache
            doc = await client.get_drucksache("20/1234")

            # Search processes
            vorgaenge = await client.search_vorgaenge(
                vorgangstyp=DIPVorgangstyp.KLEINE_ANFRAGE,
                wahlperiode=20
            )

            # Iterate all Kleine Anfragen
            async for anfrage in client.iterate_kleine_anfragen(wahlperiode=20):
                print(anfrage.titel)
    """

    BASE_URL = "https://search.dip.bundestag.de/api/v1"
    API_NAME = "DIP-Bundestag"
    DEFAULT_DELAY = 0.3  # DIP is quite responsive

    def __init__(self, api_key: str | None = None, **kwargs):
        import os
        # Load API key from environment variable (public API key for DIP Bundestag)
        resolved_api_key = api_key or os.environ.get("DIP_BUNDESTAG_API_KEY")
        super().__init__(api_key=resolved_api_key, **kwargs)

    def _get_auth_headers(self) -> dict[str, str]:
        """Add API key to headers."""
        if self.api_key:
            return {"Authorization": f"ApiKey {self.api_key}"}
        return {}

    # === Drucksachen (Printed Papers) ===

    async def search_drucksachen(
        self,
        query: str | None = None,
        wahlperiode: int | None = None,
        drucksachetyp: str | None = None,
        datum_start: date | None = None,
        datum_end: date | None = None,
        urheber: str | None = None,
        rows: int = 100,
        offset: int = 0,
    ) -> APIResponse[APIDocument]:
        """
        Search for Drucksachen (printed papers).

        Args:
            query: Full-text search query
            wahlperiode: Legislative period (e.g., 20 for current)
            drucksachetyp: Type of document
            datum_start: Start date filter
            datum_end: End date filter
            urheber: Author/originator filter
            rows: Number of results (max 100)
            offset: Pagination offset
        """
        params = {
            "format": "json",
            "rows": min(rows, 100),
            "offset": offset,
        }

        # Build filter list (f. parameter)
        filters = []
        if wahlperiode:
            filters.append(f"wahlperiode:{wahlperiode}")
        if drucksachetyp:
            filters.append(f"drucksachetyp:{drucksachetyp}")
        if urheber:
            filters.append(f"urheber:{urheber}")
        if datum_start:
            filters.append(f"datum_start:{datum_start.isoformat()}")
        if datum_end:
            filters.append(f"datum_end:{datum_end.isoformat()}")

        if query:
            params["q"] = query

        # Build URL with filter parameters
        param_parts = [f"{k}={v}" for k, v in params.items()]
        for filter_value in filters:
            param_parts.append(f"f.{filter_value}")

        url_params = "&".join(param_parts)
        data = await self.get(f"drucksache?{url_params}")

        if not data:
            return APIResponse(data=[], total_count=0)

        documents = data.get("documents", [])
        drucksachen = [self._parse_drucksache(d) for d in documents]
        api_docs = [self._drucksache_to_document(d) for d in drucksachen]

        return APIResponse(
            data=api_docs,
            total_count=data.get("numFound", len(documents)),
            page=(offset // rows) + 1 if rows > 0 else 1,
            per_page=rows,
            has_more=offset + rows < data.get("numFound", 0),
            raw_response=data,
        )

    async def get_drucksache(self, dokumentnummer: str) -> DIPDrucksache | None:
        """
        Get a specific Drucksache by document number.

        Args:
            dokumentnummer: Document number (e.g., "20/1234")
        """
        # Need to find by searching
        wp, nr = dokumentnummer.split("/") if "/" in dokumentnummer else (None, dokumentnummer)

        params = {"format": "json"}
        if wp:
            params["f.wahlperiode"] = wp
        params["f.dokumentnummer"] = dokumentnummer

        data = await self.get("drucksache", params)

        if data and data.get("documents"):
            return self._parse_drucksache(data["documents"][0])
        return None

    async def get_drucksache_text(self, document_id: str) -> str | None:
        """Get full text of a Drucksache."""
        data = await self.get(f"drucksache-text/{document_id}")
        if data:
            return data.get("text")
        return None

    async def iterate_drucksachen(
        self,
        wahlperiode: int = 20,
        drucksachetyp: str | None = None,
        batch_size: int = 100,
        max_documents: int = 10000,
        **kwargs,
    ) -> AsyncIterator[DIPDrucksache]:
        """Iterate through all Drucksachen for a legislative period."""
        offset = 0
        total = 0

        while total < max_documents:
            response = await self.search_drucksachen(
                wahlperiode=wahlperiode,
                drucksachetyp=drucksachetyp,
                rows=batch_size,
                offset=offset,
                **kwargs,
            )

            if not response.raw_response:
                break

            for doc_data in response.raw_response.get("documents", []):
                yield self._parse_drucksache(doc_data)
                total += 1
                if total >= max_documents:
                    return

            if not response.has_more:
                break

            offset += batch_size

    # === Plenarprotokolle (Plenary Protocols) ===

    async def search_plenarprotokolle(
        self,
        query: str | None = None,
        wahlperiode: int | None = None,
        datum_start: date | None = None,
        datum_end: date | None = None,
        rows: int = 100,
        offset: int = 0,
    ) -> APIResponse[APIDocument]:
        """Search for plenary protocols."""
        params = {
            "format": "json",
            "rows": min(rows, 100),
            "offset": offset,
        }

        if query:
            params["q"] = query
        if wahlperiode:
            params["f.wahlperiode"] = wahlperiode
        if datum_start:
            params["f.datum_start"] = datum_start.isoformat()
        if datum_end:
            params["f.datum_end"] = datum_end.isoformat()

        data = await self.get("plenarprotokoll", params)

        if not data:
            return APIResponse(data=[], total_count=0)

        documents = data.get("documents", [])
        protokolle = [self._parse_plenarprotokoll(d) for d in documents]
        api_docs = [self._plenarprotokoll_to_document(p) for p in protokolle]

        return APIResponse(
            data=api_docs,
            total_count=data.get("numFound", len(documents)),
            has_more=offset + rows < data.get("numFound", 0),
        )

    async def get_plenarprotokoll_text(self, document_id: str) -> str | None:
        """Get full text of a plenary protocol."""
        data = await self.get(f"plenarprotokoll-text/{document_id}")
        if data:
            return data.get("text")
        return None

    # === Vorgänge (Processes) ===

    async def search_vorgaenge(
        self,
        query: str | None = None,
        wahlperiode: int | None = None,
        vorgangstyp: str | DIPVorgangstyp | None = None,
        beratungsstand: str | None = None,
        sachgebiet: str | None = None,
        datum_start: date | None = None,
        datum_end: date | None = None,
        rows: int = 100,
        offset: int = 0,
    ) -> APIResponse[APIDocument]:
        """
        Search for parliamentary processes (Vorgänge).

        Args:
            query: Full-text search
            wahlperiode: Legislative period
            vorgangstyp: Type of process (Gesetzgebung, Kleine Anfrage, etc.)
            beratungsstand: Status of deliberation
            sachgebiet: Subject area
            datum_start: Start date
            datum_end: End date
            rows: Results per page
            offset: Pagination offset
        """
        params = {
            "format": "json",
            "rows": min(rows, 100),
            "offset": offset,
        }

        if query:
            params["q"] = query
        if wahlperiode:
            params["f.wahlperiode"] = wahlperiode
        if vorgangstyp:
            vt = vorgangstyp.value if isinstance(vorgangstyp, DIPVorgangstyp) else vorgangstyp
            params["f.vorgangstyp"] = vt
        if beratungsstand:
            params["f.beratungsstand"] = beratungsstand
        if sachgebiet:
            params["f.sachgebiet"] = sachgebiet
        if datum_start:
            params["f.datum_start"] = datum_start.isoformat()
        if datum_end:
            params["f.datum_end"] = datum_end.isoformat()

        data = await self.get("vorgang", params)

        if not data:
            return APIResponse(data=[], total_count=0)

        documents = data.get("documents", [])
        vorgaenge = [self._parse_vorgang(d) for d in documents]
        api_docs = [self._vorgang_to_document(v) for v in vorgaenge]

        return APIResponse(
            data=api_docs,
            total_count=data.get("numFound", len(documents)),
            has_more=offset + rows < data.get("numFound", 0),
        )

    async def iterate_kleine_anfragen(
        self,
        wahlperiode: int = 20,
        batch_size: int = 100,
        max_documents: int = 50000,
    ) -> AsyncIterator[DIPVorgang]:
        """Iterate through all Kleine Anfragen for a legislative period."""
        offset = 0
        total = 0

        while total < max_documents:
            response = await self.search_vorgaenge(
                wahlperiode=wahlperiode,
                vorgangstyp=DIPVorgangstyp.KLEINE_ANFRAGE,
                rows=batch_size,
                offset=offset,
            )

            if not response.raw_response:
                break

            for doc_data in response.raw_response.get("documents", []):
                yield self._parse_vorgang(doc_data)
                total += 1
                if total >= max_documents:
                    return

            if not response.has_more:
                break

            offset += batch_size

    # === Personen (MPs) ===

    async def search_personen(
        self,
        query: str | None = None,
        wahlperiode: int | None = None,
        fraktion: str | None = None,
        rows: int = 100,
        offset: int = 0,
    ) -> list[DIPPerson]:
        """Search for Members of Parliament."""
        params = {
            "format": "json",
            "rows": min(rows, 100),
            "offset": offset,
        }

        if query:
            params["q"] = query
        if wahlperiode:
            params["f.wahlperiode"] = wahlperiode
        if fraktion:
            params["f.fraktion"] = fraktion

        data = await self.get("person", params)

        if not data:
            return []

        return [self._parse_person(d) for d in data.get("documents", [])]

    # === Aktivitäten ===

    async def search_aktivitaeten(
        self,
        query: str | None = None,
        wahlperiode: int | None = None,
        aktivitaetsart: str | None = None,
        rows: int = 100,
        offset: int = 0,
    ) -> list[DIPAktivitaet]:
        """Search for parliamentary activities."""
        params = {
            "format": "json",
            "rows": min(rows, 100),
            "offset": offset,
        }

        if query:
            params["q"] = query
        if wahlperiode:
            params["f.wahlperiode"] = wahlperiode
        if aktivitaetsart:
            params["f.aktivitaetsart"] = aktivitaetsart

        data = await self.get("aktivitaet", params)

        if not data:
            return []

        return [self._parse_aktivitaet(d) for d in data.get("documents", [])]

    # === Generic Search Interface ===

    async def search(
        self,
        query: str,
        document_type: str = "drucksache",
        **kwargs,
    ) -> APIResponse[APIDocument]:
        """Generic search interface."""
        if document_type == "drucksache":
            return await self.search_drucksachen(query=query, **kwargs)
        elif document_type == "plenarprotokoll":
            return await self.search_plenarprotokolle(query=query, **kwargs)
        elif document_type == "vorgang":
            return await self.search_vorgaenge(query=query, **kwargs)
        else:
            return await self.search_drucksachen(query=query, **kwargs)

    async def get_document(self, document_id: str) -> APIDocument | None:
        """Get document by ID."""
        drucksache = await self.get_drucksache(document_id)
        if drucksache:
            return self._drucksache_to_document(drucksache)
        return None

    # === Parsers ===

    def _parse_drucksache(self, data: dict[str, Any]) -> DIPDrucksache:
        """Parse Drucksache from API response."""
        # PDF URL is in fundstelle.pdf_url, not at top level
        fundstelle = data.get("fundstelle") or {}
        pdf_url = data.get("pdf_url") or fundstelle.get("pdf_url")

        return DIPDrucksache(
            id=str(data.get("id", "")),
            dokumentnummer=data.get("dokumentnummer", ""),
            wahlperiode=data.get("wahlperiode", 0),
            dokumentart=data.get("dokumentart", "Drucksache"),
            datum=self._parse_date(data.get("datum")),
            titel=data.get("titel"),
            autoren_anzahl=data.get("autoren_anzahl", 0),
            autoren=data.get("autoren", []),
            fundstelle=data.get("fundstelle"),
            pdf_url=pdf_url,
            drucksachetyp=data.get("drucksachetyp"),
            herausgeber=data.get("herausgeber"),
            urheber=data.get("urheber", []),
            vorgangsbezug=data.get("vorgangsbezug", []),
            ressort=data.get("ressort", []),
            aktualisiert=self.parse_datetime(data.get("aktualisiert")),
        )

    def _parse_plenarprotokoll(self, data: dict[str, Any]) -> DIPPlenarprotokoll:
        """Parse Plenarprotokoll from API response."""
        return DIPPlenarprotokoll(
            id=str(data.get("id", "")),
            dokumentnummer=data.get("dokumentnummer", ""),
            wahlperiode=data.get("wahlperiode", 0),
            sitzungsnummer=data.get("sitzungsnummer", 0),
            datum=self._parse_date(data.get("datum")),
            titel=data.get("titel"),
            pdf_url=data.get("pdf_url"),
            herausgeber=data.get("herausgeber"),
            aktualisiert=self.parse_datetime(data.get("aktualisiert")),
        )

    def _parse_vorgang(self, data: dict[str, Any]) -> DIPVorgang:
        """Parse Vorgang from API response."""
        return DIPVorgang(
            id=str(data.get("id", "")),
            vorgangstyp=data.get("vorgangstyp", ""),
            wahlperiode=data.get("wahlperiode", 0),
            titel=data.get("titel", ""),
            initiative=data.get("initiative", []),
            beratungsstand=data.get("beratungsstand"),
            abstract=data.get("abstract"),
            sachgebiet=data.get("sachgebiet", []),
            deskriptor=data.get("deskriptor", []),
            gesta=data.get("gesta"),
            zustimmungsbeduerftigkeit=data.get("zustimmungsbeduerftigkeit", []),
            kom=data.get("kom"),
            ratsdok=data.get("ratsdok"),
            verkuendung=data.get("verkuendung", []),
            inkrafttreten=data.get("inkrafttreten", []),
            archiv=data.get("archiv"),
            mitteilung=data.get("mitteilung"),
            aktualisiert=self.parse_datetime(data.get("aktualisiert")),
        )

    def _parse_person(self, data: dict[str, Any]) -> DIPPerson:
        """Parse Person from API response."""
        return DIPPerson(
            id=str(data.get("id", "")),
            nachname=data.get("nachname", ""),
            vorname=data.get("vorname", ""),
            namenszusatz=data.get("namenszusatz"),
            titel=data.get("titel"),
            fraktion=data.get("fraktion"),
            wahlperiode=data.get("wahlperiode", []),
            basisdatum=self._parse_date(data.get("basisdatum")),
            aktualisiert=self.parse_datetime(data.get("aktualisiert")),
        )

    def _parse_aktivitaet(self, data: dict[str, Any]) -> DIPAktivitaet:
        """Parse Aktivitaet from API response."""
        return DIPAktivitaet(
            id=str(data.get("id", "")),
            aktivitaetsart=data.get("aktivitaetsart", ""),
            wahlperiode=data.get("wahlperiode", 0),
            datum=self._parse_date(data.get("datum")),
            titel=data.get("titel"),
            dokumentart=data.get("dokumentart"),
            drucksache=data.get("drucksache"),
            plenarprotokoll=data.get("plenarprotokoll"),
            vorgang_id=data.get("vorgang_id"),
            fundstelle=data.get("fundstelle"),
            aktualisiert=self.parse_datetime(data.get("aktualisiert")),
        )

    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    # === Document Converters ===

    def _drucksache_to_document(self, d: DIPDrucksache) -> APIDocument:
        """Convert Drucksache to generic APIDocument."""
        return APIDocument(
            source_id=d.id,
            external_id=d.dokumentnummer,
            title=d.titel or d.dokumentnummer,
            url=f"https://dip.bundestag.de/drucksache/{d.dokumentnummer.replace('/', '-')}",
            document_type=d.drucksachetyp or "Drucksache",
            file_url=d.pdf_url,
            mime_type="application/pdf" if d.pdf_url else None,
            published_date=datetime.combine(d.datum, datetime.min.time()) if d.datum else None,
            modified_date=d.aktualisiert,
            categories=[d.drucksachetyp] if d.drucksachetyp else [],
            tags=[r.get("titel", "") for r in d.ressort if r.get("titel")],
            metadata={
                "wahlperiode": d.wahlperiode,
                "dokumentnummer": d.dokumentnummer,
                "herausgeber": d.herausgeber,
                "urheber": d.urheber,
                "autoren_anzahl": d.autoren_anzahl,
                "vorgangsbezug": [v.get("id") for v in d.vorgangsbezug],
            },
        )

    def _plenarprotokoll_to_document(self, p: DIPPlenarprotokoll) -> APIDocument:
        """Convert Plenarprotokoll to generic APIDocument."""
        return APIDocument(
            source_id=p.id,
            external_id=p.dokumentnummer,
            title=p.titel or f"Plenarprotokoll {p.dokumentnummer}",
            url=f"https://dip.bundestag.de/plenarprotokoll/{p.dokumentnummer.replace('/', '-')}",
            document_type="Plenarprotokoll",
            file_url=p.pdf_url,
            mime_type="application/pdf" if p.pdf_url else None,
            published_date=datetime.combine(p.datum, datetime.min.time()) if p.datum else None,
            modified_date=p.aktualisiert,
            metadata={
                "wahlperiode": p.wahlperiode,
                "sitzungsnummer": p.sitzungsnummer,
                "herausgeber": p.herausgeber,
            },
        )

    def _vorgang_to_document(self, v: DIPVorgang) -> APIDocument:
        """Convert Vorgang to generic APIDocument."""
        return APIDocument(
            source_id=v.id,
            external_id=v.gesta,
            title=v.titel,
            url=f"https://dip.bundestag.de/vorgang/{v.id}",
            content=v.abstract,
            document_type=v.vorgangstyp,
            published_date=None,
            modified_date=v.aktualisiert,
            categories=[v.vorgangstyp] + v.sachgebiet,
            tags=[d.get("name", "") for d in v.deskriptor if d.get("name")],
            metadata={
                "wahlperiode": v.wahlperiode,
                "beratungsstand": v.beratungsstand,
                "initiative": v.initiative,
                "gesta": v.gesta,
                "kom": v.kom,
                "ratsdok": v.ratsdok,
            },
        )
