"""Event normalization components.

This package contains components for normalizing raw events from
various data sources into standardized database-ready payloads.

Exports:
    EventUpsertPayload: Dataclass for normalized event data
    Normalizer: Protocol for normalizer implementations
    
    SeverityStrategy: ABC for severity computation
    USGSSeverityStrategy: USGS earthquake magnitude strategy
    EONETSeverityStrategy: NASA EONET category strategy
    ReliefWebSeverityStrategy: ReliefWeb default strategy
    GDACSAlertSeverityStrategy: GDACS alert level strategy
    DefaultSeverityStrategy: Fallback string parsing strategy
    get_severity_strategy: Factory function for strategies
    
    AdminAreaResolver: Helper for admin area resolution
"""

from src.services.normalization.admin_area import AdminAreaResolver
from src.services.normalization.base import EventUpsertPayload, Normalizer
from src.services.normalization.severity import (
    DefaultSeverityStrategy,
    EONETSeverityStrategy,
    GDACSAlertSeverityStrategy,
    ReliefWebSeverityStrategy,
    SeverityStrategy,
    USGSSeverityStrategy,
    get_severity_strategy,
)

__all__ = [
    # Base classes
    "EventUpsertPayload",
    "Normalizer",
    # Severity strategies
    "SeverityStrategy",
    "USGSSeverityStrategy",
    "EONETSeverityStrategy",
    "ReliefWebSeverityStrategy",
    "GDACSAlertSeverityStrategy",
    "DefaultSeverityStrategy",
    "get_severity_strategy",
    # Admin area
    "AdminAreaResolver",
]
