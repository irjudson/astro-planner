# Catalog Browser User Guide

The enhanced catalog browser helps you discover and plan observations of deep sky objects with real-time visibility information and custom plan building.

## Overview

The Catalog Browser is an interactive workspace for exploring the 12,400+ object catalog and building custom observing plans. It shows real-time visibility calculations, smart sorting options, and one-click plan generation.

## Features

### Real-Time Visibility

When you configure your location in Settings, each object card displays:

- **Visibility badge** - Color-coded status indicator:
  - 🟢 Green "Visible" - Currently at good altitude (30-70°)
  - 🔵 Blue "Rising" - Below 30°, getting higher
  - 🟠 Orange "Setting" - Above 70°, descending
  - ⚫ Gray "Below" - Below the horizon

- **Current altitude** - How high the object is right now, with trend arrow (↗ rising, ↘ setting)

- **Best viewing time tonight** - When the object reaches peak altitude during tonight's astronomical dark hours

- **Best viewing months** - Optimal seasons when the object is highest at midnight (based on Right Ascension)

### Custom Plan Building

Build your own observing schedule by selecting objects from the catalog:

1. **Add objects** - Click "Add to Plan" on any catalog card
   - Button changes to "✓ Added" (green, disabled)
   - Object appears as a chip at the top of the page

2. **Manage your list** - Custom plan section shows:
   - Count of selected objects
   - Removable chips (click × to remove)
   - "Clear All" to start over

3. **Generate plan** - Click "Generate Optimized Plan"
   - Uses your location and constraints from Planner settings
   - Optimizes target order by altitude, weather, and field rotation
   - Automatically switches to Planner tab with results
   - Clears custom plan list after successful generation

**Note:** If the Planner tab has an existing plan, you'll see a confirmation dialog before replacing it.

### Smart Sorting

Sort the catalog by multiple criteria:

- **Visibility Tonight** (default when location configured) - Shows objects at optimal altitude right now
- **Brightness** (magnitude) - Brightest objects first (lower magnitude numbers)
- **Size** (angular size) - Largest objects first
- **Name** (alphabetical) - A-Z by catalog ID

Your sort preference is saved between sessions in browser localStorage.

### Search and Filtering

Use the existing filter controls to narrow down objects:

- **Object Type** - Filter by galaxy, nebula, cluster, etc.
- **Magnitude Range** - Set minimum/maximum brightness
- **Constellation** - Filter by constellation (3-letter abbreviation)
- **Search** - Find objects by catalog ID or common name

Filters work in combination with sorting and visibility calculations.

### Object Preview

Click the preview image on any catalog card to open the Aladin Lite viewer:

- DSS survey imagery centered on the object
- Interactive pan and zoom
- Field of view marker showing Seestar S50 FOV (1.27° × 0.71°)
- Quick way to evaluate framing before imaging

## Setup Requirements

### Location Configuration (Required for Visibility)

To see real-time visibility information:

1. Go to the **Settings** tab
2. Configure your observing location:
   - Latitude (degrees, positive north)
   - Longitude (degrees, positive east)
   - Elevation (meters)
   - Timezone (e.g., "America/Denver")
3. Save settings
4. Return to Catalog tab

**Without location configured:**
- Cards show "Set location to see visibility" link (clickable, goes to Settings)
- Catalog defaults to brightness sorting
- Best viewing months still displayed (calculated from RA)

### Browser Requirements

- Modern browser with JavaScript enabled
- localStorage support for saving preferences (optional but recommended)
- Minimum 1024px width for optimal layout

## Usage Tips

### Finding What to Image Tonight

1. **Configure location** in Settings if not already done
2. **Sort by "Visibility Tonight"** - This prioritizes objects at optimal altitude right now
3. **Look for green badges** - "Visible" status means good altitude for imaging
4. **Check "Best time tonight"** - Plan your session around peak times

### Planning Ahead

1. **Use "Best viewing months"** to identify seasonal objects
2. **Filter by object type** to focus on specific targets (e.g., galaxies in spring)
3. **Sort by size** to find objects that fill your FOV well
4. **Build custom plan** with objects across the night for optimal scheduling

### Building Efficient Observing Sessions

1. **Add diverse objects** - Mix different altitudes and positions for flexibility
2. **Include backup targets** - Add more objects than you think you'll image
3. **Generate optimized plan** - Let the planner handle altitude, field rotation, and weather
4. **Review in Planner tab** - Check timeline and adjust constraints if needed

### Browsing Without Location

Even without location configured, you can:
- Browse the full catalog with search and filters
- Sort by brightness, size, or name
- Preview objects with Aladin Lite
- Learn about objects (type, magnitude, size, coordinates)
- See best viewing months (static calculation from RA)

## Keyboard Shortcuts

- **Click chip ×** - Remove object from custom plan
- **Enter in search box** - Submit search query
- **Refresh page** - Updates visibility to current time

## Performance Notes

- Visibility calculations are performed for visible results only (20 objects per page)
- Calculations typically complete in 50-100ms
- Sort preferences and custom plan persist in browser localStorage
- No server-side session required

## Troubleshooting

### "Set location to see visibility" appears

**Cause:** Location not configured in Settings

**Fix:** Go to Settings tab and configure latitude, longitude, elevation, and timezone

### Visibility data seems incorrect

**Cause:** Stale page or wrong timezone

**Fix:**
1. Refresh the page to recalculate for current time
2. Verify timezone is correct in Settings
3. Check latitude/longitude signs (north is positive, west is negative for USA)

### "Add to Plan" button disabled

**Cause:** Location not configured

**Fix:** Set location in Settings first (required for plan generation)

### Custom plan list disappeared after refresh

**Cause:** Browser localStorage not available or disabled

**Fix:**
1. Check browser privacy settings (localStorage must be enabled)
2. Try a different browser
3. Note: Plan list is intentionally cleared after successful plan generation

### Visibility badge colors don't match expectations

**Reference:**
- 🟢 Green: 30-70° altitude
- 🔵 Blue: <30° altitude
- 🟠 Orange: >70° altitude
- ⚫ Gray: Below horizon

Objects transition between states as they rise and set. Refresh page to see current status.

## API Endpoint Reference

The Catalog Browser uses the following API endpoints:

- `GET /api/targets` - List catalog objects with optional visibility
  - `?include_visibility=true` - Add real-time visibility calculations
  - `?sort_by=visibility` - Sort by visibility status and altitude
  - `?object_types=galaxy,nebula` - Filter by object types
  - `?min_magnitude=3.0&max_magnitude=10.0` - Magnitude range
  - `?limit=20&offset=0` - Pagination

- `POST /api/plan` - Generate optimized observing plan
  - Accepts `custom_targets` array of catalog IDs
  - Uses location and constraints from request body

See [API Documentation](API_USAGE.md) for complete endpoint reference.

## Related Features

- **Planner Tab** - Generate and execute observing plans
- **Settings Tab** - Configure location and constraints
- **Object Preview Modal** - Aladin Lite interactive viewer
- **Export Functions** - Download plans in multiple formats (seestar_alp CSV, JSON, etc.)

## Future Enhancements

Planned improvements (not yet implemented):

- Batch add objects by filter (e.g., "Add all visible galaxies")
- Visibility forecast for future dates
- Save/load multiple custom plan lists
- Export custom plan list to CSV/JSON
- Weather-aware object highlighting
- Altitude chart preview on cards

See [Roadmap](../planning/ROADMAP.md) for details.

## See Also

- [User Guide](USAGE.md) - General application usage
- [API Usage](API_USAGE.md) - API endpoints and examples
- [Design Document](../plans/2025-12-27-catalog-browser-enhancement-design.md) - Technical design
- [Implementation Plan](../plans/2025-12-27-catalog-browser-implementation.md) - Development tasks
