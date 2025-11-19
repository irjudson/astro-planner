"""Service for calculating light pollution and Bortle dark-sky scale."""

from typing import Tuple, Optional, List, Dict
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


class SkyQuality(BaseModel):
    """Complete sky quality information for a location."""

    bortle_class: int
    bortle_name: str
    sqm_estimate: float
    light_pollution_level: str
    visibility_description: str
    suitable_for: List[str]
    limiting_magnitude: float
    milky_way_visibility: str
    light_pollution_source: str


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

    def get_sky_quality(self, location) -> SkyQuality:
        """
        Get comprehensive sky quality information for a location.

        Args:
            location: Location object with latitude and longitude

        Returns:
            SkyQuality object with complete sky quality information
        """
        # Get base light pollution data
        light_pollution = self.get_light_pollution(
            latitude=location.latitude,
            longitude=location.longitude
        )

        # Calculate additional metrics
        limiting_magnitude = self._calculate_limiting_magnitude(light_pollution.bortle_class)
        milky_way_visibility = self._assess_milky_way_visibility(light_pollution.bortle_class)
        light_pollution_level = self._categorize_light_pollution(light_pollution.bortle_class)
        visibility_description = self._get_visibility_description(light_pollution.bortle_class)
        suitable_for = self._get_suitable_object_types(light_pollution.bortle_class)

        return SkyQuality(
            bortle_class=light_pollution.bortle_class,
            bortle_name=light_pollution.description,
            sqm_estimate=light_pollution.sqm,
            light_pollution_level=light_pollution_level,
            visibility_description=visibility_description,
            suitable_for=suitable_for,
            limiting_magnitude=limiting_magnitude,
            milky_way_visibility=milky_way_visibility,
            light_pollution_source=light_pollution.source
        )

    def _calculate_limiting_magnitude(self, bortle_class: int) -> float:
        """Calculate naked-eye limiting magnitude for Bortle class."""
        # Approximate limiting magnitudes for each Bortle class
        limiting_mags = {
            1: 7.6,  # Excellent
            2: 7.1,  # Typical dark
            3: 6.6,  # Rural
            4: 6.1,  # Rural/suburban
            5: 5.6,  # Suburban
            6: 5.1,  # Bright suburban
            7: 4.6,  # Suburban/urban
            8: 4.1,  # City
            9: 3.5,  # Inner city
        }
        return limiting_mags.get(bortle_class, 5.5)

    def _assess_milky_way_visibility(self, bortle_class: int) -> str:
        """Assess Milky Way visibility for Bortle class."""
        if bortle_class <= 2:
            return "spectacular"
        elif bortle_class <= 4:
            return "visible"
        elif bortle_class <= 6:
            return "barely visible"
        else:
            return "not visible"

    def _categorize_light_pollution(self, bortle_class: int) -> str:
        """Categorize light pollution level."""
        if bortle_class <= 2:
            return "minimal"
        elif bortle_class <= 4:
            return "moderate"
        elif bortle_class <= 6:
            return "significant"
        else:
            return "severe"

    def _get_visibility_description(self, bortle_class: int) -> str:
        """Get visibility description for Bortle class."""
        descriptions = {
            1: "Exceptional observing conditions - ideal for all objects",
            2: "Excellent dark sky - suitable for all deep sky work",
            3: "Good rural sky - most objects visible",
            4: "Rural/suburban transition - good for most objects",
            5: "Suburban sky - brighter objects preferred",
            6: "Bright suburban sky - limited to bright objects",
            7: "Suburban/urban transition - very limited",
            8: "City sky - only brightest objects",
            9: "Inner city - severely limited visibility",
        }
        return descriptions.get(bortle_class, "Unknown")

    def _get_suitable_object_types(self, bortle_class: int) -> List[str]:
        """Get suitable object types for observing given Bortle class.

        Returns object types in singular form to match catalog database.
        """
        if bortle_class <= 3:
            # Excellent dark sky - all object types visible
            return ["galaxy", "nebula", "cluster", "planetary_nebula", "planet", "moon", "comet", "asteroid"]
        elif bortle_class <= 5:
            # Suburban sky - brighter objects preferred
            return ["galaxy", "nebula", "cluster", "planetary_nebula", "planet", "moon"]
        elif bortle_class <= 7:
            # Urban/suburban transition - limited to bright objects
            return ["nebula", "cluster", "planet", "moon"]
        else:
            # City sky - severely limited
            return ["planet", "moon"]

    def get_observing_recommendations(self, sky_quality: SkyQuality) -> Dict:
        """
        Get observing recommendations based on sky quality.

        Args:
            sky_quality: SkyQuality object

        Returns:
            Dictionary with recommendations
        """
        recommendations = {
            "overall_rating": self._get_overall_rating(sky_quality.bortle_class),
            "best_for": sky_quality.suitable_for,
            "avoid": self._get_objects_to_avoid(sky_quality.bortle_class),
            "tips": self._get_observing_tips(sky_quality.bortle_class)
        }
        return recommendations

    def _get_overall_rating(self, bortle_class: int) -> str:
        """Get overall observing quality rating."""
        if bortle_class <= 2:
            return "excellent"
        elif bortle_class <= 4:
            return "good"
        elif bortle_class <= 6:
            return "fair"
        else:
            return "poor"

    def _get_objects_to_avoid(self, bortle_class: int) -> List[str]:
        """Get object types that will be difficult to observe."""
        if bortle_class <= 3:
            return []
        elif bortle_class <= 5:
            return ["faint galaxies", "planetary nebulae"]
        elif bortle_class <= 7:
            return ["galaxies", "faint nebulae", "globular clusters"]
        else:
            return ["all deep sky objects except brightest"]

    def _get_observing_tips(self, bortle_class: int) -> List[str]:
        """Get tips for observing at this light pollution level."""
        tips = []

        if bortle_class >= 5:
            tips.append("Use narrowband filters for nebulae")
            tips.append("Focus on planets and the Moon")

        if bortle_class >= 7:
            tips.append("Consider traveling to darker skies for deep sky work")
            tips.append("Double stars can still provide good viewing")

        if bortle_class <= 3:
            tips.append("Excellent conditions for wide-field astrophotography")
            tips.append("Take advantage of the dark skies for faint objects")

        if not tips:
            tips.append("Good all-around observing conditions")

        return tips
