# Astro Planner API Usage Guide

## Catalog Endpoints

### Get Catalog Statistics
Returns comprehensive statistics about the DSO catalog.

```bash
GET /api/catalog/stats
```

**Response:**
```json
{
  "total_objects": 12394,
  "by_type": {
    "galaxy": 10318,
    "cluster": 874,
    "nebula": 157,
    "planetary_nebula": 135,
    "other": 910
  },
  "by_catalog": {
    "NGC": 7586,
    "IC": 4808
  },
  "by_magnitude": {
    "<=5.0 (Very Bright)": 33,
    "5.0-10.0 (Bright)": 359,
    "10.0-15.0 (Moderate)": 7472,
    ">15.0 (Faint)": 3233
  }
}
```

### List Targets with Advanced Filtering
Get a list of DSO targets with powerful filtering options.

```bash
GET /api/targets?[parameters]
```

**Query Parameters:**
- `object_types` (array): Filter by object types (can specify multiple)
  - Values: `galaxy`, `nebula`, `cluster`, `planetary_nebula`, `other`
- `min_magnitude` (float): Minimum magnitude (brighter objects have lower values)
- `max_magnitude` (float): Maximum magnitude (fainter limit)
- `constellation` (string): Filter by constellation (3-letter abbreviation)
- `limit` (int): Maximum results to return (default: 100, max: 1000)
- `offset` (int): Offset for pagination (default: 0)

**Examples:**

Get 20 brightest objects:
```bash
GET /api/targets?limit=20
```

Get bright galaxies (magnitude < 10):
```bash
GET /api/targets?object_types=galaxy&max_magnitude=10&limit=50
```

Get multiple object types (galaxies and nebulae):
```bash
GET /api/targets?object_types=galaxy&object_types=nebula&limit=100
```

Get all objects in Orion constellation:
```bash
GET /api/targets?constellation=Ori&limit=50
```

Pagination example (second page of 50):
```bash
GET /api/targets?limit=50&offset=50
```

**Response:**
```json
[
  {
    "name": "M31",
    "catalog_id": "M31",
    "object_type": "galaxy",
    "ra_hours": 0.712,
    "dec_degrees": 41.269,
    "magnitude": 4.4,
    "size_arcmin": 178.0,
    "description": "Galaxy in And"
  },
  ...
]
```

### Get Specific Target
Retrieve details for a single target by catalog ID.

```bash
GET /api/targets/{catalog_id}
```

**Examples:**
```bash
GET /api/targets/M31          # Andromeda Galaxy
GET /api/targets/NGC7000      # North America Nebula
GET /api/targets/IC405        # Flaming Star Nebula
```

**Response:**
```json
{
  "name": "M31",
  "catalog_id": "M31",
  "object_type": "galaxy",
  "ra_hours": 0.712,
  "dec_degrees": 41.269,
  "magnitude": 4.4,
  "size_arcmin": 178.0,
  "description": "Galaxy in And"
}
```

## Planning Endpoints

### Generate Observing Plan
Create a complete observing plan for a specific date and location.

```bash
POST /api/plan
Content-Type: application/json

{
  "location": {
    "name": "Three Forks, MT",
    "latitude": 45.9183,
    "longitude": -111.5433,
    "elevation": 1234.0,
    "timezone": "America/Denver"
  },
  "observing_date": "2025-11-15",
  "constraints": {
    "min_altitude": 30.0,
    "max_altitude": 90.0,
    "setup_time_minutes": 30,
    "object_types": ["galaxy", "nebula", "cluster", "planetary_nebula"],
    "planning_mode": "balanced"
  }
}
```

### Export Plan
Export an observing plan in various formats.

```bash
POST /api/export?format={format_type}
```

**Formats:**
- `json` - JSON format
- `seestar_plan` - Seestar S50 Plan Mode JSON
- `seestar_alp` - Seestar S50 ALP CSV format
- `text` - Human-readable text
- `csv` - CSV format

## Utility Endpoints

### Health Check
```bash
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "astro-planner-api",
  "version": "1.0.0"
}
```

## Object Types

The catalog includes the following object types:
- `galaxy` - Galaxies (10,318 objects)
- `cluster` - Star clusters, both open and globular (874 objects)
- `nebula` - Emission, reflection, and dark nebulae (157 objects)
- `planetary_nebula` - Planetary nebulae (135 objects)
- `other` - Other deep sky objects (910 objects)

## Constellations

Filter by standard 3-letter IAU constellation abbreviations:
- `And` - Andromeda
- `Ori` - Orion
- `Cyg` - Cygnus
- `Per` - Perseus
- `Cas` - Cassiopeia
- ... (all 88 constellations supported)

## Notes

- All results are sorted by magnitude (brightest first)
- Magnitude scale: Lower values are brighter (e.g., 2.0 is brighter than 10.0)
- Coordinates are in J2000 epoch
- RA is in decimal hours (0-24)
- Dec is in decimal degrees (-90 to +90)
