# Light Pollution and Sky Quality Feature

---
**Status:** Implemented
**Last Updated:** 2025-12-25
**Implementation:** Light pollution and sky quality features are implemented. API endpoint: `/api/astronomy/light-pollution`
---

## Overview

A comprehensive light pollution and sky quality service that provides Bortle scale classification, Sky Quality Meter (SQM) estimates, and observing recommendations for any location on Earth.

## Features

### 1. Bortle Scale Classification (1-9)

Complete implementation of the Bortle Dark-Sky Scale:

- **Class 1** - Excellent dark sky (SQM 21.7-22.0)
- **Class 2** - Typical dark sky (SQM 21.5-21.7)
- **Class 3** - Rural sky (SQM 21.3-21.5)
- **Class 4** - Rural/suburban transition (SQM 20.4-21.3)
- **Class 5** - Suburban sky (SQM 19.1-20.4)
- **Class 6** - Bright suburban sky (SQM 18.0-19.1)
- **Class 7** - Suburban/urban transition (SQM 18.0-19.0)
- **Class 8** - City sky (SQM 17.0-18.0)
- **Class 9** - Inner city sky (SQM < 17.0)

### 2. Sky Quality Metrics

- **SQM (Sky Quality Meter)** - Brightness in magnitudes per square arcsecond
- **Limiting Magnitude** - Faintest stars visible to naked eye
- **Light Pollution Level** - Negligible, Very Low, Low, Moderate, High, Very High, or Extreme
- **Milky Way Visibility** - Detailed description of Milky Way visibility

### 3. Observing Recommendations

- **Sky Quality Rating** - Exceptional, Excellent, Good, Fair, Poor, or Very Poor
- **Suitable Targets** - List of recommended target types for the conditions
- **Imaging Notes** - Specific recommendations for astrophotography
- **Visual Notes** - Recommendations for visual observation
- **Target Suitability** - Check if specific targets are suitable for conditions

### 4. Data Sources

- **Primary**: lightpollutionmap.info API (uses VIIRS/DMSP satellite data)
- **Fallback**: Location name-based estimation (keywords: "dark sky", "city", "suburb", etc.)
- **Default**: Moderate suburban conditions (Bortle 4-5)

## API Endpoint

### GET `/api/sky-quality/{lat}/{lon}`

Get comprehensive sky quality information for a location.

**Parameters:**
- `lat` (required) - Latitude in decimal degrees
- `lon` (required) - Longitude in decimal degrees
- `location_name` (optional) - Name of the location (query parameter)

**Example Request:**
```bash
curl http://localhost:9247/api/sky-quality/45.9183/-111.5433?location_name=Three%20Forks%2C%20MT
```

**Response:**
```json
{
  "location": {
    "name": "Three Forks, MT",
    "latitude": 45.9183,
    "longitude": -111.5433
  },
  "bortle_class": 3,
  "bortle_name": "Rural sky",
  "sqm_estimate": 21.4,
  "light_pollution_level": "Low",
  "visibility_description": "Some light pollution evident at the horizon. Milky Way still impressive. M15 and M4 visible.",
  "suitable_for": [
    "Deep sky imaging",
    "Galaxies",
    "Nebulae",
    "Globular clusters",
    "Planets",
    "Moon"
  ],
  "limiting_magnitude": 6.6,
  "milky_way_visibility": "Clearly visible with some structure",
  "data_source": "api",
  "recommendations": {
    "sky_quality_rating": "Excellent",
    "best_targets": ["Deep sky imaging", "Galaxies", "Nebulae", "Globular clusters", "Planets", "Moon"],
    "imaging_notes": "Good for deep sky imaging with narrowband filters. Broadband imaging possible but requires careful processing.",
    "visual_notes": "Good for most deep sky objects. Use averted vision for faint targets."
  }
}
```

## Implementation Files

### Service
- **File**: `/backend/app/services/light_pollution_service.py`
- **Class**: `LightPollutionService`
- **Key Methods**:
  - `get_sky_quality(location)` - Main entry point for sky quality data
  - `get_observing_recommendations(sky_quality, target_type)` - Get recommendations
  - `_fetch_sqm_from_api(location)` - Fetch from lightpollutionmap.info
  - `_estimate_sqm(location)` - Fallback estimation
  - `_sqm_to_bortle(sqm)` - Convert SQM to Bortle class

### API Routes
- **File**: `/backend/app/api/routes.py`
- **Endpoint**: `/api/sky-quality/{lat}/{lon}`

### Tests
- **File**: `/backend/tests/test_light_pollution.py`
- **Coverage**: 41 unit tests covering all functionality

## Usage Examples

### Python Service

```python
from app.services.light_pollution_service import LightPollutionService
from app.models import Location

service = LightPollutionService()

# Create location
location = Location(
    name="Cherry Springs State Park",
    latitude=41.6616,
    longitude=-77.8222,
    elevation=700.0,
    timezone="America/New_York"
)

# Get sky quality
sky_quality = service.get_sky_quality(location)

print(f"Bortle Class: {sky_quality.bortle_class}")
print(f"SQM: {sky_quality.sqm_estimate}")
print(f"Suitable for: {', '.join(sky_quality.suitable_for)}")

# Get recommendations
recommendations = service.get_observing_recommendations(sky_quality)
print(f"Rating: {recommendations['sky_quality_rating']}")

# Check target suitability
recommendations = service.get_observing_recommendations(sky_quality, "galaxy")
if recommendations['target_suitable']:
    print("This location is suitable for galaxy imaging!")
```

### JavaScript/Frontend

```javascript
// Fetch sky quality for a location
async function getSkyQuality(lat, lon, locationName) {
  const response = await fetch(
    `/api/sky-quality/${lat}/${lon}?location_name=${encodeURIComponent(locationName)}`
  );
  const data = await response.json();

  console.log(`Bortle Class: ${data.bortle_class}`);
  console.log(`Sky Quality: ${data.recommendations.sky_quality_rating}`);
  console.log(`SQM: ${data.sqm_estimate} mag/arcsec²`);

  return data;
}

// Example usage
getSkyQuality(45.9183, -111.5433, "Three Forks, MT")
  .then(data => {
    // Display to user
    displaySkyQuality(data);
  });
```

## Algorithm Details

### SQM to Bortle Conversion

The service converts Sky Quality Meter readings to Bortle scale classes using the standard ranges:

```python
SQM Range          Bortle Class    Description
≥ 22.0            1               Excellent dark sky
21.5 - 22.0       2               Typical dark sky
21.3 - 21.5       3               Rural sky
20.4 - 21.3       4               Rural/suburban transition
19.1 - 20.4       5               Suburban sky
18.0 - 19.1       6               Bright suburban sky
18.0 - 19.0       7               Suburban/urban transition
17.0 - 18.0       8               City sky
< 17.0            9               Inner city sky
```

### API Data Conversion

When fetching from lightpollutionmap.info API, artificial brightness (in mcd/m²) is converted to SQM using:

```
SQM = 21.58 - 2.5 × log₁₀(brightness)
```

This empirical formula provides realistic SQM values that align with field measurements.

### Fallback Estimation

If API is unavailable, the service estimates SQM based on location name keywords:

- **"dark sky", "park", "wilderness", "mountain"** → SQM 21.0 (Bortle 3)
- **"city", "urban", "downtown"** → SQM 17.5 (Bortle 8)
- **"suburb"** → SQM 19.5 (Bortle 5)
- **Default** → SQM 20.0 (Bortle 4)

## Test Coverage

All functionality is covered by comprehensive unit tests:

- ✅ Bortle scale definitions (complete 1-9)
- ✅ SQM to Bortle conversion accuracy
- ✅ Location-based SQM estimation
- ✅ API integration (with mocking)
- ✅ Fallback handling
- ✅ Sky quality retrieval
- ✅ Recommendation generation
- ✅ Target suitability matching
- ✅ API endpoint functionality
- ✅ Response structure validation

## Integration Points

### Planner Service Integration

The light pollution data can be integrated into the main planner service:

```python
from app.services.light_pollution_service import LightPollutionService

# In planner_service.py
def generate_plan(request: PlanRequest):
    # ... existing code ...

    # Add sky quality info
    lp_service = LightPollutionService()
    sky_quality = lp_service.get_sky_quality(request.location)

    # Filter targets based on light pollution
    suitable_targets = [
        target for target in targets
        if lp_service._is_target_suitable(target.object_type, sky_quality.suitable_for)
    ]

    # Include in plan metadata
    plan.sky_quality_info = {
        "bortle_class": sky_quality.bortle_class,
        "sqm": sky_quality.sqm_estimate,
        "rating": recommendations["sky_quality_rating"]
    }
```

### Frontend Display

Sky quality information can enhance the UI:

- Display Bortle class with color coding
- Show Milky Way visibility icon
- Filter target lists by suitability
- Suggest optimal observing sites
- Warning for poor conditions

## Future Enhancements

1. **Offline Database** - Include offline light pollution data for faster lookups
2. **Time-Based Predictions** - Account for moon phase and twilight
3. **Site Comparison** - Compare multiple locations side-by-side
4. **Weather Integration** - Combine with weather forecast for complete observing conditions
5. **Mobile Integration** - GPS-based automatic location detection
6. **Historical Data** - Track sky quality changes over time
7. **User Contributions** - Allow users to submit actual SQM measurements

## References

- Bortle, J.E. (2001). "Introducing the Bortle Dark-Sky Scale". Sky & Telescope
- Light Pollution Map: https://www.lightpollutionmap.info
- VIIRS/DMSP Satellite Data: NASA/NOAA
- SQM Device: Unihedron Sky Quality Meter

## License

Part of the Astro Planner project.
