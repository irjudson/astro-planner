"""Service for calculating light pollution and Bortle dark-sky scale."""

from typing import Tuple, Optional
from pydantic import BaseModel, field_validator
import requests
import random


class BortleScale:
    """Bortle dark-sky scale classification (1-9)."""
    
    # SQM (Sky Quality Magnitude) ranges for each Bortle class
    SQM_RANGES = {
        1: (21.9, 22.0),   # Excellent dark-sky site
        2: (21.7, 21.8),   # Typical truly dark site
        3: (21.3, 21.6),   # Rural sky
        4: (20.5, 21.2),   # Rural/suburban transition
        5: (19.5, 20.4),   # Suburban sky
        6: (18.5, 19.4),   # Bright suburban sky
        7: (18.0, 18.4),   # Suburban/urban transition
        8: (17.0, 17.9),   # City sky
        9: (13.0, 16.9),   # Inner-city sky
    }
    
    DESCRIPTIONS = {
        1: "Excellent dark-sky site",
        2: "Typical truly dark site",
        3: "Rural sky",
        4: "Rural/suburban transition",
        5: "Suburban sky",
        6: "Bright suburban sky",
        7: "Suburban/urban transition",
        8: "City sky",
        9: "Inner-city sky",
    }
    
    @classmethod
    def from_sqm(cls, sqm: float) -> int:
        """Convert SQM value to Bortle class."""
        for bortle_class, (sqm_min, sqm_max) in cls.SQM_RANGES.items():
            if sqm_min <= sqm <= sqm_max:
                return bortle_class
        # Handle edge cases
        if sqm >= 21.9:
            return 1
        if sqm < 13.0:
            return 9
        # Shouldn't reach here, but default to middle value
        return 5
    
    @classmethod
    def get_description(cls, bortle_class: int) -> str:
        """Get description for Bortle class."""
        return cls.DESCRIPTIONS.get(bortle_class, "Unknown")
    
    @classmethod
    def get_sqm_range(cls, bortle_class: int) -> Tuple[float, float]:
        """Get SQM range for Bortle class."""
        return cls.SQM_RANGES.get(bortle_class, (19.5, 20.4))


class LightPollutionData(BaseModel):
    """Light pollution data for a location."""
    
    latitude: float
    longitude: float
    sqm: float  # Sky Quality Magnitude
    bortle_class: int  # 1-9
    description: str
    source: str  # "lightpollutionmap.info", "estimated", etc.
    
    @field_validator('latitude')
    @classmethod
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v
    
    @field_validator('longitude')
    @classmethod
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v


class LightPollutionService:
    """Service for retrieving and calculating light pollution data."""
    
    def __init__(self):
        """Initialize service."""
        self.api_timeout = 5  # seconds
    
    def get_light_pollution(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[LightPollutionData]:
        """
        Get light pollution data for coordinates.
        
        Tries to fetch from API, falls back to estimation.
        """
        # Try API first
        try:
            return self._fetch_from_api(latitude, longitude)
        except Exception:
            # Fall back to estimation
            pass
        
        # Estimate based on coordinates
        bortle = self._estimate_bortle_from_coordinates(latitude, longitude)
        sqm = self._calculate_sqm_from_bortle(bortle)
        description = BortleScale.get_description(bortle)
        
        return LightPollutionData(
            latitude=latitude,
            longitude=longitude,
            sqm=sqm,
            bortle_class=bortle,
            description=description,
            source="estimated"
        )
    
    def _fetch_from_api(
        self,
        latitude: float,
        longitude: float
    ) -> LightPollutionData:
        """Fetch light pollution data from API."""
        url = f"https://api.lightpollutionmap.info/sqm/{latitude}/{longitude}"
        response = requests.get(url, timeout=self.api_timeout)
        response.raise_for_status()
        
        data = response.json()
        sqm = data['sqm']
        bortle = data.get('bortle') or BortleScale.from_sqm(sqm)
        description = BortleScale.get_description(bortle)
        
        return LightPollutionData(
            latitude=latitude,
            longitude=longitude,
            sqm=sqm,
            bortle_class=bortle,
            description=description,
            source="lightpollutionmap.info"
        )
    
    def _estimate_bortle_from_coordinates(
        self,
        latitude: float,
        longitude: float
    ) -> int:
        """
        Estimate Bortle class based on coordinates.
        
        This is a simple heuristic based on known urban areas.
        In production, you'd use population density or light pollution maps.
        """
        # Known major city coordinates (very rough approximation)
        major_cities = [
            (40.7128, -74.0060),  # NYC
            (34.0522, -118.2437),  # LA
            (41.8781, -87.6298),   # Chicago
            (29.7604, -95.3698),   # Houston
            (33.4484, -112.0740),  # Phoenix
            (39.7392, -104.9903),  # Denver
            (47.6062, -122.3321),  # Seattle
            (37.7749, -122.4194),  # SF
        ]
        
        # Check if near major city (within ~1 degree)
        for city_lat, city_lon in major_cities:
            dist = ((latitude - city_lat)**2 + (longitude - city_lon)**2)**0.5
            if dist < 0.5:  # Very close to city center
                return 8 + min(int((0.5 - dist) * 2), 1)  # 8 or 9
            elif dist < 1.0:  # Near city
                return 7
        
        # Remote locations get darker skies
        # Simple heuristic: more remote = darker
        # This is very rough and should be improved
        return min(4, max(1, int(abs(latitude - 40) / 10) + 1))
    
    def _calculate_sqm_from_bortle(self, bortle_class: int) -> float:
        """Calculate typical SQM value for Bortle class."""
        sqm_min, sqm_max = BortleScale.get_sqm_range(bortle_class)
        # Return midpoint with small random variation
        midpoint = (sqm_min + sqm_max) / 2
        variation = (sqm_max - sqm_min) * 0.3
        return midpoint + random.uniform(-variation, variation)
