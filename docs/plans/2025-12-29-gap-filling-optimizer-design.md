# Gap-Filling Plan Optimizer Design

**Date**: 2025-12-29

**Goal**: Maximize observing session coverage by automatically filling time gaps in generated plans with suitable targets, while maintaining quality standards.

## Overview

When the planner generates an observing session, it often leaves unfilled time gaps between scheduled targets or at the end of the session. This design adds intelligent gap-filling that automatically suggests and inserts targets to maximize coverage, with visual distinction and full user control through undo/swap capabilities.

## User Requirements

- Automatic gap-filling during plan generation (not manual opt-in)
- Auto-filled targets inserted immediately, with alternatives available on demand
- Visual distinction in altitude graph (color + styling)
- Inline interaction - no separate panels or lists
- Undo capability for auto-filled targets
- Catalog sorted by same scheduler score as planner
- Catalog context-aware (tonight vs last plan)

---

## Architecture

### Core Components

**1. Gap Detection Engine**
- Analyzes scheduled plans to identify unfilled time windows
- Categories: quality (45min+), balanced (30min+), quick (15min+) based on planning mode
- Detects gaps between targets and trailing gaps at session end

**2. Gap-Filling Scheduler**
- Extended scheduler with relaxed constraints (0.5 vs 0.6 minimum score)
- Prioritization: (a) scheduler score, (b) gap-fit efficiency, (c) diversity bonus
- Caches top 3 candidates per gap for user alternatives

**3. Catalog Scoring Service**
- Applies scheduler scoring to catalog browsing
- Dual context: "tonight" (default location + current date) vs "last plan" (most recent plan params)
- Exposes context toggle in catalog UI

**4. Plan State Manager**
- Tracks original vs auto-filled targets
- Manages undo operations
- Stores suggestion alternatives for popovers

### Data Flow

```
1. User generates plan
2. Initial scheduler runs → creates base schedule
3. Gap detector identifies unfilled windows
4. Gap-filler runs automatically for gaps ≥ minimum duration
5. Auto-filled targets inserted with metadata
6. Plan rendered with visual distinction
7. User can undo, swap alternatives, or accept as-is
```

---

## Gap-Filling Algorithm

### Gap Detection Logic

```
For each scheduled target in chronological order:
  If gap exists between (previous_target.end_time + slew_time) and current_target.start_time:
    duration = current_target.start_time - (previous_target.end_time + slew_time)
    If duration >= minimum_threshold_for_planning_mode:
      Create gap_record {start_time, end_time, duration, position_in_schedule}

After last scheduled target:
  If time remains before session.imaging_end:
    Create trailing_gap_record
```

### Minimum Gap Thresholds by Planning Mode

- **Quality mode**: 45 minutes
- **Balanced mode**: 30 minutes
- **Quantity mode**: 15 minutes

### Gap-Filling Selection Process

```
For each detected gap:
  1. Find all targets visible during [gap.start_time, gap.end_time]

  2. Exclude already-scheduled targets

  3. Filter by relaxed constraints:
     - Minimum altitude: same as main scheduler
     - Minimum score threshold: 0.5 (vs 0.6 for main scheduler)
     - Minimum visibility duration: gap.duration - 5min buffer

  4. Score each candidate:
     base_score = scheduler_algorithm(visibility + weather + object)
     fit_bonus = +0.1 if target fills ≥ 90% of gap
     diversity_bonus = +0.05 if object_type not in current plan
     total_score = base_score + fit_bonus + diversity_bonus

  5. Select top candidate for auto-fill

  6. Cache top 3 candidates for alternatives

  7. Add to schedule with metadata:
     - is_gap_filler: true
     - gap_index: position
     - alternatives: [candidate2, candidate3]
```

### Constraints

- Gap fillers never overlap with existing scheduled targets
- Respect slew time between targets
- Stop if no candidates meet minimum score (0.5)
- Limit to first 20 gaps to prevent excessive computation

---

## Visual Design & User Interaction

### Altitude Graph Display

**Scheduled Targets (Original):**
- Solid color blocks (existing blue gradient)
- Opacity: 1.0
- No special border

**Auto-filled Gap Targets:**
- Color: Orange/amber (#FF9800)
- Border: 2px dashed rgba(255,152,0,0.8)
- Opacity: 0.85
- Small "auto-fill" badge icon in corner

**Empty Gaps (unfilled or after undo):**
- Hatched/striped region
- Light gray with diagonal lines
- Distinguishable from background

### Timeline Interaction States

**1. Initial State**
- Plan renders with auto-filled targets already inserted
- Visually distinct per above styling

**2. Hover on Auto-filled Target**
- Border glows
- Tooltip: "Auto-filled: [Target Name] • [Duration]min • Score: [X.X]"
- Hint: "Click for alternatives"

**3. Click on Auto-filled Target**
- Popover appears inline showing:
  ```
  Current: [Target Name] (Score: X.X) [Undo]

  Alternatives:
  • [Alt 1 Name] (Score: X.X) [Use This]
  • [Alt 2 Name] (Score: X.X) [Use This]
  ```
- **[Undo]**: Removes gap filler → gap becomes empty
- **[Use This]**: Swaps current filler with selected alternative

**4. Empty Gap Interaction**
- Hover shows: "X min gap • No suitable targets"
- Click shows reason: "Gap too small" or "No targets meet criteria"

### Catalog Context Toggle

**Location**: Catalog header

**Display**:
```
[Tonight ○ Last Plan]
└─ Active context: [Location] • [Date] • [HH:MM - HH:MM]
```

**Behavior**:
- Default: "Tonight" mode (saved location + current date + tonight's dark window)
- After plan generation: automatically switches to "Last Plan" mode
- Toggle persists during session
- Sorting uses scheduler score for selected context

---

## Implementation Details

### Backend API Changes

#### New Data Models

```python
class GapFillStats(BaseModel):
    """Statistics about gap-filling operation."""
    total_gaps_found: int
    gaps_filled: int
    gaps_unfilled: int
    total_gap_time_minutes: int
    filled_gap_time_minutes: int
    unfilled_reasons: List[str]  # e.g., ["No suitable targets", "Gap too small"]

class GapAlternative(BaseModel):
    """Alternative target suggestion for a gap."""
    target: DSOTarget
    score: TargetScore
    duration_minutes: int

class ScheduledTarget(BaseModel):
    # ... existing fields ...
    is_gap_filler: bool = False
    gap_alternatives: Optional[List[GapAlternative]] = None

class ObservingPlan(BaseModel):
    # ... existing fields ...
    gap_fill_stats: Optional[GapFillStats] = None
```

#### Modified Services

**SchedulerService** (`backend/app/services/scheduler_service.py`):
- Add method: `detect_gaps(scheduled_targets, session) -> List[Gap]`
- Add method: `fill_gaps(gaps, targets, location, session, constraints) -> List[ScheduledTarget]`
- Modify: `schedule_session()` to call gap-filling after initial scheduling

**PlannerService** (`backend/app/services/planner_service.py`):
```python
def generate_plan(request: PlanRequest) -> ObservingPlan:
    # ... existing code for initial scheduling ...

    # NEW: Detect and fill gaps
    gaps = self.scheduler.detect_gaps(scheduled_targets, session)
    gap_fillers = self.scheduler.fill_gaps(
        gaps=gaps,
        targets=targets,  # Same candidate pool
        location=request.location,
        session=session,
        constraints=request.constraints,
        weather_forecasts=weather_forecast
    )

    # Merge gap fillers into schedule
    all_scheduled = sorted(scheduled_targets + gap_fillers, key=lambda x: x.start_time)

    # Calculate gap fill stats
    gap_fill_stats = self._calculate_gap_stats(gaps, gap_fillers)

    # Return plan with gap metadata
    plan.scheduled_targets = all_scheduled
    plan.gap_fill_stats = gap_fill_stats
    return plan
```

**CatalogService** (`backend/app/services/catalog_service.py`):
- Add method: `get_scored_targets(context, location, session_info, constraints, limit, offset) -> List[DSOTarget]`
- Uses existing scheduler scoring algorithm
- Returns targets sorted by total_score descending

#### New API Endpoint

```python
@router.get("/targets/scored")
async def get_scored_targets(
    context: str = "tonight",  # "tonight" or "plan"
    plan_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get catalog targets scored and sorted by scheduler algorithm.

    Context modes:
    - "tonight": Use saved location + current date + tonight's dark window
    - "plan": Use parameters from saved plan (requires plan_id)
    """
    if context == "plan" and not plan_id:
        raise HTTPException(400, "plan_id required for 'plan' context")

    # Build session context based on mode
    if context == "tonight":
        settings_service = SettingsService(db)
        location = settings_service.get_location()
        # Calculate tonight's window
        # ...
    else:
        # Load plan and extract context
        # ...

    catalog_service = CatalogService(db)
    scored_targets = catalog_service.get_scored_targets(
        context=context,
        location=location,
        session_info=session_info,
        constraints=constraints,
        limit=limit,
        offset=offset
    )

    return scored_targets
```

### Frontend Changes

**Files to Modify**:
- `frontend/index.html` - Altitude graph rendering + popover interactions
- `frontend/catalog.html` - Context toggle + scored endpoint integration

**Altitude Graph Renderer** (`frontend/index.html`):
```javascript
function renderScheduledTarget(target, graphHeight) {
    const isGapFiller = target.is_gap_filler || false;

    const style = isGapFiller ? {
        backgroundColor: 'rgba(255, 152, 0, 0.85)',
        border: '2px dashed rgba(255, 152, 0, 0.8)',
        cursor: 'pointer'
    } : {
        backgroundColor: 'rgba(100, 126, 234, 1.0)',
        border: '1px solid rgba(100, 126, 234, 1.0)'
    };

    // Render block with appropriate styling
    // Add click handler for gap fillers
    if (isGapFiller) {
        block.addEventListener('click', () => showGapFillerPopover(target));
    }
}
```

**Gap Filler Popover** (`frontend/index.html`):
```javascript
function showGapFillerPopover(target) {
    const alternatives = target.gap_alternatives || [];

    const html = `
        <div class="gap-filler-popover">
            <div class="current">
                <strong>Current:</strong> ${target.target.name}
                (Score: ${target.score.total_score.toFixed(2)})
                <button onclick="undoGapFiller('${target.target.catalog_id}')">Undo</button>
            </div>
            ${alternatives.length > 0 ? `
                <div class="alternatives">
                    <strong>Alternatives:</strong>
                    ${alternatives.map(alt => `
                        <div class="alternative">
                            ${alt.target.name} (Score: ${alt.score.total_score.toFixed(2)})
                            <button onclick="swapGapFiller('${target.target.catalog_id}', '${alt.target.catalog_id}')">
                                Use This
                            </button>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `;

    // Show popover near clicked target
}
```

**Catalog Context Toggle** (`frontend/catalog.html`):
```javascript
let catalogContext = 'tonight';  // or 'plan'
let lastPlanId = null;

function renderContextToggle() {
    return `
        <div class="context-toggle">
            <button onclick="setCatalogContext('tonight')"
                    class="${catalogContext === 'tonight' ? 'active' : ''}">
                Tonight
            </button>
            <button onclick="setCatalogContext('plan')"
                    class="${catalogContext === 'plan' ? 'active' : ''}"
                    ${!lastPlanId ? 'disabled' : ''}>
                Last Plan
            </button>
            <div class="context-info">
                ${getContextDescription()}
            </div>
        </div>
    `;
}

async function loadScoredCatalog() {
    const params = new URLSearchParams({
        context: catalogContext,
        limit: 100,
        offset: currentOffset
    });

    if (catalogContext === 'plan' && lastPlanId) {
        params.append('plan_id', lastPlanId);
    }

    const response = await fetch(`/api/targets/scored?${params}`);
    const targets = await response.json();
    renderCatalog(targets);
}
```

### Performance Considerations

**Timing Impact**:
- Gap-filling adds ~20-30% to plan generation time
- Acceptable tradeoff for better coverage
- Most time spent in ephemeris calculations (already optimized)

**Optimizations**:
- Limit gap-filling to first 20 gaps (prevent runaway computation)
- Reuse weather forecast data from main scheduler
- Cache catalog scoring results for 5 minutes per context
- Pre-filter candidates to magnitude < 12 before scoring

**Resource Limits**:
- Maximum 3 alternatives cached per gap
- Gap detection uses O(n) scan of scheduled targets
- Gap-filling is O(gaps × candidates) but bounded by limits

---

## Testing Strategy

**Unit Tests**:
- Gap detection with various schedules (tight, sparse, no gaps)
- Gap-filling selection with different candidate pools
- Score calculation with fit/diversity bonuses
- Context switching for catalog scoring

**Integration Tests**:
- Full plan generation with gap-filling
- Undo/swap operations maintain schedule integrity
- API endpoints return correct data structure
- Catalog scoring matches scheduler scoring

**UI Tests**:
- Visual distinction renders correctly
- Popover interactions (undo, swap)
- Context toggle updates catalog
- Gap statistics display

**Performance Tests**:
- Plan generation time with/without gap-filling
- Large candidate pools (200+ targets)
- Many small gaps (20+ gaps in session)

---

## Success Metrics

**Functional**:
- Plans achieve ≥ 90% coverage when suitable targets exist
- Gap-filling completes within 3 seconds for typical sessions
- Undo/swap operations work correctly 100% of time

**User Experience**:
- Visual distinction is immediately clear
- Popover interaction is intuitive
- Catalog sorting matches plan scheduling
- No separate panels or confusing UI

**Quality**:
- Gap fillers meet minimum score threshold (0.5)
- Diversity bonus increases object type variety
- Fit bonus minimizes fragmentation

---

## Future Enhancements

**Not in initial scope, but possible later**:
- User-configurable gap-filling aggressiveness
- "Smart diversity" that balances object types across full session
- Multi-night planning with gap-filling across multiple sessions
- Export gap-fill suggestions as separate optional plan
- Machine learning to improve scoring based on actual observation success
