"""API client implementations for various public data sources."""

from crawlers.api_clients.base_api import BaseAPIClient
from crawlers.api_clients.oparl_client import OparlClient
from crawlers.api_clients.govdata_client import GovDataClient
from crawlers.api_clients.dip_bundestag_client import DIPBundestagClient
from crawlers.api_clients.fragdenstaat_client import FragDenStaatClient

__all__ = [
    "BaseAPIClient",
    "OparlClient",
    "GovDataClient",
    "DIPBundestagClient",
    "FragDenStaatClient",
]
