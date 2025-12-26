# Astronomy Features Documentation

---
**Status:** Partially Implemented
**Last Updated:** 2025-12-25
**Implementation:** Some features described here are planned but not yet implemented. See [ROADMAP.md](docs/planning/ROADMAP.md) for current status.
---

This document describes the comprehensive astronomy tools integrated into the Astro Planner application.

## Overview

The Astro Planner includes five integrated astronomy services that help you plan and optimize your astrophotography sessions:

1. **Light Pollution / Sky Quality Assessment** - Evaluate observing conditions based on location
2. **Astronomy Weather Forecasting** - Get detailed astronomy-specific weather predictions
3. **ISS & Satellite Pass Predictions** - Track satellite passes to avoid or capture them
4. **Best Viewing Months Calculator** - Determine optimal months for specific targets
5. **Caldwell Catalog Integration** - Extended deep sky object catalog

All services are accessible through the **Astronomy** tab in the web interface and via REST API endpoints.

---

## Features

### 1. Light Pollution / Sky Quality

**Purpose:** Assess the quality of your observing location based on light pollution levels.

**What it provides:**
- Bortle Scale classification (1-9)
- SQM (Sky Quality Meter) estimates
- Limiting magnitude predictions
- Milky Way visibility assessment
- Recommended object types for your location

**How to use:**
1. Navigate to the **Astronomy** tab
2. Enter your latitude and longitude
3. Click "Check Sky Quality"

**API Endpoint:**
```
GET /api/sky-quality/{latitude}/{longitude}
```

**Example Response:**
```json
{
  "bortle_class": 4,
  "bortle_name": "Rural/Suburban Transition",
  "sqm_estimate": 20.5,
  "light_pollution_level": "moderate",
  "visibility_description": "Good for most objects",
  "suitable_for": ["galaxies", "nebulae", "clusters"],
  "limiting_magnitude": 5.5,
  "milky_way_visibility": "visible"
}
```

**Quality Ratings:**
- **Bortle 1-2:** Excellent dark sky - ideal for all observations
- **Bortle 3-4:** Good rural sky - suitable for most objects
- **Bortle 5-6:** Suburban sky - bright objects preferred
- **Bortle 7-9:** Urban sky - limited to bright targets

---

### 2. Astronomy Weather Forecasting

**Purpose:** Get detailed weather predictions optimized for astronomical observations.

**What it provides:**
- Cloud cover conditions (clear, mostly clear, partly cloudy, etc.)
- Atmospheric transparency (excellent to poor)
- Astronomical seeing conditions (excellent to poor)
- Temperature and wind speed
- Overall astronomy quality score (0-100%)

**How to use:**
1. Navigate to the **Astronomy** tab
2. Enter your latitude and longitude
3. Click "Get Weather Forecast"
4. View 48-hour forecast with quality scores

**API Endpoint:**
```
GET /api/weather/astronomy?lat={lat}&lon={lon}&hours=48
```

**Example Response:**
```json
{
  "forecast": [
    {
      "time": "2025-11-18T20:00:00",
      "cloud_cover": {
        "range": "0-25%",
        "description": "Clear"
      },
      "transparency": "excellent",
      "seeing": "good",
      "temperature_c": 15.0,
      "wind_speed_kmh": 10.0,
      "astronomy_score": 0.85
    }
  ],
  "location": {"latitude": 40.7, "longitude": -74.0},
  "hours": 48
}
```

**Quality Score Interpretation:**
- **70-100%:** Excellent observing conditions
- **40-69%:** Fair to good conditions
- **0-39%:** Poor conditions, consider postponing

**Scoring Algorithm:**
- Cloud Cover: 40% weight
- Transparency: 35% weight
- Seeing: 25% weight

---

### 3. ISS & Satellite Pass Predictions

**Purpose:** Track International Space Station and satellite passes to avoid streaks in your images or capture satellite transits.

**What it provides:**
- Pass start and end times
- Maximum altitude and azimuth
- Duration in minutes
- Visibility classification (excellent, good, fair, poor)
- Apparent magnitude (brightness)
- Quality score for each pass

**How to use:**
1. Navigate to the **Astronomy** tab
2. Enter your latitude and longitude
3. Set number of days to predict (1-30)
4. Click "Get ISS Passes"

**API Endpoints:**
```
GET /api/satellites/iss?lat={lat}&lon={lon}&days=10
GET /api/satellites/passes?norad_id={id}&lat={lat}&lon={lon}&days=10
```

**Example Response:**
```json
{
  "passes": [
    {
      "satellite_name": "ISS (ZARYA)",
      "start_time": "2025-11-18T19:30:00",
      "end_time": "2025-11-18T19:36:00",
      "max_altitude_deg": 45.0,
      "max_altitude_time": "2025-11-18T19:33:00",
      "start_azimuth_deg": 270.0,
      "end_azimuth_deg": 90.0,
      "visibility": "excellent",
      "magnitude": -3.5,
      "duration_minutes": 6.0,
      "quality_score": 0.75
    }
  ],
  "satellite_name": "ISS (ZARYA)",
  "days": 10
}
```

**Visibility Classifications:**
- **Excellent:** High altitude (>60°), bright magnitude
- **Good:** Medium altitude (40-60°), visible magnitude
- **Fair:** Lower altitude (20-40°), dimmer
- **Poor:** Very low altitude (<20°)

**Use Cases:**
- **Avoid streaks:** Schedule imaging between passes
- **Capture transits:** Image ISS crossing Moon/Sun
- **Time-lapse:** Include visible passes in sequences

---

### 4. Best Viewing Months Calculator

**Purpose:** Determine which months are optimal for observing specific deep sky objects from your location.

**What it provides:**
- Month-by-month visibility ratings
- Estimated hours visible above 20° altitude
- Best observation time for each month
- Viewing notes (altitude, evening visibility, season)
- Summary of best 3 months

**How to use:**
1. Navigate to the **Astronomy** tab
2. Enter your latitude
3. Enter target's Right Ascension (0-24 hours)
4. Enter target's Declination (-90 to +90 degrees)
5. Optionally enter object name
6. Click "Calculate Viewing Months"

**API Endpoints:**
```
GET /api/viewing-months?ra_hours={ra}&dec_degrees={dec}&latitude={lat}
GET /api/viewing-months/summary?ra_hours={ra}&dec_degrees={dec}&latitude={lat}
```

**Example Response:**
```json
{
  "months": [
    {
      "month": 1,
      "month_name": "January",
      "rating": "excellent",
      "rating_value": 5,
      "visibility_hours": 8.5,
      "best_time": "21:00",
      "notes": "Object high in sky, visible in evening hours (Winter)",
      "is_good_month": true
    }
  ],
  "object_name": "M42",
  "coordinates": {"ra_hours": 5.919, "dec_degrees": -5.39}
}
```

**Rating System:**
- **Excellent (5):** High altitude + long visibility + evening hours
- **Good (4):** Good altitude + decent visibility hours
- **Fair (3):** Moderate conditions
- **Poor (2):** Low altitude or short visibility
- **Not Visible (1):** Below horizon

**Calculation Factors:**
- Target altitude at transit
- Hours above minimum altitude (20°)
- Evening vs. late-night visibility
- Seasonal night length

**Example Targets:**
- M42 (Orion Nebula): Best in winter months (Dec-Feb)
- M31 (Andromeda): Best in fall months (Sep-Nov)
- M13 (Hercules Cluster): Best in summer months (Jun-Aug)

---

### 5. Caldwell Catalog

**Purpose:** Extended deep sky object catalog beyond the Messier catalog.

**What it provides:**
- 109 additional deep sky objects
- Object types, magnitudes, sizes
- Right Ascension and Declination
- Constellation information
- Recommended telescopes and exposures

**Integration:**
The Caldwell catalog objects are integrated into the main catalog browser and planning tools. Filter by:
- Object type (galaxy, nebula, cluster, etc.)
- Magnitude range
- Size
- Constellation

**Popular Caldwell Objects:**
- C14 (Double Cluster) - Open cluster pair
- C49 (Rosette Nebula) - Large emission nebula
- C11 (Bubble Nebula) - Emission nebula
- C13 (Iris Nebula) - Reflection nebula

---

## Technical Architecture

### Backend Services

All astronomy services are implemented with comprehensive test coverage:

**Service Layer** (`backend/app/services/`):
- `light_pollution_service.py` - Bortle scale calculations (19 tests)
- `caldwell_service.py` - Caldwell catalog data (12 tests)
- `cleardarksky_service.py` - Weather forecasting (11 tests)
- `satellite_service.py` - ISS/satellite tracking (13 tests)
- `viewing_months_service.py` - Optimal month calculations (16 tests)

**API Layer** (`backend/app/api/astronomy.py`):
- 5 REST endpoints with validation
- Query parameter constraints
- Comprehensive error handling
- 13 API integration tests

**Total Test Coverage:** 84 tests (71 service + 13 API)

### Frontend Integration

**Dashboard** (`frontend/index.html`):
- Astronomy tab with 4 interactive widgets
- Real-time data fetching
- Color-coded quality indicators
- Responsive grid layout
- Shared location inputs

**JavaScript Functions:**
- `loadAstronomyWeather()` - Weather widget
- `loadISSPasses()` - Satellite tracker
- `loadViewingMonths()` - Viewing months calculator
- `loadSkyQuality()` - Sky quality display

---

## Common Use Cases

### Planning a Session

1. **Check Sky Quality** - Verify your location is suitable for your targets
2. **Check Weather** - Confirm good conditions for tonight
3. **Check Satellite Passes** - Plan imaging windows between passes
4. **Check Viewing Months** - Confirm targets are in optimal months

### Target Selection

1. Use **Sky Quality** to determine what object types are visible
2. Use **Viewing Months** to find what's optimal right now
3. Filter Caldwell/Messier catalogs by suitable types
4. Generate observing plan with filtered targets

### Avoiding Issues

**Problem:** ISS streaks in images
**Solution:** Check ISS passes and schedule exposures between them

**Problem:** Poor transparency despite clear skies
**Solution:** Check astronomy weather for transparency ratings

**Problem:** Object too low on horizon
**Solution:** Use viewing months to find better months for that target

---

## API Rate Limits and Caching

**External Services:**
- ClearDarkSky: Cached forecasts (15-minute expiry)
- Satellite data: TLE data refreshed daily
- Light pollution: Data cached per location

**Best Practices:**
- Don't poll weather more than once per 15 minutes
- Cache satellite pass predictions for your location
- Reuse viewing month calculations for same target/location

---

## Future Enhancements

Planned improvements to astronomy features:

1. **Weather Alerts** - Notifications for improving conditions
2. **Target Recommendations** - AI-suggested targets based on conditions
3. **Historical Data** - Track observing conditions over time
4. **Integration with Plans** - Auto-filter targets by current conditions
5. **Moon Phase Integration** - Consider lunar illumination in recommendations
6. **Custom Satellite Tracking** - Add specific satellites by NORAD ID

---

## Troubleshooting

### Weather Not Loading
- Verify latitude/longitude are valid (-90 to +90, -180 to +180)
- Check internet connection for external API access
- Try again in a few minutes if service is temporarily unavailable

### No ISS Passes Found
- ISS may not be visible from your location for several days
- Try increasing the prediction period (up to 30 days)
- Verify your latitude/longitude are correct

### Viewing Months Showing "Not Visible"
- Object may be at declination too far from your latitude
- Check RA/Dec coordinates are correct (RA: 0-24h, Dec: -90 to +90°)
- Some objects never rise above horizon from certain latitudes

### Sky Quality Seems Inaccurate
- Light pollution data may not reflect recent development
- Local conditions (nearby lights) can vary from area averages
- Consider using a physical SQM meter for precise measurements

---

## References

- **Bortle Scale:** John E. Bortle, Sky & Telescope (2001)
- **ClearDarkSky:** Attilla Danko's astronomy weather service
- **TLE Data:** CelesTrak satellite tracking data
- **Caldwell Catalog:** Sir Patrick Caldwell-Moore (1995)

---

## Support

For issues or questions about astronomy features:
1. Check this documentation
2. Review API endpoint documentation at `/api/docs`
3. File issues at the GitHub repository
4. Join community discussions

---

*Last Updated: 2025-11-18*
*Version: 1.0*
