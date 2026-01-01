"""Admin area resolution for event geolocation.

This module provides the AdminAreaResolver class for linking events
to administrative areas (countries) based on coordinates or country info.

Example:
    resolver = AdminAreaResolver(session)
    
    # Resolve from coordinates
    admin_area_id = await resolver.resolve_from_point(lat=37.5, lng=127.0)
    
    # Resolve from country info (when no coordinates)
    admin_area_id, lat, lng = await resolver.resolve_from_country(
        country="South Korea",
        country_code="KR"
    )
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.geocoder_service import CountryGeocoder


class AdminAreaResolver:
    """Resolver for linking events to admin areas.
    
    This class wraps CountryGeocoder to provide convenient methods
    for the normalization pipeline. It handles two scenarios:
    
    1. Events WITH coordinates: Use spatial query to find containing country
    2. Events WITHOUT coordinates: Use country name/code to find admin area
       and return its centroid as fallback coordinates
    
    Attributes:
        geocoder: CountryGeocoder instance for lookups
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize resolver with database session.
        
        Args:
            session: AsyncSession for database queries
        """
        self.geocoder = CountryGeocoder(session)
    
    async def resolve_from_country(
        self,
        country: str | None,
        country_code: str | None,
    ) -> tuple[UUID | None, float | None, float | None]:
        """Resolve admin area from country name or code.
        
        Use this method when an event doesn't have coordinates but has
        country information. Returns the admin area and its centroid
        as fallback coordinates.
        
        Args:
            country: Country name (e.g., "South Korea")
            country_code: ISO alpha-2 or alpha-3 code (e.g., "KR" or "KOR")
            
        Returns:
            Tuple of (admin_area_id, centroid_lat, centroid_lng)
            All values may be None if no match found
            
        Example:
            >>> admin_id, lat, lng = await resolver.resolve_from_country(
            ...     country="Japan",
            ...     country_code="JP"
            ... )
            >>> print(f"Centroid: {lat}, {lng}")
            Centroid: 36.2048, 138.2529
        """
        # Prefer country code over name for more reliable matching
        identifier = country_code or country
        if not identifier:
            return None, None, None
        
        result = await self.geocoder.lookup(identifier)
        if result is None:
            return None, None, None
        
        return (
            result.admin_area_id,
            result.centroid_lat,
            result.centroid_lng,
        )
    
    async def resolve_from_point(
        self,
        lat: float,
        lng: float,
    ) -> UUID | None:
        """Find admin area containing a point.
        
        Use this method when an event has coordinates. Uses PostGIS
        ST_Contains to find which country polygon contains the point.
        
        Args:
            lat: Latitude (WGS84)
            lng: Longitude (WGS84)
            
        Returns:
            admin_area_id if point is within a country, None otherwise
            
        Example:
            >>> admin_id = await resolver.resolve_from_point(
            ...     lat=37.5665,
            ...     lng=126.9780
            ... )
            >>> # admin_id is UUID of South Korea
        """
        result = await self.geocoder.find_by_point(lat, lng)
        return result.admin_area_id if result else None
    
    async def resolve(
        self,
        lat: float | None,
        lng: float | None,
        country: str | None,
        country_code: str | None,
    ) -> tuple[UUID | None, float | None, float | None, bool]:
        """Resolve admin area using best available information.
        
        This is the primary method for the normalization pipeline.
        It tries coordinates first, then falls back to country info.
        
        Args:
            lat: Event latitude (optional)
            lng: Event longitude (optional)
            country: Country name (optional)
            country_code: ISO country code (optional)
            
        Returns:
            Tuple of (admin_area_id, final_lat, final_lng, used_centroid)
            - admin_area_id: UUID of admin area or None
            - final_lat: Original lat or centroid lat
            - final_lng: Original lng or centroid lng
            - used_centroid: True if centroid was used as fallback
            
        Example:
            >>> # Event with coordinates
            >>> result = await resolver.resolve(
            ...     lat=35.6762, lng=139.6503,
            ...     country="Japan", country_code="JP"
            ... )
            >>> admin_id, lat, lng, used_centroid = result
            >>> print(used_centroid)  # False - used original coords
            
            >>> # Event without coordinates
            >>> result = await resolver.resolve(
            ...     lat=None, lng=None,
            ...     country="Japan", country_code="JP"
            ... )
            >>> admin_id, lat, lng, used_centroid = result
            >>> print(used_centroid)  # True - used country centroid
        """
        # If we have coordinates, use spatial lookup
        if lat is not None and lng is not None:
            admin_area_id = await self.resolve_from_point(lat, lng)
            return admin_area_id, lat, lng, False
        
        # Fall back to country lookup
        admin_area_id, centroid_lat, centroid_lng = await self.resolve_from_country(
            country, country_code
        )
        return admin_area_id, centroid_lat, centroid_lng, True
