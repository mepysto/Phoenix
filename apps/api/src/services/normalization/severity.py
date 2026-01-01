"""Severity computation strategies for different data sources.

Each data source has its own way of expressing event severity. These
strategy classes implement source-specific logic to convert raw severity
data into our standardized SeverityLevel enum.

Example:
    strategy = USGSSeverityStrategy()
    severity = strategy.compute(raw_event)  # SeverityLevel.high
"""

from abc import ABC, abstractmethod

from src.models.event import SeverityLevel
from src.services.connectors.base import RawEvent


class SeverityStrategy(ABC):
    """Abstract base class for severity computation strategies.
    
    Each data source may express severity differently:
    - USGS uses earthquake magnitude (numeric)
    - GDACS uses alert levels (Green/Orange/Red)
    - EONET uses event categories
    - ReliefWeb uses status indicators
    
    Subclasses implement source-specific logic to convert these
    different representations into our SeverityLevel enum.
    """
    
    @abstractmethod
    def compute(self, raw: RawEvent) -> SeverityLevel:
        """Compute severity level from raw event data.
        
        Args:
            raw: RawEvent containing source-specific severity info
            
        Returns:
            Normalized SeverityLevel enum value
        """
        ...


class USGSSeverityStrategy(SeverityStrategy):
    """Severity strategy for USGS earthquake data.
    
    USGS provides earthquake magnitude on the Richter scale.
    We map these to severity levels based on typical impact:
    
    - magnitude >= 7.0: critical (major earthquake, widespread damage)
    - magnitude >= 6.0: high (strong earthquake, significant damage)
    - magnitude >= 4.5: medium (moderate earthquake, felt widely)
    - magnitude < 4.5: low (minor earthquake, limited impact)
    """
    
    def compute(self, raw: RawEvent) -> SeverityLevel:
        """Compute severity from USGS magnitude.
        
        Args:
            raw: RawEvent with magnitude field populated
            
        Returns:
            SeverityLevel based on magnitude thresholds
        """
        mag = raw.magnitude
        if mag is None:
            return SeverityLevel.medium
        
        if mag >= 7.0:
            return SeverityLevel.critical
        elif mag >= 6.0:
            return SeverityLevel.high
        elif mag >= 4.5:
            return SeverityLevel.medium
        return SeverityLevel.low


class EONETSeverityStrategy(SeverityStrategy):
    """Severity strategy for NASA EONET data.
    
    EONET categorizes events by type but doesn't provide explicit
    severity levels. We assign default severities based on typical
    impact of each event category.
    
    Categories with typically high immediate impact (wildfires, storms,
    earthquakes, volcanoes) are assigned 'high' severity by default.
    
    Categories with typically slower-onset impacts (floods, landslides,
    drought) are assigned 'medium' severity by default.
    """
    
    CATEGORY_SEVERITY: dict[str, SeverityLevel] = {
        # Original EONET categories (plural form)
        "wildfires": SeverityLevel.high,
        "severestorms": SeverityLevel.high,
        "earthquakes": SeverityLevel.high,
        "volcanoes": SeverityLevel.high,
        "floods": SeverityLevel.medium,
        "landslides": SeverityLevel.medium,
        "drought": SeverityLevel.medium,
        "dusthaze": SeverityLevel.low,
        "manmade": SeverityLevel.medium,
        "seaandlakeice": SeverityLevel.low,
        "snow": SeverityLevel.low,
        "tempextremes": SeverityLevel.medium,
        "watercolor": SeverityLevel.low,
        # Mapped types (singular form, after EONET_CATEGORY_MAP transformation)
        "wildfire": SeverityLevel.high,
        "storm": SeverityLevel.high,
        "earthquake": SeverityLevel.high,
        "volcano": SeverityLevel.high,
        "flood": SeverityLevel.medium,
        "landslide": SeverityLevel.medium,
        "industrial": SeverityLevel.medium,
        "heatwave": SeverityLevel.medium,
        "pollution": SeverityLevel.low,
        "other": SeverityLevel.medium,
    }
    
    def compute(self, raw: RawEvent) -> SeverityLevel:
        """Compute severity from EONET category.
        
        Args:
            raw: RawEvent with event_type_raw containing EONET category
            
        Returns:
            SeverityLevel based on category mapping
        """
        category = (raw.event_type_raw or "").lower().replace(" ", "")
        return self.CATEGORY_SEVERITY.get(category, SeverityLevel.medium)


class ReliefWebSeverityStrategy(SeverityStrategy):
    """Severity strategy for ReliefWeb disaster data.
    
    ReliefWeb provides disaster status but not explicit severity levels.
    Disasters reported on ReliefWeb are typically significant events
    that warrant humanitarian response.
    
    Current implementation returns 'medium' as a baseline, but can be
    enhanced with status-based logic (e.g., 'ongoing' = higher severity).
    """
    
    def compute(self, raw: RawEvent) -> SeverityLevel:
        """Compute severity from ReliefWeb data.
        
        Args:
            raw: RawEvent from ReliefWeb
            
        Returns:
            SeverityLevel (currently defaults to medium)
        """
        # ReliefWeb doesn't provide explicit severity
        # Could enhance based on:
        # - Number of affected countries
        # - Type of disaster
        # - Status (ongoing vs past)
        return SeverityLevel.medium


class GDACSAlertSeverityStrategy(SeverityStrategy):
    """Severity strategy for GDACS alert levels.
    
    GDACS uses a color-coded alert system:
    - Green: Low impact expected
    - Orange: Moderate impact expected  
    - Red: High impact expected
    
    This strategy parses the severity_raw field for GDACS alert levels.
    """
    
    ALERT_SEVERITY: dict[str, SeverityLevel] = {
        "green": SeverityLevel.low,
        "orange": SeverityLevel.medium,
        "red": SeverityLevel.high,
    }
    
    def compute(self, raw: RawEvent) -> SeverityLevel:
        """Compute severity from GDACS alert level.
        
        Args:
            raw: RawEvent with severity_raw containing alert level
            
        Returns:
            SeverityLevel based on alert color
        """
        alert = (raw.severity_raw or "").lower().strip()
        return self.ALERT_SEVERITY.get(alert, SeverityLevel.medium)


class DefaultSeverityStrategy(SeverityStrategy):
    """Default fallback severity strategy.
    
    Attempts to parse severity_raw as a SeverityLevel enum value.
    Falls back to 'medium' if parsing fails or no severity is provided.
    
    Use this strategy when the source provides severity as a string
    that matches our enum values (low, medium, high, critical).
    """
    
    def compute(self, raw: RawEvent) -> SeverityLevel:
        """Compute severity from raw severity string.
        
        Args:
            raw: RawEvent with optional severity_raw field
            
        Returns:
            Parsed SeverityLevel or medium as fallback
        """
        if raw.severity_raw:
            severity_str = raw.severity_raw.lower().strip()
            try:
                return SeverityLevel(severity_str)
            except ValueError:
                pass
        return SeverityLevel.medium


# Strategy registry for easy lookup
SEVERITY_STRATEGIES: dict[str, type[SeverityStrategy]] = {
    "USGS": USGSSeverityStrategy,
    "EONET": EONETSeverityStrategy,
    "ReliefWeb": ReliefWebSeverityStrategy,
    "GDACS": GDACSAlertSeverityStrategy,
}


def get_severity_strategy(source_name: str) -> SeverityStrategy:
    """Get the appropriate severity strategy for a data source.
    
    Args:
        source_name: Name of the data source
        
    Returns:
        Instantiated severity strategy for the source
    """
    strategy_class = SEVERITY_STRATEGIES.get(source_name, DefaultSeverityStrategy)
    return strategy_class()
