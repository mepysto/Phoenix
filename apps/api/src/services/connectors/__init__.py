"""Connectors for external data sources.

This package contains connector implementations for various disaster
event data sources.

Exports:
    RawEvent: Dataclass for parsed raw events from any source
    Connector: Protocol that all connectors must implement
    USGSConnector: Connector for USGS Earthquake API
    USGSEarthquake: Dataclass for USGS earthquake events
    EONETConnector: Connector for NASA EONET API
    EONETEvent: Dataclass for EONET natural events
"""

from src.services.connectors.base import Connector, RawEvent
from src.services.connectors.eonet_connector import EONETConnector, EONETEvent
from src.services.connectors.usgs_connector import USGSConnector, USGSEarthquake

__all__ = [
    "Connector",
    "EONETConnector",
    "EONETEvent",
    "RawEvent",
    "USGSConnector",
    "USGSEarthquake",
]
