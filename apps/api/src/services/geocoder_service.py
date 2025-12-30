"""
CountryGeocoder Service

Provides country lookup by ISO code or name, returning admin area centroids
for geocoding purposes.

Usage:
    geocoder = CountryGeocoder(session)
    
    # Single lookup
    result = await geocoder.lookup("KR")        # ISO alpha-2
    result = await geocoder.lookup("KOR")       # ISO alpha-3  
    result = await geocoder.lookup("South Korea")  # Country name
    
    # Batch lookup
    results = await geocoder.batch_lookup(["KR", "US", "Japan"])
    
    # Reverse geocoding (point to country)
    country = await geocoder.find_by_point(lat=37.5665, lng=126.9780)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING
from uuid import UUID

from geoalchemy2.functions import ST_Contains, ST_SetSRID, ST_MakePoint, ST_X, ST_Y
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.admin_area import AdminArea
from src.models.event import GeoMethod, GeoPrecision

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class AdminAreaLookupResult:
    """Result of an admin area lookup.
    
    Attributes:
        admin_area_id: UUID of the admin area
        iso_a2: ISO 3166-1 alpha-2 code (e.g., "KR")
        iso_a3: ISO 3166-1 alpha-3 code (e.g., "KOR")
        name: English name of the country
        centroid_lng: Longitude of centroid
        centroid_lat: Latitude of centroid
        geo_precision: Precision level (always 'country' for this service)
        geo_method: Method used (always 'admin_centroid' for this service)
    """
    admin_area_id: UUID
    iso_a2: str | None
    iso_a3: str | None
    name: str
    centroid_lng: float
    centroid_lat: float
    geo_precision: GeoPrecision = GeoPrecision.country
    geo_method: GeoMethod = GeoMethod.admin_centroid
    
    @property
    def centroid(self) -> tuple[float, float]:
        """Return centroid as (lng, lat) tuple."""
        return (self.centroid_lng, self.centroid_lat)


class CountryGeocoder:
    """Geocoder service for country-level lookups.
    
    Provides efficient lookup of countries by ISO code or name,
    with in-memory caching for frequently accessed data.
    
    Args:
        session: AsyncSession for database queries
        cache_enabled: Whether to use in-memory caching (default: True)
    """
    
    # Class-level cache for country data
    # Key: normalized identifier (uppercase ISO code or lowercase name)
    # Value: AdminAreaLookupResult
    _cache: dict[str, AdminAreaLookupResult] = {}
    _cache_loaded: bool = False
    
    def __init__(self, session: AsyncSession, cache_enabled: bool = True):
        self._session = session
        self._cache_enabled = cache_enabled
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear the in-memory cache."""
        cls._cache.clear()
        cls._cache_loaded = False
    
    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        """Normalize identifier for consistent lookup.
        
        - ISO codes: uppercase
        - Names: lowercase, stripped
        """
        cleaned = identifier.strip()
        # If it looks like an ISO code (2-3 chars, letters only)
        if len(cleaned) <= 3 and cleaned.isalpha():
            return cleaned.upper()
        # Otherwise treat as name
        return cleaned.lower()
    
    @staticmethod
    def _is_iso_code(identifier: str) -> tuple[bool, int]:
        """Check if identifier is an ISO code.
        
        Returns:
            Tuple of (is_iso_code, code_length)
        """
        cleaned = identifier.strip().upper()
        if len(cleaned) == 2 and cleaned.isalpha():
            return (True, 2)
        if len(cleaned) == 3 and cleaned.isalpha():
            return (True, 3)
        return (False, 0)
    
    async def _load_cache(self) -> None:
        """Load all countries into cache for fast lookup."""
        if self._cache_loaded or not self._cache_enabled:
            return
        
        # Query all countries (admin_level = 0)
        stmt = select(
            AdminArea.id,
            AdminArea.iso_a2,
            AdminArea.iso_a3,
            AdminArea.name,
            ST_X(AdminArea.centroid).label("lng"),
            ST_Y(AdminArea.centroid).label("lat"),
        ).where(AdminArea.admin_level == 0)
        
        result = await self._session.execute(stmt)
        rows = result.fetchall()
        
        for row in rows:
            if row.lng is None or row.lat is None:
                continue
                
            lookup_result = AdminAreaLookupResult(
                admin_area_id=row.id,
                iso_a2=row.iso_a2,
                iso_a3=row.iso_a3,
                name=row.name,
                centroid_lng=float(row.lng),
                centroid_lat=float(row.lat),
            )
            
            # Index by all possible identifiers
            if row.iso_a2:
                self._cache[row.iso_a2.upper()] = lookup_result
            if row.iso_a3:
                self._cache[row.iso_a3.upper()] = lookup_result
            if row.name:
                self._cache[row.name.lower()] = lookup_result
        
        self.__class__._cache_loaded = True
    
    async def lookup(self, identifier: str) -> AdminAreaLookupResult | None:
        """Look up a country by ISO code or name.
        
        Args:
            identifier: ISO alpha-2 code (e.g., "KR"), 
                       ISO alpha-3 code (e.g., "KOR"),
                       or country name (e.g., "South Korea")
        
        Returns:
            AdminAreaLookupResult with centroid coordinates, or None if not found
            
        Examples:
            >>> result = await geocoder.lookup("KR")
            >>> result.centroid
            (127.0, 37.5)
            
            >>> result = await geocoder.lookup("United States")
            >>> result.iso_a2
            "US"
        """
        if not identifier or not identifier.strip():
            return None
        
        normalized = self._normalize_identifier(identifier)
        
        # Try cache first
        if self._cache_enabled:
            await self._load_cache()
            if normalized in self._cache:
                return self._cache[normalized]
        
        # Cache miss or cache disabled - query database
        is_iso, code_len = self._is_iso_code(identifier)
        
        if is_iso:
            if code_len == 2:
                stmt = select(
                    AdminArea.id,
                    AdminArea.iso_a2,
                    AdminArea.iso_a3,
                    AdminArea.name,
                    ST_X(AdminArea.centroid).label("lng"),
                    ST_Y(AdminArea.centroid).label("lat"),
                ).where(
                    AdminArea.admin_level == 0,
                    func.upper(AdminArea.iso_a2) == normalized,
                )
            else:  # code_len == 3
                stmt = select(
                    AdminArea.id,
                    AdminArea.iso_a2,
                    AdminArea.iso_a3,
                    AdminArea.name,
                    ST_X(AdminArea.centroid).label("lng"),
                    ST_Y(AdminArea.centroid).label("lat"),
                ).where(
                    AdminArea.admin_level == 0,
                    func.upper(AdminArea.iso_a3) == normalized,
                )
        else:
            # Search by name (case-insensitive)
            stmt = select(
                AdminArea.id,
                AdminArea.iso_a2,
                AdminArea.iso_a3,
                AdminArea.name,
                ST_X(AdminArea.centroid).label("lng"),
                ST_Y(AdminArea.centroid).label("lat"),
            ).where(
                AdminArea.admin_level == 0,
                func.lower(AdminArea.name) == normalized,
            )
        
        result = await self._session.execute(stmt)
        row = result.fetchone()
        
        if not row or row.lng is None or row.lat is None:
            return None
        
        lookup_result = AdminAreaLookupResult(
            admin_area_id=row.id,
            iso_a2=row.iso_a2,
            iso_a3=row.iso_a3,
            name=row.name,
            centroid_lng=float(row.lng),
            centroid_lat=float(row.lat),
        )
        
        # Update cache
        if self._cache_enabled:
            self._cache[normalized] = lookup_result
        
        return lookup_result
    
    async def batch_lookup(
        self, 
        identifiers: list[str],
    ) -> dict[str, AdminAreaLookupResult | None]:
        """Look up multiple countries at once.
        
        More efficient than multiple single lookups when cache is warm.
        
        Args:
            identifiers: List of ISO codes or country names
            
        Returns:
            Dict mapping each identifier to its result (or None if not found)
            
        Example:
            >>> results = await geocoder.batch_lookup(["KR", "US", "Japan"])
            >>> results["KR"].name
            "South Korea"
        """
        # Ensure cache is loaded for efficiency
        if self._cache_enabled:
            await self._load_cache()
        
        results: dict[str, AdminAreaLookupResult | None] = {}
        
        for identifier in identifiers:
            results[identifier] = await self.lookup(identifier)
        
        return results
    
    async def find_by_point(
        self,
        lat: float,
        lng: float,
    ) -> AdminAreaLookupResult | None:
        """Find the country containing a given point.
        
        Uses PostGIS ST_Contains for spatial query.
        
        Args:
            lat: Latitude (WGS84)
            lng: Longitude (WGS84)
            
        Returns:
            AdminAreaLookupResult for the containing country, or None
            
        Example:
            >>> result = await geocoder.find_by_point(lat=37.5665, lng=126.9780)
            >>> result.name
            "South Korea"
        """
        # Create point geometry
        point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
        
        stmt = select(
            AdminArea.id,
            AdminArea.iso_a2,
            AdminArea.iso_a3,
            AdminArea.name,
            ST_X(AdminArea.centroid).label("centroid_lng"),
            ST_Y(AdminArea.centroid).label("centroid_lat"),
        ).where(
            AdminArea.admin_level == 0,
            ST_Contains(AdminArea.geometry, point),
        ).limit(1)
        
        result = await self._session.execute(stmt)
        row = result.fetchone()
        
        if not row:
            return None
        
        # Handle case where centroid might not be set
        centroid_lng = row.centroid_lng if row.centroid_lng is not None else lng
        centroid_lat = row.centroid_lat if row.centroid_lat is not None else lat
        
        return AdminAreaLookupResult(
            admin_area_id=row.id,
            iso_a2=row.iso_a2,
            iso_a3=row.iso_a3,
            name=row.name,
            centroid_lng=float(centroid_lng),
            centroid_lat=float(centroid_lat),
        )
    
    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[AdminAreaLookupResult]:
        """Search countries by partial name match.
        
        Useful for autocomplete functionality.
        
        Args:
            query: Search query (partial name)
            limit: Maximum results to return
            
        Returns:
            List of matching AdminAreaLookupResult objects
        """
        if not query or len(query) < 2:
            return []
        
        # Use ILIKE for case-insensitive partial match
        pattern = f"%{query}%"
        
        stmt = select(
            AdminArea.id,
            AdminArea.iso_a2,
            AdminArea.iso_a3,
            AdminArea.name,
            ST_X(AdminArea.centroid).label("lng"),
            ST_Y(AdminArea.centroid).label("lat"),
        ).where(
            AdminArea.admin_level == 0,
            AdminArea.name.ilike(pattern),
        ).order_by(AdminArea.name).limit(limit)
        
        result = await self._session.execute(stmt)
        rows = result.fetchall()
        
        results = []
        for row in rows:
            if row.lng is None or row.lat is None:
                continue
            results.append(AdminAreaLookupResult(
                admin_area_id=row.id,
                iso_a2=row.iso_a2,
                iso_a3=row.iso_a3,
                name=row.name,
                centroid_lng=float(row.lng),
                centroid_lat=float(row.lat),
            ))
        
        return results


# Convenience function for one-off lookups
async def geocode_country(
    session: AsyncSession,
    identifier: str,
) -> AdminAreaLookupResult | None:
    """Convenience function for single country lookup.
    
    Args:
        session: Database session
        identifier: ISO code or country name
        
    Returns:
        AdminAreaLookupResult or None
    """
    geocoder = CountryGeocoder(session)
    return await geocoder.lookup(identifier)
