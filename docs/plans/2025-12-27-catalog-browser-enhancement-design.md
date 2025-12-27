# Catalog Browser Enhancement Design

**Date:** 2025-12-27
**Status:** Approved for Implementation
**Related Issue:** #5 - Implement frontend catalog browser UI

## Overview

Transform the catalog browser from a reference tool into an interactive planning workspace by adding real-time visibility calculations, custom plan building, and intelligent sorting.

## Goals

1. Show real-time visibility for each catalog object based on user's location
2. Enable building custom observing plans by selecting objects from the catalog
3. Provide intelligent sorting to surface the best objects to image right now
4. Maintain fast performance and graceful degradation when location not configured

## Non-Goals

- Dark mode support (planning done remotely during daytime)
- Advanced scheduling constraints (handled by existing planner service)
- Object detail pages (preview modal already exists)
- User accounts or multi-user support

## Architecture

### Backend Changes

**API Enhancement: `/api/catalog/search`**

Extend existing catalog search endpoint to include visibility calculations:

**New Query Parameters:**
- `include_visibility` (boolean, default: true) - Calculate visibility info
- `sort_by` (string, default: "magnitude") - Sort order: visibility|magnitude|size|name

**New Response Fields (per object):**
```json
{
  "name": "M31",
  "magnitude": 3.4,
  "ra_hours": 0.71,
  "dec_degrees": 41.27,
  "size_arcmin": 190.0,
  "object_type": "galaxy",
  "visibility": {
    "current_altitude": 45.2,
    "current_azimuth": 180.5,
    "status": "visible",
    "best_time_tonight": "2025-12-27T21:30:00-07:00",
    "best_altitude_tonight": 62.5,
    "is_optimal_now": false
  }
}
```

**Visibility Status Values:**
- `visible` - Currently 30-70° altitude
- `rising` - Below 30°, altitude increasing
- `setting` - Above 30°, altitude decreasing
- `below_horizon` - Below horizon

**Implementation Details:**

1. **Location retrieval** - Read from existing settings configuration
   - If no location configured, omit `visibility` field entirely
   - Use existing Location model (lat, lon, elevation, timezone)

2. **Ephemeris calculations** - Reuse existing `EphemerisService`
   - `calculate_position(target, location, time)` - Current altitude/azimuth
   - `calculate_twilight_times(location, date)` - Tonight's observing window
   - NEW: `get_best_viewing_time(target, location, start_time, end_time)` - Find peak altitude

3. **Sorting logic:**
   - `visibility` - Rank by: optimal now > rising > setting > below horizon. Secondary sort by altitude × brightness score
   - `magnitude` - Ascending (current behavior)
   - `size` - Descending (largest first)
   - `name` - Alphabetical by catalog_id

4. **Performance considerations:**
   - Calculate visibility for paginated results only (20 objects at a time)
   - Cache twilight times for the request (same for all objects)
   - Expected overhead: ~50-100ms per request

**Files to modify:**
- `backend/app/api/routes.py` - Enhance `/catalog/search` endpoint
- `backend/app/services/ephemeris_service.py` - Add `get_best_viewing_time()` method
- `backend/app/services/catalog_service.py` - Add sorting logic

### Frontend Changes

**1. Catalog Card Redesign**

Enhanced DSO card layout prioritizing visibility and actions:

```
┌─────────────────────────────────┐
│ [Preview Image - 250px wide]    │
│ (click to open Aladin modal)    │
├─────────────────────────────────┤
│ M31 - Andromeda Galaxy    [🟢]  │ ← Name + visibility badge
│ Galaxy • Mag 3.4 • 3.2° × 1°    │ ← Type, mag, size
├─────────────────────────────────┤
│ 📍 Alt now: 45° (rising)        │ ← Current altitude + trend
│ ⭐ Best: 9:30 PM at 62°         │ ← Peak time tonight
│ 📅 Best months: Oct-Feb         │ ← Static best viewing season
├─────────────────────────────────┤
│ RA: 0.71h  Dec: +41.27°         │ ← Coordinates
├─────────────────────────────────┤
│ [🔭 Preview] [➕ Add to Plan]   │ ← Actions
└─────────────────────────────────┘
```

**Visibility Badges:**
- 🟢 Green "Visible" - Currently 30-70° altitude
- 🔵 Blue "Rising" - Below 30°, altitude increasing
- 🟠 Orange "Setting" - Above 30°, altitude decreasing
- ⚫ Gray "Below" - Below horizon

**When location not configured:**
```
├─────────────────────────────────┤
│ 📍 Set location to see          │ ← Clickable link to Settings
│    visibility →                 │
│ 📅 Best months: Oct-Feb         │ ← Still show static info
├─────────────────────────────────┤
│ [🔭 Preview] [Add to Plan]      │ ← Add button disabled
└─────────────────────────────────┘
```

**Changes from current design:**
- Remove "Best Months" button → Static text in visibility section
- Remove "Details" button → Replaced by "Add to Plan"
- Add visibility section between object info and actions
- "Add to Plan" is primary action (bold, colored)

**2. Custom Plan Builder**

Section appears above catalog results when objects are added:

```
┌─────────────────────────────────────────────────┐
│ 🎯 Your Custom Plan (3 objects)                │
│                                                  │
│ [M31 - Andromeda ×] [M42 - Orion ×] [M81 ×]    │ ← Removable chips
│                                                  │
│ [Generate Optimized Plan] [Clear All]           │ ← Actions
└─────────────────────────────────────────────────┘
```

**Interaction Flow:**

1. **Adding objects:**
   - Click "Add to Plan" on catalog card
   - Card button changes to "✓ Added" (disabled, green)
   - Object appears as chip in plan builder
   - Counter updates "Your Custom Plan (3 objects)"

2. **Removing objects:**
   - Click × on chip to remove
   - Card's "Add to Plan" button re-enables
   - Section hides when empty

3. **Generating plan:**
   - Click "Generate Optimized Plan"
   - If Planner tab has existing plan, show confirmation modal
   - Send custom target list to `/api/plan` endpoint
   - Clear custom plan list
   - Auto-switch to Planner tab
   - Display optimized schedule

**State Management:**
- Store custom plan list in JavaScript array
- Persist to `localStorage` for page refresh
- Clear on successful plan generation

**3. Smart Sorting**

Add sort dropdown in filter section:

```
┌─────────────────────────────────────────┐
│ 🔍 Search & Filter                      │
│ [Search box] [Object Type ▼]            │
│ [Magnitude] [Constellation]             │
│                                          │
│ Sort by: [Visibility Tonight ▼]         │ ← New dropdown
└─────────────────────────────────────────┘
```

**Sort Options:**

1. **Visibility Tonight** (default when location set)
   - Best to image right now
   - Shows optimal altitude objects first

2. **Brightness** (magnitude ascending)
   - Current default behavior
   - Lower magnitude = brighter

3. **Size** (angular size descending)
   - Largest objects first
   - Good for FOV matching

4. **Name** (alphabetical)
   - A-Z by catalog ID
   - Good for lookup

**Smart Default Logic:**
```javascript
if (userLocationConfigured) {
  defaultSort = 'visibility';
} else {
  defaultSort = 'magnitude';
}
```

**Sort Persistence:**
- Remember choice in `localStorage`
- Show indicator: "Sorted by: Visibility Tonight (from Three Forks, MT)"
- Reset to smart default when location changes

**Files to modify:**
- `frontend/index.html` - Catalog tab HTML structure
- `frontend/index.html` - JavaScript functions for plan builder, sorting
- `frontend/styles.css` - Styles for visibility badges, plan builder section

## Error Handling & Edge Cases

### Location Not Configured
- Catalog loads with magnitude sorting
- Cards show "Set location to see visibility →" prompt (clickable, goes to Settings)
- "Add to Plan" button disabled with tooltip "Set location first"
- Sort dropdown hides "Visibility Tonight" option

### Ephemeris Calculation Failures
- If visibility calc fails for an object, omit visibility section
- Log error to console but don't break catalog display
- Fall back to showing basic info (mag, size, coordinates)

### API Timeouts
- Set 5-second timeout for catalog search
- If timeout, show cached results without visibility
- Display banner: "Visibility data unavailable - showing basic catalog"

### Empty Custom Plan
- "Generate Plan" button disabled when no objects added
- Show helper text: "Add objects from catalog below to build your plan"

### Plan Generation Conflicts
- Before replacing plan, check if Planner tab has unsaved changes
- Confirmation modal shows number of targets being replaced
- "Cancel" keeps you in catalog browser with plan list intact

### Invalid Objects in Plan List
- Filter out objects missing required fields (RA/Dec) before sending to planner
- Show warning: "2 of 5 objects skipped (missing coordinates)"

### Browser Compatibility
- `localStorage` not available → Custom plan list resets on refresh (show warning)
- Older browsers without `fetch()` → Graceful degradation to basic catalog

## Testing Strategy

### Backend Tests
- Unit tests for `get_best_viewing_time()` with known objects/locations
- Test visibility calculations at different times of day
- Test sorting algorithms for each sort option
- Test behavior when location not configured

### Frontend Tests
- Test plan builder add/remove workflow
- Test localStorage persistence and recovery
- Test sort dropdown changing and persistence
- Test "Set location" prompt when location missing
- Test confirmation modal on plan generation

### Integration Tests
- End-to-end: Browse catalog → Add objects → Generate plan → View in Planner
- Test with/without location configured
- Test API timeout handling
- Test plan generation with mixed valid/invalid objects

### Manual Testing Checklist
- [ ] Visibility badges show correct colors for different altitudes
- [ ] Current altitude updates when refreshing page
- [ ] Best viewing time matches planner's optimal scheduling
- [ ] Plan builder chips can be added/removed
- [ ] Generate plan creates correct optimized schedule
- [ ] Sorting changes order as expected
- [ ] Location prompt links to Settings correctly
- [ ] Confirmation modal appears when replacing existing plan

## Implementation Plan

### Phase 1: Backend Visibility (Priority 1)
1. Add `get_best_viewing_time()` to `EphemerisService`
2. Enhance `/api/catalog/search` endpoint with visibility calculations
3. Add sorting logic to catalog service
4. Write unit tests for ephemeris calculations

### Phase 2: Frontend Card Redesign (Priority 1)
1. Update catalog card HTML structure
2. Add visibility badge styling (colors for each status)
3. Replace "Best Months" button with static text
4. Replace "Details" button with "Add to Plan"
5. Add "Set location" prompt for missing location

### Phase 3: Custom Plan Builder (Priority 2)
1. Create plan builder section HTML/CSS
2. Implement add/remove object logic
3. Add localStorage persistence
4. Create confirmation modal for plan replacement
5. Implement "Generate Plan" API call and tab switch

### Phase 4: Smart Sorting (Priority 2)
1. Add sort dropdown UI
2. Implement sort persistence in localStorage
3. Add smart default logic
4. Update sort indicator text

### Phase 5: Testing & Polish (Priority 3)
1. Write comprehensive tests
2. Add error handling and edge case coverage
3. Performance optimization if needed
4. Update documentation

## Success Metrics

- Time to build a custom observing plan reduced from ~10 minutes (manual lookup) to <2 minutes (browse + add + generate)
- Visibility calculations complete in <100ms for 20 objects
- 0 errors when location not configured (graceful degradation)
- Custom plan list persists across page refreshes

## Future Enhancements (Not in Scope)

- Batch add objects by filter (e.g., "Add all visible galaxies")
- Visibility forecast for future dates ("Which objects are best next week?")
- Save/load multiple custom plan lists
- Export custom plan list to CSV/JSON
- Integration with weather forecast to highlight best objects given predicted conditions
- Altitude chart preview directly on catalog cards
