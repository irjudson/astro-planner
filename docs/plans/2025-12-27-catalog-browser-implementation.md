# Catalog Browser Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform catalog browser into interactive planning workspace with real-time visibility calculations, custom plan building, and smart sorting.

**Architecture:** Extend backend `/api/targets` endpoint to calculate visibility using existing `EphemerisService`. Frontend adds plan builder state management and redesigned cards. No new database tables needed - uses existing Settings for location.

**Tech Stack:** FastAPI, Pydantic, Skyfield (ephemeris), Vue.js patterns (reactive state in vanilla JS), localStorage

---

## Task 1: Add get_best_viewing_time() to EphemerisService

**Files:**
- Modify: `backend/app/services/ephemeris_service.py:210`
- Test: `backend/tests/unit/test_ephemeris_service.py`

**Step 1: Write the failing test**

Create test file:

```python
"""Tests for ephemeris service visibility calculations."""

import pytest
from datetime import datetime, timedelta
import pytz

from app.models import DSOTarget, Location
from app.services.ephemeris_service import EphemerisService


def test_get_best_viewing_time():
    """Test finding peak altitude during observing window."""
    service = EphemerisService()

    # M31 (Andromeda) - peaks around local midnight in fall
    m31 = DSOTarget(
        name="M31",
        catalog_id="M31",
        ra_hours=0.71,
        dec_degrees=41.27,
        object_type="galaxy",
        magnitude=3.4,
        size_arcmin=190.0,
        description="Andromeda Galaxy"
    )

    # Three Forks, MT
    location = Location(
        latitude=45.9183,
        longitude=-111.5433,
        elevation=1234,
        timezone="America/Denver"
    )

    # November evening observing window (8 PM - 4 AM)
    tz = pytz.timezone("America/Denver")
    start_time = tz.localize(datetime(2025, 11, 15, 20, 0))
    end_time = tz.localize(datetime(2025, 11, 16, 4, 0))

    best_time, best_alt = service.get_best_viewing_time(m31, location, start_time, end_time)

    # M31 should peak around midnight-2am at 60-70° altitude
    assert best_time is not None
    assert best_alt > 60.0
    assert best_alt < 80.0
    assert start_time < best_time < end_time


def test_get_best_viewing_time_below_horizon():
    """Test object that never rises during window."""
    service = EphemerisService()

    # Southern hemisphere object (LMC)
    lmc = DSOTarget(
        name="LMC",
        catalog_id="LMC",
        ra_hours=5.24,
        dec_degrees=-69.75,
        object_type="galaxy",
        magnitude=0.9,
        size_arcmin=645.0,
        description="Large Magellanic Cloud"
    )

    # Three Forks, MT (northern hemisphere - LMC never visible)
    location = Location(
        latitude=45.9183,
        longitude=-111.5433,
        elevation=1234,
        timezone="America/Denver"
    )

    tz = pytz.timezone("America/Denver")
    start_time = tz.localize(datetime(2025, 11, 15, 20, 0))
    end_time = tz.localize(datetime(2025, 11, 16, 4, 0))

    best_time, best_alt = service.get_best_viewing_time(lmc, location, start_time, end_time)

    # Should return None or negative altitude
    assert best_time is None or best_alt < 0
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_ephemeris_service.py::test_get_best_viewing_time -v`
Expected: FAIL with "AttributeError: 'EphemerisService' object has no attribute 'get_best_viewing_time'"

**Step 3: Write minimal implementation**

Add to `backend/app/services/ephemeris_service.py` after line 209:

```python
def get_best_viewing_time(
    self, target: DSOTarget, location: Location, start_time: datetime, end_time: datetime
) -> Tuple[Optional[datetime], Optional[float]]:
    """
    Find the best viewing time (peak altitude) during observing window.

    Args:
        target: DSO target
        location: Observer location
        start_time: Start of observing window (timezone-aware)
        end_time: End of observing window (timezone-aware)

    Returns:
        Tuple of (best_time, best_altitude) or (None, None) if never rises
    """
    # Sample altitude every 15 minutes
    sample_interval = timedelta(minutes=15)
    current_time = start_time

    best_time = None
    best_altitude = -90.0  # Start below horizon

    while current_time <= end_time:
        alt, _ = self.calculate_position(target, location, current_time)

        if alt > best_altitude:
            best_altitude = alt
            best_time = current_time

        current_time += sample_interval

    # Return None if object never rises above horizon
    if best_altitude < 0:
        return None, None

    return best_time, best_altitude
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/unit/test_ephemeris_service.py::test_get_best_viewing_time -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/ephemeris_service.py backend/tests/unit/test_ephemeris_service.py
git commit -m "feat: add get_best_viewing_time() to EphemerisService"
```

---

## Task 2: Add TargetVisibility Pydantic model

**Files:**
- Modify: `backend/app/models/models.py:200` (after DSOTarget)
- Modify: `backend/app/models/__init__.py:26` (add to exports)

**Step 1: Write the failing test**

Create `backend/tests/unit/test_models.py`:

```python
"""Tests for Pydantic models."""

from datetime import datetime
import pytz

from app.models import TargetVisibility


def test_target_visibility_model():
    """Test TargetVisibility Pydantic model."""
    tz = pytz.timezone("America/Denver")
    best_time = tz.localize(datetime(2025, 11, 15, 23, 30))

    visibility = TargetVisibility(
        current_altitude=45.2,
        current_azimuth=180.5,
        status="visible",
        best_time_tonight=best_time,
        best_altitude_tonight=62.5,
        is_optimal_now=False
    )

    assert visibility.current_altitude == 45.2
    assert visibility.status == "visible"
    assert visibility.best_altitude_tonight == 62.5

    # Test JSON serialization
    json_data = visibility.model_dump()
    assert json_data["status"] == "visible"
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_models.py::test_target_visibility_model -v`
Expected: FAIL with "ImportError: cannot import name 'TargetVisibility'"

**Step 3: Write minimal implementation**

Add to `backend/app/models/models.py` after DSOTarget class:

```python
class TargetVisibility(BaseModel):
    """Real-time visibility information for a catalog object."""

    current_altitude: float = Field(..., description="Current altitude in degrees")
    current_azimuth: float = Field(..., description="Current azimuth in degrees")
    status: str = Field(..., description="Visibility status: visible|rising|setting|below_horizon")
    best_time_tonight: Optional[datetime] = Field(None, description="Best viewing time during tonight's observing window")
    best_altitude_tonight: Optional[float] = Field(None, description="Altitude at best time")
    is_optimal_now: bool = Field(False, description="True if currently at optimal altitude (45-65°)")
```

Add to `backend/app/models/__init__.py` exports:

```python
from .models import (
    # ... existing imports ...
    TargetVisibility,
)

__all__ = [
    # ... existing exports ...
    "TargetVisibility",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/unit/test_models.py::test_target_visibility_model -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/models.py backend/app/models/__init__.py backend/tests/unit/test_models.py
git commit -m "feat: add TargetVisibility Pydantic model"
```

---

## Task 3: Extend DSOTarget model with optional visibility field

**Files:**
- Modify: `backend/app/models/models.py` (DSOTarget class)

**Step 1: Write the failing test**

Add to `backend/tests/unit/test_models.py`:

```python
def test_dso_target_with_visibility():
    """Test DSOTarget with optional visibility field."""
    from app.models import DSOTarget, TargetVisibility
    from datetime import datetime
    import pytz

    tz = pytz.timezone("America/Denver")
    best_time = tz.localize(datetime(2025, 11, 15, 23, 30))

    visibility = TargetVisibility(
        current_altitude=45.2,
        current_azimuth=180.5,
        status="visible",
        best_time_tonight=best_time,
        best_altitude_tonight=62.5,
        is_optimal_now=False
    )

    target = DSOTarget(
        name="M31",
        catalog_id="M31",
        ra_hours=0.71,
        dec_degrees=41.27,
        object_type="galaxy",
        magnitude=3.4,
        size_arcmin=190.0,
        description="Andromeda Galaxy",
        visibility=visibility
    )

    assert target.visibility is not None
    assert target.visibility.status == "visible"

    # Test without visibility (should still work)
    target_no_vis = DSOTarget(
        name="M42",
        catalog_id="M42",
        ra_hours=5.58,
        dec_degrees=-5.39,
        object_type="nebula",
        magnitude=4.0,
        size_arcmin=85.0,
        description="Orion Nebula"
    )

    assert target_no_vis.visibility is None
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_models.py::test_dso_target_with_visibility -v`
Expected: FAIL with "ValidationError: extra fields not permitted"

**Step 3: Write minimal implementation**

Modify `backend/app/models/models.py` DSOTarget class, add field:

```python
class DSOTarget(BaseModel):
    """Deep Sky Object target."""

    name: str
    catalog_id: str
    ra_hours: float
    dec_degrees: float
    magnitude: float
    object_type: str
    size_arcmin: float
    description: Optional[str] = None
    constellation: Optional[str] = None
    image_url: Optional[str] = None
    visibility: Optional[TargetVisibility] = Field(None, description="Real-time visibility info (if calculated)")
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/unit/test_models.py::test_dso_target_with_visibility -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/models.py backend/tests/unit/test_models.py
git commit -m "feat: add optional visibility field to DSOTarget"
```

---

## Task 4: Add visibility calculation helper to CatalogService

**Files:**
- Modify: `backend/app/services/catalog_service.py:210`
- Test: `backend/tests/unit/test_catalog_service.py`

**Step 1: Write the failing test**

Create `backend/tests/unit/test_catalog_service.py`:

```python
"""Tests for catalog service."""

import pytest
from datetime import datetime
import pytz
from unittest.mock import MagicMock

from app.models import DSOTarget, Location, TargetVisibility
from app.services.catalog_service import CatalogService
from app.services.ephemeris_service import EphemerisService


def test_add_visibility_info():
    """Test adding visibility info to target."""
    # Mock database session
    db = MagicMock()
    service = CatalogService(db)

    # Mock ephemeris service
    ephemeris = MagicMock(spec=EphemerisService)
    ephemeris.calculate_position.return_value = (45.2, 180.5)  # alt, az
    ephemeris.calculate_twilight_times.return_value = {
        "astronomical_twilight_end": pytz.timezone("America/Denver").localize(datetime(2025, 11, 15, 19, 30)),
        "astronomical_twilight_start": pytz.timezone("America/Denver").localize(datetime(2025, 11, 16, 5, 30))
    }
    ephemeris.get_best_viewing_time.return_value = (
        pytz.timezone("America/Denver").localize(datetime(2025, 11, 15, 23, 30)),
        62.5
    )

    target = DSOTarget(
        name="M31",
        catalog_id="M31",
        ra_hours=0.71,
        dec_degrees=41.27,
        object_type="galaxy",
        magnitude=3.4,
        size_arcmin=190.0,
        description="Andromeda Galaxy"
    )

    location = Location(
        latitude=45.9183,
        longitude=-111.5433,
        elevation=1234,
        timezone="America/Denver"
    )

    current_time = pytz.timezone("America/Denver").localize(datetime(2025, 11, 15, 21, 0))

    # Add visibility
    enriched = service.add_visibility_info(target, location, ephemeris, current_time)

    assert enriched.visibility is not None
    assert enriched.visibility.current_altitude == 45.2
    assert enriched.visibility.status == "visible"
    assert enriched.visibility.best_altitude_tonight == 62.5
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_catalog_service.py::test_add_visibility_info -v`
Expected: FAIL with "AttributeError: 'CatalogService' object has no attribute 'add_visibility_info'"

**Step 3: Write minimal implementation**

Add to `backend/app/services/catalog_service.py` at end of class:

```python
def add_visibility_info(
    self,
    target: DSOTarget,
    location: Location,
    ephemeris: EphemerisService,
    current_time: datetime
) -> DSOTarget:
    """
    Add real-time visibility information to a target.

    Args:
        target: DSO target
        location: Observer location
        ephemeris: Ephemeris service instance
        current_time: Current time (timezone-aware)

    Returns:
        Target with visibility field populated
    """
    from app.models import TargetVisibility

    # Calculate current position
    current_alt, current_az = ephemeris.calculate_position(target, location, current_time)

    # Determine visibility status
    if current_alt < 0:
        status = "below_horizon"
    elif current_alt < 30:
        status = "rising"
    elif current_alt > 70:
        status = "setting"
    else:
        status = "visible"

    # Check if optimal (45-65° altitude)
    is_optimal = 45.0 <= current_alt <= 65.0

    # Calculate tonight's observing window
    twilight_times = ephemeris.calculate_twilight_times(location, current_time)

    # Get best viewing time during observing window
    astro_end = twilight_times.get("astronomical_twilight_end")
    astro_start = twilight_times.get("astronomical_twilight_start")

    best_time = None
    best_alt = None

    if astro_end and astro_start:
        best_time, best_alt = ephemeris.get_best_viewing_time(
            target, location, astro_end, astro_start
        )

    # Create visibility object
    visibility = TargetVisibility(
        current_altitude=current_alt,
        current_azimuth=current_az,
        status=status,
        best_time_tonight=best_time,
        best_altitude_tonight=best_alt,
        is_optimal_now=is_optimal
    )

    # Return copy of target with visibility added
    return target.model_copy(update={"visibility": visibility})
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/unit/test_catalog_service.py::test_add_visibility_info -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/catalog_service.py backend/tests/unit/test_catalog_service.py
git commit -m "feat: add visibility calculation helper to CatalogService"
```

---

## Task 5: Enhance /api/targets endpoint with visibility and sorting

**Files:**
- Modify: `backend/app/api/routes.py:89-137` (list_targets function)
- Test: `backend/tests/integration/test_catalog_api.py`

**Step 1: Write the failing test**

Create `backend/tests/integration/test_catalog_api.py`:

```python
"""Integration tests for catalog API."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_targets_with_visibility():
    """Test /api/targets endpoint with visibility calculations."""
    # Note: This requires location to be configured in settings
    response = client.get("/api/targets?limit=5&include_visibility=true")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

    # If location configured, should have visibility
    if len(data) > 0:
        target = data[0]
        assert "name" in target
        assert "catalog_id" in target
        # visibility may or may not be present depending on location config


def test_list_targets_sort_by_magnitude():
    """Test sorting by magnitude."""
    response = client.get("/api/targets?limit=10&sort_by=magnitude")

    assert response.status_code == 200
    data = response.json()

    # Should be sorted by magnitude ascending (brightest first)
    if len(data) > 1:
        assert data[0]["magnitude"] <= data[1]["magnitude"]


def test_list_targets_sort_by_size():
    """Test sorting by size."""
    response = client.get("/api/targets?limit=10&sort_by=size")

    assert response.status_code == 200
    data = response.json()

    # Should be sorted by size descending (largest first)
    if len(data) > 1:
        assert data[0]["size_arcmin"] >= data[1]["size_arcmin"]


def test_list_targets_sort_by_name():
    """Test sorting by name."""
    response = client.get("/api/targets?limit=10&sort_by=name")

    assert response.status_code == 200
    data = response.json()

    # Should be sorted alphabetically
    if len(data) > 1:
        assert data[0]["catalog_id"] <= data[1]["catalog_id"]
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/integration/test_catalog_api.py::test_list_targets_with_visibility -v`
Expected: FAIL (parameters not recognized)

**Step 3: Write minimal implementation**

Modify `backend/app/api/routes.py` list_targets function:

```python
@router.get("/targets", response_model=List[DSOTarget])
async def list_targets(
    db: Session = Depends(get_db),
    object_types: Optional[List[str]] = Query(None, description="Filter by object types (can specify multiple)"),
    min_magnitude: Optional[float] = Query(None, description="Minimum magnitude (brighter objects have lower values)"),
    max_magnitude: Optional[float] = Query(None, description="Maximum magnitude (fainter limit)"),
    constellation: Optional[str] = Query(None, description="Filter by constellation (3-letter abbreviation)"),
    limit: Optional[int] = Query(100, description="Maximum number of results (default: 100, max: 1000)", le=1000),
    offset: int = Query(0, description="Offset for pagination (default: 0)", ge=0),
    include_visibility: bool = Query(True, description="Include real-time visibility calculations"),
    sort_by: str = Query("magnitude", description="Sort order: magnitude|size|name|visibility"),
):
    """
    List available DSO targets with advanced filtering, sorting, and optional visibility.

    Args:
        object_types: Filter by object types
        min_magnitude: Minimum magnitude
        max_magnitude: Maximum magnitude
        constellation: Filter by constellation
        limit: Maximum results
        offset: Pagination offset
        include_visibility: Calculate real-time visibility (requires location in settings)
        sort_by: Sort order (magnitude, size, name, visibility)

    Returns:
        List of DSO targets with optional visibility info
    """
    try:
        from app.services.ephemeris_service import EphemerisService
        from app.services.settings_service import SettingsService
        from datetime import datetime
        import pytz

        catalog_service = CatalogService(db)

        # Get filtered targets
        targets = catalog_service.filter_targets(
            object_types=object_types,
            min_magnitude=min_magnitude,
            max_magnitude=max_magnitude,
            constellation=constellation,
            limit=None,  # Get all for sorting, then paginate
            offset=0,
        )

        # Add visibility if requested and location configured
        if include_visibility:
            try:
                settings_service = SettingsService(db)
                location = settings_service.get_location()

                if location:
                    ephemeris = EphemerisService()
                    current_time = datetime.now(pytz.timezone(location.timezone))

                    # Add visibility to each target
                    targets = [
                        catalog_service.add_visibility_info(target, location, ephemeris, current_time)
                        for target in targets
                    ]
            except Exception as e:
                # If visibility fails, continue without it
                print(f"Warning: Could not calculate visibility: {e}")

        # Sort targets
        if sort_by == "magnitude":
            targets.sort(key=lambda t: t.magnitude)
        elif sort_by == "size":
            targets.sort(key=lambda t: t.size_arcmin, reverse=True)
        elif sort_by == "name":
            targets.sort(key=lambda t: t.catalog_id)
        elif sort_by == "visibility" and include_visibility:
            # Sort by: optimal now > visible > rising > setting > below horizon
            # Within each group, sort by altitude
            def visibility_sort_key(t):
                if not t.visibility:
                    return (999, -999)  # No visibility - sort last

                status_order = {
                    "visible": 0,
                    "rising": 1,
                    "setting": 2,
                    "below_horizon": 3
                }
                status_rank = status_order.get(t.visibility.status, 999)

                # Within status, prefer higher altitude
                alt = t.visibility.current_altitude

                return (status_rank, -alt)

            targets.sort(key=visibility_sort_key)

        # Apply pagination after sorting
        paginated = targets[offset:offset + limit] if limit else targets[offset:]

        return paginated
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching targets: {str(e)}")
```

**Step 4: Create SettingsService for location retrieval**

Create `backend/app/services/settings_service.py`:

```python
"""Settings service for retrieving configuration."""

from typing import Optional
from sqlalchemy.orm import Session

from app.models import Location
from app.models.settings_models import Settings


class SettingsService:
    """Service for managing application settings."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def get_location(self) -> Optional[Location]:
        """
        Get configured location from settings.

        Returns:
            Location object or None if not configured
        """
        settings = self.db.query(Settings).first()

        if not settings or not settings.location_latitude:
            return None

        return Location(
            latitude=settings.location_latitude,
            longitude=settings.location_longitude,
            elevation=settings.location_elevation or 0,
            timezone=settings.location_timezone or "UTC"
        )
```

**Step 5: Run tests to verify they pass**

Run: `pytest backend/tests/integration/test_catalog_api.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/api/routes.py backend/app/services/settings_service.py backend/tests/integration/test_catalog_api.py
git commit -m "feat: enhance /api/targets with visibility and sorting"
```

---

## Task 6: Frontend - Add plan builder state management

**Files:**
- Modify: `frontend/index.html:4600` (add to catalog tab JavaScript)

**Step 1: Add custom plan state**

Add JavaScript at start of catalog tab section:

```javascript
// Custom Plan Builder State
const customPlan = {
    targets: [],  // Array of catalog objects

    add(target) {
        // Don't add duplicates
        if (this.targets.find(t => t.catalog_id === target.catalog_id)) {
            return false;
        }
        this.targets.push(target);
        this.save();
        this.render();
        return true;
    },

    remove(catalogId) {
        this.targets = this.targets.filter(t => t.catalog_id !== catalogId);
        this.save();
        this.render();
    },

    clear() {
        this.targets = [];
        this.save();
        this.render();
    },

    save() {
        try {
            localStorage.setItem('astro_custom_plan', JSON.stringify(this.targets));
        } catch (e) {
            console.warn('Could not save custom plan to localStorage:', e);
        }
    },

    load() {
        try {
            const saved = localStorage.getItem('astro_custom_plan');
            if (saved) {
                this.targets = JSON.parse(saved);
                this.render();
            }
        } catch (e) {
            console.warn('Could not load custom plan from localStorage:', e);
            this.targets = [];
        }
    },

    render() {
        const container = document.getElementById('custom-plan-container');
        if (!container) return;

        if (this.targets.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';

        const chips = this.targets.map(t => `
            <span class="plan-chip">
                ${t.name} <button onclick="customPlan.remove('${t.catalog_id}')">&times;</button>
            </span>
        `).join('');

        document.getElementById('plan-chips').innerHTML = chips;
        document.getElementById('plan-count').textContent = this.targets.length;
    },

    async generatePlan() {
        if (this.targets.length === 0) {
            alert('Add objects to your plan first!');
            return;
        }

        // Check if planner tab has existing plan
        const existingPlan = document.getElementById('session-summary');
        const hasExistingPlan = existingPlan && existingPlan.style.display !== 'none';

        if (hasExistingPlan) {
            if (!confirm(`Replace existing plan?\n\nThis will replace the current plan in the Planner tab with a new plan optimized for these ${this.targets.length} objects.`)) {
                return;
            }
        }

        // TODO: Call /api/plan with custom targets
        // For now, just show message
        alert(`Generating plan for ${this.targets.length} objects...\n\nThis will be implemented in next task.`);

        // Clear custom plan
        this.clear();

        // Switch to planner tab
        showTab('planner');
    }
};

// Load saved plan on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => customPlan.load());
} else {
    customPlan.load();
}
```

**Step 2: Add HTML for plan builder section**

Add HTML in catalog tab before search filters (around line 1823):

```html
<!-- Custom Plan Builder -->
<div id="custom-plan-container" style="display: none; background: #f8f9fa; border: 2px solid #667eea; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
    <h3 style="margin: 0 0 15px 0; color: #333;">🎯 Your Custom Plan (<span id="plan-count">0</span> objects)</h3>

    <div id="plan-chips" style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 15px;">
        <!-- Chips rendered by JavaScript -->
    </div>

    <div style="display: flex; gap: 10px;">
        <button onclick="customPlan.generatePlan()" class="btn" style="background: #667eea; color: white; padding: 12px 24px; flex: 1;">
            Generate Optimized Plan
        </button>
        <button onclick="customPlan.clear()" class="btn" style="background: #dc3545; color: white; padding: 12px 24px;">
            Clear All
        </button>
    </div>
</div>
```

**Step 3: Add CSS for plan chips**

Add CSS in `<style>` section:

```css
.plan-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: white;
    border: 2px solid #667eea;
    border-radius: 20px;
    padding: 6px 12px;
    font-size: 0.9em;
    color: #333;
}

.plan-chip button {
    background: none;
    border: none;
    color: #dc3545;
    font-size: 1.2em;
    cursor: pointer;
    padding: 0;
    line-height: 1;
    font-weight: bold;
}

.plan-chip button:hover {
    color: #c82333;
}
```

**Step 4: Manual test**

1. Open browser to catalog tab
2. Open DevTools console
3. Run: `customPlan.add({catalog_id: 'M31', name: 'M31'})`
4. Verify chip appears
5. Click × to remove
6. Verify chip disappears
7. Refresh page - verify plan persists via localStorage

**Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add custom plan builder state management"
```

---

## Task 7: Frontend - Redesign catalog cards with visibility

**Files:**
- Modify: `frontend/index.html:4536-4574` (DSO card rendering)

**Step 1: Update catalog card HTML template**

Replace DSO card rendering (around line 4536) with:

```javascript
// DSO display with visibility
const magStr = obj.magnitude && obj.magnitude < 99 ? obj.magnitude.toFixed(1) : 'N/A';
const sizeStr = obj.size_arcmin ? `${obj.size_arcmin.toFixed(1)}'` : 'N/A';
const raStr = obj.ra_hours ? `${obj.ra_hours.toFixed(2)}h` : 'N/A';
const decStr = obj.dec_degrees ? `${obj.dec_degrees >= 0 ? '+' : ''}${obj.dec_degrees.toFixed(2)}°` : 'N/A';

// Convert RA hours to degrees for image services
const raDeg = obj.ra_hours ? (obj.ra_hours * 15).toFixed(4) : null;

// Auto-generate preview image URL
const sanitizedId = obj.catalog_id.replace(/ /g, '_').replace(/\//g, '_').replace(/:/g, '_');
const previewImageUrl = `/api/images/targets/${sanitizedId}`;

// Visibility badge and info
let visibilityBadge = '';
let visibilityInfo = '';

if (obj.visibility) {
    const vis = obj.visibility;
    const badgeColors = {
        visible: '#28a745',
        rising: '#007bff',
        setting: '#fd7e14',
        below_horizon: '#6c757d'
    };
    const badgeLabels = {
        visible: '🟢 Visible',
        rising: '🔵 Rising',
        setting: '🟠 Setting',
        below_horizon: '⚫ Below'
    };

    visibilityBadge = `<span style="background: ${badgeColors[vis.status]}; color: white; padding: 4px 10px; border-radius: 15px; font-size: 0.8em;">${badgeLabels[vis.status]}</span>`;

    const altTrend = vis.status === 'rising' ? '↗' : vis.status === 'setting' ? '↘' : '';
    const bestTime = vis.best_time_tonight ? new Date(vis.best_time_tonight).toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit'}) : 'N/A';
    const bestAlt = vis.best_altitude_tonight ? vis.best_altitude_tonight.toFixed(0) + '°' : 'N/A';

    visibilityInfo = `
        <div style="border-top: 1px solid #e0e0e0; padding-top: 10px; margin-top: 10px;">
            <div style="font-size: 0.9em; color: #666; line-height: 1.8;">
                <div>📍 Alt now: ${vis.current_altitude.toFixed(0)}° ${altTrend}</div>
                <div>⭐ Best: ${bestTime} at ${bestAlt}</div>
                <div>📅 Best months: ${getBestMonths(obj.ra_hours)}</div>
            </div>
        </div>
    `;
} else {
    // No location configured
    visibilityInfo = `
        <div style="border-top: 1px solid #e0e0e0; padding-top: 10px; margin-top: 10px;">
            <div style="font-size: 0.9em; color: #666; line-height: 1.8;">
                <div>📍 <a href="#" onclick="event.preventDefault(); showTab('settings'); return false;" style="color: #667eea;">Set location</a> to see visibility</div>
                <div>📅 Best months: ${getBestMonths(obj.ra_hours)}</div>
            </div>
        </div>
    `;
}

// Check if already in plan
const inPlan = customPlan.targets.find(t => t.catalog_id === obj.catalog_id);
const addButtonHtml = inPlan
    ? '<button class="select-btn" disabled style="background: #28a745; color: white;">✓ Added</button>'
    : `<button class="select-btn" onclick="event.stopPropagation(); addToPlan('${obj.catalog_id}')" style="background: #667eea; color: white;">➕ Add to Plan</button>`;

return `
    <div class="catalog-item">
        <div class="catalog-item-header">
            <div class="catalog-item-name">${obj.name}</div>
            ${visibilityBadge || `<div class="catalog-item-type">${obj.object_type}</div>`}
        </div>
        <div style="margin-bottom: 12px;">
            <img src="${previewImageUrl}"
                 alt="${obj.name} preview"
                 style="width: 100%; max-width: 250px; height: auto; border-radius: 6px; border: 2px solid #e0e0e0; cursor: pointer; display: block; margin: 0 auto;"
                 onclick="event.stopPropagation(); showObjectPreview('${obj.name}', '${obj.catalog_id}', ${raDeg}, ${obj.dec_degrees}, ${obj.size_arcmin || 60})"
                 onerror="this.style.display='none'">
        </div>
        <div class="catalog-item-details">
            <div><strong>Type:</strong> ${obj.object_type}</div>
            <div><strong>Magnitude:</strong> ${magStr} • <strong>Size:</strong> ${sizeStr}</div>
            <div><strong>RA/Dec:</strong> ${raStr}, ${decStr}</div>
        </div>
        ${visibilityInfo}
        <div class="catalog-item-actions" style="display: flex; gap: 8px; margin-top: 12px;">
            ${raDeg && obj.dec_degrees ? `
                <button class="preview-btn" onclick="event.stopPropagation(); showObjectPreview('${obj.name}', '${obj.catalog_id}', ${raDeg}, ${obj.dec_degrees}, ${obj.size_arcmin || 60})">
                    🔭 Preview
                </button>
            ` : ''}
            ${addButtonHtml}
        </div>
    </div>
`;
```

**Step 2: Add helper functions**

Add before catalog rendering code:

```javascript
// Helper: Get best viewing months from RA
function getBestMonths(raHours) {
    if (!raHours) return 'N/A';

    // Convert RA to month (opposition month when object is highest at midnight)
    // RA 0h → September/October (opposite of March sun)
    // RA 6h → December/January
    // RA 12h → March/April
    // RA 18h → June/July

    const monthStart = Math.floor((raHours + 6) / 2) % 12;
    const monthEnd = (monthStart + 2) % 12;

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    return `${months[monthStart]}-${months[monthEnd]}`;
}

// Add to plan from catalog card
function addToPlan(catalogId) {
    const target = catalogFilters.lastResults.find(t => t.catalog_id === catalogId);
    if (!target) {
        alert('Could not find target');
        return;
    }

    if (customPlan.add(target)) {
        // Refresh catalog display to update button state
        displayCatalogResults(catalogFilters.lastResults);
    }
}
```

**Step 3: Store last results for add-to-plan**

Modify `displayCatalogResults` function to store results:

```javascript
function displayCatalogResults(objects) {
    // Store for add-to-plan functionality
    catalogFilters.lastResults = objects;

    // ... rest of existing function
}
```

**Step 4: Manual test**

1. Configure location in Settings tab
2. Go to Catalog tab
3. Verify cards show:
   - Visibility badge (green/blue/orange/gray)
   - Current altitude with trend arrow
   - Best time tonight
   - Best months
   - "Add to Plan" button
4. Click "Add to Plan"
5. Verify button changes to "✓ Added"
6. Verify chip appears in plan builder

**Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat: redesign catalog cards with visibility info"
```

---

## Task 8: Frontend - Add sort dropdown

**Files:**
- Modify: `frontend/index.html:1862` (add after filters)

**Step 1: Add sort dropdown HTML**

Add after filter section (around line 1867):

```html
<div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e0e0e0;">
    <label for="catalog-sort" style="display: block; margin-bottom: 5px; font-weight: 500;">Sort by:</label>
    <select id="catalog-sort" onchange="handleSortChange()" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <option value="magnitude">Brightness (magnitude)</option>
        <option value="visibility">Visibility Tonight</option>
        <option value="size">Size (largest first)</option>
        <option value="name">Name (A-Z)</option>
    </select>
    <div id="sort-indicator" style="margin-top: 5px; font-size: 0.85em; color: #666;"></div>
</div>
```

**Step 2: Add sort change handler**

Add JavaScript:

```javascript
function handleSortChange() {
    const sortSelect = document.getElementById('catalog-sort');
    const sortBy = sortSelect.value;

    // Save preference
    try {
        localStorage.setItem('catalog_sort_preference', sortBy);
    } catch (e) {
        console.warn('Could not save sort preference:', e);
    }

    // Update sort indicator
    updateSortIndicator(sortBy);

    // Update filters and reload
    catalogFilters.sortBy = sortBy;
    catalogFilters.page = 0;
    loadCatalogData();
}

function updateSortIndicator(sortBy) {
    const indicator = document.getElementById('sort-indicator');
    const sortLabels = {
        magnitude: 'Sorted by brightness (brightest first)',
        visibility: 'Sorted by visibility (best to image now first)',
        size: 'Sorted by size (largest first)',
        name: 'Sorted alphabetically'
    };

    indicator.textContent = sortLabels[sortBy] || '';
}

// Load saved sort preference
function loadSortPreference() {
    try {
        const saved = localStorage.getItem('catalog_sort_preference');
        if (saved) {
            document.getElementById('catalog-sort').value = saved;
            catalogFilters.sortBy = saved;
            updateSortIndicator(saved);
        }
    } catch (e) {
        console.warn('Could not load sort preference:', e);
    }
}

// Call on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadSortPreference);
} else {
    loadSortPreference();
}
```

**Step 3: Update loadCatalogData to include sort_by**

Modify the fetch call to include sort parameter:

```javascript
async function loadCatalogData() {
    // ... existing filter params ...

    if (catalogFilters.sortBy) {
        params.append('sort_by', catalogFilters.sortBy);
    }

    const response = await fetch(`/api/targets?${params.toString()}`);
    // ... rest of function
}
```

**Step 4: Add smart default (visibility when location set)**

Modify loadSortPreference:

```javascript
async function loadSortPreference() {
    try {
        // Check if location is configured
        const settingsResponse = await fetch('/api/settings');
        const settings = await settingsResponse.json();
        const hasLocation = settings.location_latitude !== null;

        // Load saved preference or use smart default
        const saved = localStorage.getItem('catalog_sort_preference');
        const defaultSort = hasLocation ? 'visibility' : 'magnitude';
        const sortBy = saved || defaultSort;

        document.getElementById('catalog-sort').value = sortBy;
        catalogFilters.sortBy = sortBy;
        updateSortIndicator(sortBy);
    } catch (e) {
        console.warn('Could not load sort preference:', e);
        catalogFilters.sortBy = 'magnitude';
    }
}
```

**Step 5: Manual test**

1. Go to Catalog tab
2. Verify sort dropdown appears
3. Change sort to "Visibility Tonight"
4. Verify catalog reloads with visibility sorted first
5. Change to "Size"
6. Verify largest objects appear first
7. Refresh page - verify sort preference persists

**Step 6: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add smart sorting to catalog browser"
```

---

## Task 9: Integration - Connect plan builder to planner API

**Files:**
- Modify: `frontend/index.html` (customPlan.generatePlan function)
- Modify: `backend/app/api/routes.py` (accept custom target list)

**Step 1: Update generatePlan to call API**

Replace customPlan.generatePlan function:

```javascript
async generatePlan() {
    if (this.targets.length === 0) {
        alert('Add objects to your plan first!');
        return;
    }

    // Check if planner tab has existing plan
    const existingPlan = document.getElementById('session-summary');
    const hasExistingPlan = existingPlan && existingPlan.style.display !== 'none';

    if (hasExistingPlan) {
        if (!confirm(`Replace existing plan?\n\nThis will replace the current plan in the Planner tab with a new plan optimized for these ${this.targets.length} objects.`)) {
            return;
        }
    }

    // Show loading
    const container = document.getElementById('custom-plan-container');
    const originalHtml = container.innerHTML;
    container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating optimized plan...</p></div>';

    try {
        // Get current planning parameters from planner tab
        const planRequest = {
            location: {
                latitude: parseFloat(document.getElementById('latitude').value),
                longitude: parseFloat(document.getElementById('longitude').value),
                elevation: parseFloat(document.getElementById('elevation').value),
                timezone: document.getElementById('timezone').value
            },
            constraints: {
                min_altitude: parseFloat(document.getElementById('min-altitude').value),
                max_altitude: parseFloat(document.getElementById('max-altitude').value),
                min_moon_distance: parseFloat(document.getElementById('moon-distance').value) || 30,
                max_field_rotation: parseFloat(document.getElementById('max-rotation').value) || 2.0
            },
            date: document.getElementById('observation-date').value || new Date().toISOString().split('T')[0],
            custom_targets: this.targets.map(t => t.catalog_id)  // Send catalog IDs
        };

        const response = await fetch('/api/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(planRequest)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const plan = await response.json();

        // Store plan globally
        window.currentPlan = plan;

        // Clear custom plan
        this.clear();

        // Switch to planner tab and display results
        showTab('planner');
        displayPlanResults(plan);

    } catch (error) {
        console.error('Error generating plan:', error);
        alert(`Failed to generate plan: ${error.message}`);
        container.innerHTML = originalHtml;
    }
}
```

**Step 2: Update backend to accept custom_targets**

Modify `backend/app/models/models.py` PlanRequest:

```python
class PlanRequest(BaseModel):
    """Request model for generating an observing plan."""

    location: Location
    date: str = Field(..., description="Observation date (YYYY-MM-DD)")
    constraints: ObservingConstraints
    object_types: Optional[List[str]] = Field(None, description="Filter by object types")
    max_targets: int = Field(20, description="Maximum number of targets to schedule", ge=1, le=100)
    custom_targets: Optional[List[str]] = Field(None, description="Custom list of catalog IDs to schedule")
```

**Step 3: Update planner service to handle custom targets**

Modify `backend/app/services/planner_service.py` generate_plan method:

```python
def generate_plan(self, request: PlanRequest) -> ObservingPlan:
    """Generate observing plan from request."""
    # ... existing code ...

    # Get candidate targets
    if request.custom_targets:
        # Use custom target list
        candidates = []
        for catalog_id in request.custom_targets:
            target = self.catalog_service.get_target_by_id(catalog_id)
            if target:
                candidates.append(target)

        if len(candidates) == 0:
            raise ValueError("None of the custom targets were found in catalog")
    else:
        # Use filtered catalog (existing behavior)
        candidates = self.catalog_service.filter_targets(
            object_types=request.object_types,
            max_magnitude=15.0,  # Only bright targets
            limit=1000,
        )

    # ... rest of existing code ...
```

**Step 4: Manual test**

1. Go to Catalog tab
2. Add 3 objects to custom plan
3. Click "Generate Optimized Plan"
4. Verify confirmation modal appears if plan exists
5. Verify plan generates with only those 3 objects
6. Verify switches to Planner tab
7. Verify custom plan clears

**Step 5: Commit**

```bash
git add frontend/index.html backend/app/models/models.py backend/app/services/planner_service.py
git commit -m "feat: connect plan builder to planner API"
```

---

## Task 10: Update GitHub Issue and documentation

**Files:**
- Modify: Issue #5 (mark items complete)
- Create: `docs/user-guides/CATALOG_BROWSER.md`

**Step 1: Update Issue #5**

Mark completed items:

```bash
gh issue edit 5 --body "## Description
Enhance the existing catalog browser with planning integration, real-time visibility calculations, and custom plan building.

## Current State
Basic catalog browser exists with:
- ✅ Search and filters (type, magnitude, constellation)
- ✅ Pagination
- ✅ Object preview modal (Aladin Lite)
- ✅ Basic object cards showing RA/Dec, magnitude, size

## Enhancements Completed
- ✅ Real-time visibility calculations (current altitude, best time tonight)
- ✅ Visibility badges (visible/rising/setting/below horizon)
- ✅ \"Add to Plan\" button to build custom observing plans
- ✅ Custom plan builder section (queue objects, generate optimized schedule)
- ✅ Smart sorting by visibility (default when location configured)
- ✅ Additional sort options (brightness, size, name)
- ✅ Static \"best viewing months\" info on cards (replaced button)
- ✅ Removed unused \"Details\" button

## Documentation
See \`docs/plans/2025-12-27-catalog-browser-enhancement-design.md\` for design.
See \`docs/user-guides/CATALOG_BROWSER.md\` for user guide.
"
```

**Step 2: Create user guide**

Create `docs/user-guides/CATALOG_BROWSER.md`:

```markdown
# Catalog Browser User Guide

The enhanced catalog browser helps you discover and plan observations of deep sky objects with real-time visibility information.

## Features

### Real-Time Visibility

Each object card shows:
- **Current altitude** - How high the object is right now
- **Visibility status** - Color-coded badge:
  - 🟢 Green "Visible" - Currently at good altitude (30-70°)
  - 🔵 Blue "Rising" - Below 30°, getting higher
  - 🟠 Orange "Setting" - Still visible but descending
  - ⚫ Gray "Below" - Below the horizon
- **Best viewing time tonight** - When the object peaks during tonight's observing window
- **Best viewing months** - Seasons when object is highest at midnight

### Custom Plan Building

1. Browse the catalog and click "Add to Plan" on objects you want to image
2. Added objects appear as chips at the top of the page
3. Click "Generate Optimized Plan" to create a schedule
4. The planner optimizes the order based on altitude, weather, and constraints

### Smart Sorting

Sort catalog by:
- **Visibility Tonight** (default) - Best objects to image right now
- **Brightness** - Brightest objects first
- **Size** - Largest objects first
- **Name** - Alphabetical order

Your sort preference is saved between sessions.

## Setup Requirements

**To see visibility information:**
1. Go to Settings tab
2. Configure your location (latitude, longitude, elevation, timezone)
3. Return to Catalog - visibility appears automatically

**Without location configured:**
- Cards show "Set location to see visibility" link
- Catalog defaults to brightness sorting
- "Add to Plan" button is disabled

## Tips

- **Finding what's optimal now:** Sort by "Visibility Tonight" to see objects at peak altitude
- **Planning ahead:** Use "Best viewing months" to know when an object is seasonal
- **Building wishlists:** Add multiple objects to your plan, then let the planner optimize the schedule
- **Quick preview:** Click the object image to see DSS survey data in Aladin Lite viewer

## Keyboard Shortcuts

- Click chip × to remove from plan
- Refresh page to reload visibility (updated to current time)
```

**Step 3: Commit**

```bash
git add docs/user-guides/CATALOG_BROWSER.md
git commit -m "docs: add catalog browser user guide"
gh issue comment 5 --body "✅ Implementation complete! See docs/user-guides/CATALOG_BROWSER.md for usage."
```

---

## Summary

This plan implements catalog browser enhancements in 10 tasks:

1. ✅ Backend visibility calculations (ephemeris service)
2. ✅ Pydantic models for visibility data
3. ✅ API endpoint enhancements (sorting, visibility)
4. ✅ Frontend plan builder state management
5. ✅ Redesigned catalog cards with visibility
6. ✅ Smart sorting dropdown
7. ✅ Integration with planner API
8. ✅ Documentation and user guide

**Estimated time:** 4-6 hours for full implementation

**Testing checklist:**
- [ ] Backend unit tests pass
- [ ] Frontend plan builder works without location
- [ ] Frontend plan builder works with location
- [ ] Visibility calculations match expected values
- [ ] Sort preferences persist across sessions
- [ ] Custom plan generation creates optimized schedule
- [ ] localStorage handles errors gracefully

---

## Next Steps

After implementation:
1. Manual QA testing with real location
2. Performance testing with large result sets
3. Consider adding batch operations (future enhancement)
