# Unified Application Layout Design

**Date:** 2026-01-02
**Status:** Approved for Implementation
**Type:** Complete Rebuild (No Code Reuse)

## Overview

Transform Astro Planner from a multi-tab interface into a unified 3-zone layout based on the Observe View design pattern. This creates a cohesive workflow experience where users flow naturally through discovery → planning → execution → processing stages.

## Current State

The application currently uses five separate tabs:
- Browse Catalog (catalog search and browsing)
- Plan (observation planning)
- Observe (telescope control and imaging)
- Process (image processing)
- Settings (application configuration)

Each tab has its own layout, navigation, and organization, creating a disjointed user experience.

## Target Architecture

### Three-Zone Layout

**Zone 1: Left Sidebar (320px fixed width)**
- Connection panel (pinned at top, always visible)
- Four collapsible workflow sections with nested panels
- Scrollable when content exceeds viewport height

**Zone 2: Main Content Area (flexible width)**
- Context-aware display that changes based on sidebar interactions
- Shows catalog grid, planning results, sky map, live view, processing interface
- No internal tab navigation (except in Execution context)
- Maintains Observe View styling (rounded corners, borders, dark theme)

**Zone 3: Bottom Drawer (toggleable)**
- Context-aware advanced controls
- Content changes based on active workflow
- Settings gear icon for application configuration
- Slides up/down like current Observe View drawer

### Eliminated Elements
- Top navigation bar with tab buttons
- Individual tab containers (`#catalog-tab`, `#planner-tab`, etc.)
- Settings as a separate top-level section

## Sidebar Structure

### Hierarchy

```
.observe-sidebar (320px, scrollable)
├── Connection Panel (pinned, always visible)
│   ├── Device Selection dropdown
│   ├── Connect/Disconnect button
│   ├── Connection status indicator
│   └── Weather Conditions
│       ├── Current conditions (temp, humidity, cloud cover)
│       ├── Forecast summary
│       └── Observability indicator (good/fair/poor)
│
├── Discovery Section (collapsible workflow group)
│   ├── Section header: "DISCOVERY" with expand/collapse
│   ├── Catalog Search Panel (collapsible)
│   │   ├── Search box
│   │   ├── Filter dropdowns (type, constellation, magnitude, etc.)
│   │   └── Sort options
│   └── Custom Plan Builder Panel (collapsible)
│       └── Custom plan creation controls
│
├── Planning Section (collapsible workflow group)
│   ├── Section header: "PLANNING" with expand/collapse
│   ├── Location & Device Panel (collapsible)
│   │   ├── Location inputs (lat/lon/elevation)
│   │   └── Device selection
│   ├── Observing Preferences Panel (collapsible)
│   │   ├── Date/time selection
│   │   ├── Constraints (altitude, moon phase, etc.)
│   │   └── Preferences toggles
│   ├── Mosaic Planning Panel (collapsible)
│   │   ├── Enable mosaic checkbox
│   │   ├── Mosaic pattern (grid size, overlap percentage)
│   │   ├── Panel arrangement visualization
│   │   └── Estimated total time
│   └── Plan Results Panel (collapsible)
│       └── Generated plan summary
│
├── Execution Section (collapsible workflow group)
│   ├── Section header: "EXECUTION" with expand/collapse
│   ├── Execution Controls Panel (collapsible)
│   │   ├── Target selection
│   │   ├── Start/Stop/Pause buttons
│   │   └── Progress indicators
│   ├── Imaging Panel (collapsible)
│   │   ├── Exposure settings
│   │   ├── Filters, gain, etc.
│   │   └── Preview controls
│   ├── Telescope Panel (collapsible)
│   │   ├── RA/Dec coordinates
│   │   ├── Slew controls
│   │   └── Tracking status
│   ├── Hardware Panel (collapsible)
│   │   └── Temperature, dew heater, focuser, etc.
│   └── Info Panel (collapsible)
│       └── Session info, statistics, logs
│
└── Processing Section (collapsible workflow group)
    ├── Section header: "PROCESSING" with expand/collapse
    ├── File Browser Panel (collapsible)
    │   ├── Directory navigation
    │   └── File selection list
    ├── Processing Options Panel (collapsible)
    │   ├── Stack Images button
    │   ├── Stitch Mosaic button
    │   ├── Calibrate button
    │   └── Other processing options
    └── Job Status Panel (collapsible)
        └── Active/recent job status
```

### Interaction Behavior
- Click workflow section header to expand/collapse entire group
- Within expanded sections, each panel can be independently collapsed
- Connection panel cannot be collapsed (always accessible)
- Expanding one workflow section doesn't auto-collapse others

## Main Content Area - Context-Aware Display

The main content area dynamically changes based on user interactions in the sidebar.

### Discovery Context
**Trigger:** User interacts with Catalog Search (types search, changes filters, clicks Search)
**Display:** Catalog grid with item cards in responsive layout
**Content:**
- Catalog stats banner at top (total objects, active filters)
- Catalog item cards in responsive grid
- Pagination controls

### Planning Context
**Trigger:** User clicks "Generate Plan" button in Planning sidebar
**Display:** Planning results
**Content:**
- Plan success banner with date/time
- Weather warnings (if applicable)
- Observation plan summary
- Scheduled targets list with visibility windows
- Export options (PDF, CSV, iCal)

### Execution Context
**Trigger:** Device connects, or user starts execution
**Display:** Multi-view with internal tabs
**Content:**
- **Execution tab** (default): Current target info, progress, timing
- **Library tab**: Image library grid (captured images, updates live)
- **Telemetry tab**: Real-time device status, graphs, diagnostics
- **Live View tab**: Live camera feed from telescope

### Processing Context
**Trigger:** User selects file in File Browser panel
**Display:** Processing workspace
**Content:**
- Selected file preview/details
- Processing output display
- Dual-column layout: Output Files (left) | Recent Jobs (right)

### Initial/Idle State
**Display:** Catalog grid (Discovery context)
**Rationale:** Matches initial sidebar state (Discovery expanded, Catalog Search open)

## Bottom Drawer - Context-Aware Advanced Controls

### Discovery Context Drawer
- **Advanced Filters tab:** Additional catalog filtering options
- **Custom Queries tab:** SQL-like query builder for power users
- **Settings** (gear icon): Application settings

### Planning Context Drawer
- **Constraints tab:** Advanced observability constraints (airmass, moon separation)
- **Optimization tab:** Plan optimization settings (prioritization, target selection)
- **Settings** (gear icon): Application settings

### Execution Context Drawer
- **Advanced Imaging tab:** Stacking and mosaic execution controls, dithering settings
- **System tab:** System diagnostics and controls
- **WiFi tab:** Network configuration
- **Calibration tab:** Calibration frames and settings
- **Hardware tab:** Advanced hardware controls
- **Settings** (gear icon): Application settings

### Processing Context Drawer
- **Processing Parameters tab:** Advanced processing settings (algorithms, thresholds)
- **Batch Operations tab:** Batch processing configuration
- **Settings** (gear icon): Application settings

### Drawer Behavior
- Opens/closes independently of sidebar state
- Remembers open/closed state per context
- Settings gear icon in drawer header provides quick access to app settings
- Drawer content animates/transitions when context changes

## Data Flow & State Management

### Discovery → Planning Flow
- User searches catalog and selects targets
- "Add to Plan" button on catalog cards adds target to planning queue
- Planning Results panel shows selected targets with visibility windows

### Planning → Execution Flow
- Generated plan becomes available in Execution section
- "Start Execution" button in Plan Results loads targets into Execution queue
- Execution Controls panel shows queued targets from plan
- User can start automated execution sequence

### Execution → Processing Flow
- Captured images appear **immediately** in Library tab as they're taken (live updates)
- File Browser panel in Processing section updates in real-time
- "Process Latest" button always available to process most recent capture
- Active session shows live progress (current panel for mosaics, stacking count)
- Background processing can run while execution continues

### Processing → Discovery Flow
- Processed images can be matched back to catalog entries
- "Find in Catalog" button on processed images returns to Discovery context
- Enables comparison of results with catalog data

### Cross-Context State Persistence
- Device connection status persists across all contexts
- Weather updates continuously regardless of active context
- Background jobs (planning calculations, processing tasks) continue while user switches contexts
- Sidebar panel expanded/collapsed states saved per workflow section

### URL/Navigation State
- URL updates to reflect current context (`/#/discovery`, `/#/planning`, `/#/execution`, `/#/processing`)
- Browser back/forward buttons navigate between contexts
- Deep linking supported (can share URL to specific context)

## Visual Styling & Transitions

### Colors & Theme
- Dark background: `#0a0e27`
- Accent cyan: `#00d9ff` (active states, highlights, borders)
- Panel backgrounds: `rgba(255, 255, 255, 0.05)` with 1px borders
- Text: White primary, cyan for interactive elements
- Status colors: Green (good), yellow (warning), red (error)

### Border Radius
- All panels/cards: `8px` rounded corners
- Collapsible panel headers when expanded: `8px 8px 0 0` (rounded top only)
- Collapsible panel headers when collapsed: `8px` (all corners)
- Buttons: `4px`

### Spacing
- Sidebar-to-main gap: `24px`
- Panel spacing within sidebar: `16px`
- Internal padding: `16px` for panels, `12px` for compact elements

### Transitions & Animations

**Context Switching:**
- Main area content fades out (200ms) → new content fades in (200ms)
- Loading spinner during data fetch between contexts

**Sidebar Workflow Sections:**
- Expand/collapse animation: `300ms ease-in-out`
- Height animates smoothly
- Chevron icon rotates (▼ expanded, ▶ collapsed)

**Panel Collapse/Expand:**
- Smooth height transition (same as current Observe View)
- Content inside panels doesn't animate

**Drawer:**
- Slides up/down: `250ms ease-out`
- Content within drawer tabs fades when switching: `150ms`

**Hover Effects:**
- Catalog cards: subtle lift + border glow
- Panel headers: background `rgba(0, 217, 255, 0.1)` (no layout shift)
- Buttons: brightness increase + scale 1.02

## Responsive Behavior

### Desktop (>1200px)
- Full 3-zone layout: 320px sidebar + flexible main + 24px gap
- Drawer can be open simultaneously with sidebar
- All panels visible, smooth scrolling in sidebar

### Tablet/Medium (768px - 1200px)
- Sidebar remains at 320px fixed
- Main area gets smaller but still functional
- Drawer overlays main content when open
- Sidebar workflow sections more likely to be collapsed

### Mobile (<768px)
- **Sidebar becomes slide-out panel** (hidden by default)
- Hamburger menu button (top-left) toggles sidebar visibility
- Sidebar slides in from left, overlays main content
- Main content takes full width when sidebar hidden
- Drawer becomes full-screen modal
- Touch-friendly tap targets (minimum 44px height)

**Sidebar Slide-Out Behavior (Mobile):**
- Backdrop/overlay darkens main content when sidebar open
- Tap backdrop or swipe to close sidebar
- Sidebar retains 320px width (or 90vw, whichever smaller)

**Touch Interactions:**
- Collapsible sections: tap header to toggle
- Catalog cards: tap to select, long-press for actions
- Drawer: swipe down to dismiss

## Error Handling & Edge Cases

### Connection Loss During Execution
- Connection panel shows red "Disconnected" indicator
- Execution pauses automatically
- Modal: "Connection lost. Attempting to reconnect..."
- Auto-reconnect every 5 seconds
- If reconnected: resume from last safe point
- If timeout (60s): prompt user to manually reconnect or cancel

### Weather Deterioration
- Weather panel shows warning indicator (yellow/red)
- If executing: notification "Weather conditions degrading"
- User can: Continue, Pause, or Stop execution
- Critical conditions: auto-pause with alert

### Context Switching with Unsaved Changes
- Form data persists when switching contexts
- Badge on workflow section header indicates "Draft plan"
- Switching back restores unsaved state
- Optional confirmation before switching

### Long-Running Operations
- Planning calculations: Progress indicator in Plan Results panel
- Processing jobs: Real-time progress in Job Status panel + drawer
- Mosaic execution: Progress bar + panel counter ("Panel 3/12")
- All operations can be canceled with confirmation

### Failed Catalog Searches
- No results: "No objects found. Try adjusting filters."
- Network error: "Unable to reach catalog. Check connection." + Retry button

### File Browser Empty State
- "No files found. Capture images in Execution mode."
- "Go to Execution" link button switches context

### Device Not Available
- Connection panel shows disabled device dropdown
- Message: "No devices configured. Add device in Settings."
- Settings gear icon pulsing/highlighted

### Background Job Failures
- Toast notification (non-blocking)
- Error details in relevant status panel
- "Retry" or "View Details" actions

## Implementation Strategy - Clean Rebuild

### Approach: Complete Rebuild (No Code Reuse)

All HTML, CSS, and JavaScript will be written fresh for the unified layout. No code from the old tab system will be migrated.

### Phase 1: New 3-Zone Layout Foundation
- Write new `index.html` from scratch with unified layout structure
- Write new CSS organized by workflow sections
- Create new JavaScript context manager and state system
- No references to old tab system

### Phase 2: Rebuild Each Workflow Section
- **Discovery:** Rebuild catalog search, filters, grid display, pagination
- **Planning:** Rebuild location/device forms, preferences, plan generation, results
- **Execution:** Rebuild device connection, imaging controls, telescope controls, library, live view
- **Processing:** Rebuild file browser, processing options, job status

### Phase 3: Rebuild Supporting Features
- Rebuild all modals (device add, location add, etc.)
- Rebuild settings interface in drawer
- Rebuild weather display for Connection panel
- Rebuild all API integration points

### Phase 4: Feature Parity Verification
Test all functionality:
- Catalog: Search, filter, sort, pagination, custom plans, export
- Planning: Location input, device selection, date/time, constraints, plan generation, export
- Execution: Device connection, target selection, imaging params, telescope control, live view, library, telemetry
- Processing: File browsing, stacking, mosaicing, calibration, batch operations
- Settings: Device management, location management, all app preferences
- Weather: Current conditions, forecasts, alerts

### Phase 5: Replace & Cleanup
- Back up old files
- Deploy new files
- Delete old files completely
- Clean up any backend code that was tab-specific

## Files to Modify

### Complete Rewrites
- `/home/irjudson/Projects/astro-planner/frontend/index.html` - Complete rewrite
- `/home/irjudson/Projects/astro-planner/frontend/astro-planner.css` - Reorganize and cleanup
- `/home/irjudson/Projects/astro-planner/frontend/app.js` - Add context management, remove old tab logic

### Review for Cleanup
- Any JavaScript files with tab-specific logic
- Modal/popup HTML that might be tab-specific

## Initial State

When the application first loads:
- **Connection panel:** Expanded (pinned at top)
- **Discovery section:** Expanded, with Catalog Search panel open
- **Planning/Execution/Processing sections:** Collapsed
- **Main area:** Catalog grid (ready to browse)
- **Drawer:** Closed

## Success Criteria

- All functionality from the old 5-tab system is present
- Users can flow seamlessly through discovery → planning → execution → processing
- Context switching is intuitive and driven by user actions
- Live updates work correctly during execution
- Weather data is always visible and accurate
- All responsive breakpoints work correctly
- No performance regressions
- Clean, maintainable codebase with no legacy cruft
