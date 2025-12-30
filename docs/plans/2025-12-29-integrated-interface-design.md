# Integrated Interface Overhaul Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a comprehensive closed-loop workflow integrating Seestar telescope control, catalog browser enhancements, and capture history tracking.

**Architecture:** Unified interface with real-time telescope operations, intelligent plan building with visibility calculations, and automatic file transfer with capture history tracking. All components feed back into planning to optimize future observations.

**Tech Stack:** FastAPI, SQLAlchemy, Astropy (FITS), thefuzz (fuzzy matching), WebSocket (real-time), SSE (execution progress), Vanilla JS (reactive state)

---

## Architecture Overview

### System Architecture

The redesigned interface creates a closed-loop workflow:

```
Catalog Browser → Plan Builder → Observe/Execute → Capture Files → History Tracking → Catalog Browser
      ↑                                                                                    ↓
      └────────────────── Feedback Loop (avoid re-observing) ──────────────────────────┘
```

### Core Components

**1. Capture History Layer** (Backend)
- `CaptureHistory` model: Aggregated stats per catalog target (total exposure, frames, sessions, status)
- `OutputFile` model: Links individual FITS/JPG files to targets and executions
- `FileScannerService`: Discovers files in output directory, extracts FITS metadata, fuzzy-matches to catalog
- API endpoints: `/api/captures`, `/api/captures/scan`, `/api/captures/{catalog_id}`

**2. Enhanced Catalog Browser** (Frontend + Backend)
- Backend: Extends `/api/targets` to include visibility calculations and capture history
- Frontend: Interactive cards with real-time altitude/visibility, plan builder state, capture indicators
- Features: Smart sorting (by altitude, setting time, capture status), filter by object type, "Add to Plan" workflow

**3. Seestar Remote Operations** (Observe Tab)
- Connection manager: WebSocket for real-time status updates
- Command interface: All 58 Seestar API commands exposed via clean UI
- Execution engine: Automated plan execution with progress tracking
- Live monitoring: Current target, exposure progress, quality metrics, preview images
- File transfer: Automatic download and organization after capture completion

### Technology Stack

- **Backend:** FastAPI, SQLAlchemy, Astropy (FITS), thefuzz (fuzzy matching)
- **Frontend:** Vanilla JS with Vue.js-style reactive state management, localStorage for plan persistence
- **Real-time:** WebSocket for telescope status, Server-Sent Events for execution progress

---

## Component 1: Capture History Backend

### Database Models

**File:** `backend/app/models/capture_models.py`

```python
from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class CaptureHistory(Base):
    """Aggregated capture statistics per catalog target."""

    __tablename__ = "capture_history"

    id = Column(Integer, primary_key=True)
    catalog_id = Column(String(50), unique=True, nullable=False, index=True)

    # Aggregate stats
    total_exposure_seconds = Column(Integer, default=0)
    total_frames = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    first_captured_at = Column(DateTime, nullable=True)
    last_captured_at = Column(DateTime, nullable=True)

    # User-controlled status: null (captured), 'complete', 'needs_more_data'
    status = Column(String(20), nullable=True)
    suggested_status = Column(String(20), nullable=True)  # Auto-calculated

    # Quality metrics (from best capture)
    best_fwhm = Column(Float, nullable=True)
    best_star_count = Column(Integer, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    output_files = relationship("OutputFile", back_populates="capture_history")


class OutputFile(Base):
    """Links captured files to targets and executions."""

    __tablename__ = "output_files"

    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False, unique=True, index=True)
    file_type = Column(String(20), nullable=False)  # raw_fits, stacked_fits, jpg, png, tiff
    file_size_bytes = Column(BigInteger, nullable=False)

    # Target linking
    catalog_id = Column(String(50), nullable=False, index=True)
    catalog_id_confidence = Column(Float, default=1.0)  # Fuzzy match score

    # Execution linking (nullable - files may exist before tracking)
    execution_id = Column(Integer, ForeignKey("telescope_executions.id"), nullable=True)
    execution_target_id = Column(Integer, ForeignKey("execution_targets.id"), nullable=True)

    # FITS metadata
    exposure_seconds = Column(Integer, nullable=True)
    filter_name = Column(String(20), nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    gain = Column(Integer, nullable=True)

    # Quality metrics
    fwhm = Column(Float, nullable=True)
    star_count = Column(Integer, nullable=True)

    # Timestamps
    observation_date = Column(DateTime, nullable=True)  # From FITS DATE-OBS
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    capture_history = relationship("CaptureHistory", back_populates="output_files")
```

### FileScannerService Algorithm

**File:** `backend/app/services/file_scanner_service.py`

```python
class FileScannerService:
    """Discovers and links capture files to catalog targets."""

    async def scan_directory(self, output_dir: str) -> Dict[str, Any]:
        """
        Scan output directory for capture files.

        Algorithm:
        1. Scan recursively for FITS/JPG/PNG/TIFF files
        2. For each file:
           - Extract target name from FITS OBJECT header, fallback to parent directory
           - Fuzzy match target name to catalog (handles "M 31" vs "M31" vs "NGC 224")
           - Extract metadata: exposure, filter, temperature, observation date
           - Calculate quality metrics: FWHM, star count (if FITS)
        3. Create/update OutputFile record
        4. Aggregate to CaptureHistory:
           - Sum total exposure and frames
           - Count unique observation dates → sessions
           - Track best FWHM and star count
           - Suggest status: <1hr = needs_more_data, 1-3hrs = null, >3hrs = complete

        Returns summary: files_scanned, files_linked, targets_updated
        """

    async def scan_files(
        self,
        file_paths: List[str],
        catalog_id: str = None,
        execution_id: int = None
    ) -> List[OutputFile]:
        """
        Scan specific files (e.g., after transfer from Seestar).

        If catalog_id provided, use it directly (skip fuzzy match).
        Links to execution_id if provided.
        """

    def _extract_fits_metadata(self, fits_path: str) -> Dict[str, Any]:
        """Extract metadata from FITS header using Astropy."""

    def _calculate_quality_metrics(self, fits_path: str) -> Dict[str, float]:
        """Calculate FWHM and star count from FITS data."""

    def _fuzzy_match_catalog(self, target_name: str) -> Optional[Tuple[str, float]]:
        """
        Fuzzy match target name to catalog.

        Returns (catalog_id, confidence_score) or None.
        Uses thefuzz library with token_sort_ratio.
        Handles: "M 31" vs "M31" vs "NGC 224" vs "Andromeda"
        """

    async def _update_capture_history(self, catalog_id: str):
        """Aggregate OutputFiles to update CaptureHistory."""
```

### API Endpoints

**File:** `backend/app/api/captures.py`

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.file_scanner_service import FileScannerService

router = APIRouter(prefix="/api/captures", tags=["captures"])


@router.get("")
async def list_capture_history(
    status: Optional[str] = None,  # filter by status
    db: Session = Depends(get_db)
):
    """List all capture history with optional status filter."""


@router.get("/{catalog_id}")
async def get_capture_details(
    catalog_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed capture history for specific target including file list."""


@router.post("/scan")
async def trigger_file_scan(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger background file scan of output directory."""
    scanner = FileScannerService()
    background_tasks.add_task(scanner.scan_directory, settings.OUTPUT_DIRECTORY)
    return {"message": "File scan started"}


@router.patch("/{catalog_id}")
async def update_capture_status(
    catalog_id: str,
    status: str,  # 'complete' or 'needs_more_data'
    db: Session = Depends(get_db)
):
    """Update user-controlled status for target."""
```

---

## Component 2: Enhanced Catalog Browser

### Backend API Enhancement

**File:** `backend/app/api/targets.py` (extend existing)

```python
from app.services.ephemeris_service import EphemerisService
from app.models.capture_models import CaptureHistory

@router.get("/targets")
async def get_targets_enriched(
    # Visibility parameters
    date: Optional[str] = None,          # Calculate visibility for this date
    location_id: Optional[int] = None,   # Use saved location from settings
    start_time: Optional[str] = None,    # Observing window start (local time)
    end_time: Optional[str] = None,      # Observing window end

    # Capture history filters
    include_captured: bool = True,       # Include captured targets
    capture_status: Optional[str] = None, # Filter by status

    db: Session = Depends(get_db)
):
    """
    Get targets enriched with visibility and capture history.

    Response format:
    {
      "targets": [
        {
          "catalog_id": "M31",
          "name": "Andromeda Galaxy",
          "ra_hours": 0.71,
          "dec_degrees": 41.27,
          "object_type": "galaxy",
          "magnitude": 3.4,
          "size_arcmin": 190.0,
          "imaging_mode": "deepsky",  # or "planetary"

          # Visibility data (if date/location provided)
          "visibility": {
            "is_visible": true,
            "peak_time": "2025-12-29T23:45:00",
            "peak_altitude": 68.5,
            "rise_time": "2025-12-29T18:30:00",
            "set_time": "2025-12-30T05:15:00",
            "hours_visible": 10.75,
            "field_rotation_rate": 0.3  # deg/min at peak
          },

          # Capture history (if exists)
          "capture_history": {
            "total_exposure_seconds": 7200,  # 2 hours
            "total_frames": 720,
            "total_sessions": 3,
            "last_captured_at": "2025-12-15T22:30:00",
            "status": "needs_more_data",
            "suggested_status": "needs_more_data"
          }
        }
      ]
    }
    """
```

### Frontend Redesign

**File:** `frontend/index.html` (catalog-tab section)

**UI Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│ 📚 Browse Catalog                                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌───────────────────────┐  ┌────────────────────────────┐  │
│ │ 🎯 Plan Builder       │  │ 🔧 Filters & Sort          │  │
│ │ 3 targets selected    │  │ Type: [All ▾]              │  │
│ │ [View Plan] [Clear]   │  │ Status: [☐ Show Captured]  │  │
│ └───────────────────────┘  │ Sort: [Setting Time ▾]     │  │
│                            └────────────────────────────────┘  │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ M31 - Andromeda Galaxy                      🌟 VISIBLE   │ │
│ │ Galaxy • 3.4 mag • 190' × 60' • 🌌 Deep-Sky              │ │
│ │                                                           │ │
│ │ 📈 Altitude: 68° (peaks at 23:45)      [Add to Plan +]   │ │
│ │ 📊 Captured: 2.0hrs (3 sessions)      [View Files]       │ │
│ │ ⏱️  Last: 2025-12-15                   Status: Needs More │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ M42 - Orion Nebula                          ⬇️ SETTING   │ │
│ │ Nebula • 4.0 mag • 85' × 60' • 🌌 Deep-Sky   Sets in 2.5h│ │
│ │                                                           │ │
│ │ 📈 Altitude: 45° (setting)            [Add to Plan +]    │ │
│ │ 📊 Not captured yet                   [Priority!]        │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ JUPITER                                     🪐 PLANETARY  │ │
│ │ Planet • -2.5 mag • 45" diameter                         │ │
│ │                                                           │ │
│ │ 📈 Altitude: 52° (peaks at 21:15)      [Add to Plan +]   │ │
│ │ 📊 Not captured yet                   Mode: Video        │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ NGC 7000 - North America Nebula             ✅ COMPLETE  │ │
│ │ Nebula • 4.0 mag • 120' × 100' • 🌌 Deep-Sky             │ │
│ │                                                           │ │
│ │ 📈 Altitude: 52° (peaks at 21:15)      [View Files]      │ │
│ │ 📊 Captured: 5.5hrs (8 sessions)      Status: Complete   │ │
│ │ ⏱️  Last: 2025-12-20                   [Re-observe]      │ │
│ └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Smart Sorting Options:**
- **Setting time** (urgency) - Prioritizes targets setting soon
- **Peak altitude** - Best visibility first
- **Never captured** - New targets first
- **Needs more data** - Incomplete targets first
- **Brightness** - Easier targets first
- **Object type** - Group by galaxy/nebula/cluster/planet

**Plan Builder Workflow:**

```javascript
// State management
const planBuilder = {
    targets: [],  // Array of catalog_ids

    addTarget(catalogId) {
        if (!this.targets.includes(catalogId)) {
            this.targets.push(catalogId);
            this.save();
            this.updateUI();
        }
    },

    removeTarget(catalogId) {
        this.targets = this.targets.filter(id => id !== catalogId);
        this.save();
        this.updateUI();
    },

    clear() {
        this.targets = [];
        this.save();
        this.updateUI();
    },

    save() {
        localStorage.setItem('customPlan', JSON.stringify(this.targets));
    },

    load() {
        const saved = localStorage.getItem('customPlan');
        this.targets = saved ? JSON.parse(saved) : [];
    },

    updateUI() {
        document.getElementById('plan-builder-count').textContent = this.targets.length;
        // Update button states on target cards
    },

    viewPlan() {
        // Navigate to Planner tab with pre-populated targets
        showTab('planner');
        plannerTab.loadCustomTargets(this.targets);
    }
};
```

---

## Component 3: File Transfer Integration

### File Organization Structure

```
{OUTPUT_DIRECTORY}/
├── M31/
│   ├── 2025-12-29/
│   │   ├── M31_20251229_2145_Light_300s_Gain100.fit
│   │   ├── M31_20251229_stacked.fit
│   │   └── M31_20251229_processed.jpg
│   └── 2025-12-15/
│       └── ...
├── M42/
│   └── 2025-12-28/
│       └── ...
├── JUPITER/
│   └── 2025-12-29/
│       └── JUPITER_20251229_2200_video.avi
└── NGC7000/
    └── ...
```

### FileTransferService

**File:** `backend/app/services/file_transfer_service.py`

```python
from pathlib import Path
from typing import List
from app.clients.seestar_client import SeestarClient
from app.services.file_scanner_service import FileScannerService
from app.core.config import settings
from datetime import datetime


class FileTransferService:
    """Handles downloading files from Seestar to output directory."""

    async def transfer_target_files(
        self,
        seestar_client: SeestarClient,
        catalog_id: str,
        target_name: str,
        execution_id: int = None
    ) -> Dict[str, Any]:
        """
        Transfer all files for a target from Seestar.

        Returns:
        {
            "files_transferred": 12,
            "total_size_bytes": 458392847,
            "transferred_paths": [...],
            "errors": []
        }
        """
        # 1. List files on Seestar for this target
        files = await seestar_client.list_target_files(target_name)

        # 2. Create output directory structure: {target}/{date}/
        today = datetime.now().strftime("%Y-%m-%d")
        output_dir = Path(settings.OUTPUT_DIRECTORY) / target_name / today
        output_dir.mkdir(parents=True, exist_ok=True)

        # 3. Download each file
        transferred = []
        errors = []
        total_size = 0

        for file_info in files:
            try:
                local_path = output_dir / file_info['filename']
                await seestar_client.download_file(file_info['path'], local_path)
                transferred.append(str(local_path))
                total_size += local_path.stat().st_size
            except Exception as e:
                errors.append({"file": file_info['filename'], "error": str(e)})

        # 4. Trigger file scanner to update capture history
        scanner = FileScannerService()
        await scanner.scan_files(transferred, catalog_id, execution_id)

        # 5. Optionally delete from Seestar (if enabled in settings)
        if settings.AUTO_DELETE_TRANSFERRED_FILES:
            for file_info in files:
                try:
                    await seestar_client.delete_file(file_info['path'])
                except Exception as e:
                    # Log but don't fail - files still transferred
                    pass

        return {
            "files_transferred": len(transferred),
            "total_size_bytes": total_size,
            "transferred_paths": transferred,
            "errors": errors
        }

    async def transfer_plan_files(
        self,
        seestar_client: SeestarClient,
        execution_id: int,
        targets: List[Dict[str, str]]  # [{"catalog_id": "M31", "target_name": "..."}, ...]
    ) -> Dict[str, Any]:
        """Transfer files for all targets in a plan."""
        results = []

        for target in targets:
            result = await self.transfer_target_files(
                seestar_client,
                target['catalog_id'],
                target['target_name'],
                execution_id
            )
            results.append({
                "target": target['target_name'],
                **result
            })

        return {
            "targets_processed": len(results),
            "total_files_transferred": sum(r['files_transferred'] for r in results),
            "total_size_bytes": sum(r['total_size_bytes'] for r in results),
            "results": results
        }
```

### Observe Tab Integration

```javascript
// After each target completes
async function onTargetComplete(targetId) {
    // Show transfer status
    updateExecutionStatus('Transferring files from telescope...');

    // Call transfer API
    const response = await fetch('/api/transfer/target', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            catalog_id: currentTarget.catalog_id,
            target_name: currentTarget.name,
            execution_id: currentExecutionId
        })
    });

    const result = await response.json();

    // Update UI with transfer results
    const sizeGB = (result.total_size_bytes / 1073741824).toFixed(2);
    showNotification(
        `✅ Transfer complete: ${result.files_transferred} files (${sizeGB} GB)`,
        'success'
    );

    // Refresh capture history for next planning
    await refreshCaptureHistory();

    // Move to next target
    nextTarget();
}
```

---

## Component 4: Observe Tab Seestar Integration

### Layout Structure

```
┌──────────────────────────────────────────────────────────────────┐
│ 🔭 Observe                                                        │
├─────────────────┬────────────────────────────────────────────────┤
│ SIDEBAR (300px) │ MAIN CONTENT                                   │
│                 │                                                 │
│ 🔌 Connection   │ ┌────────────────────────────────────────────┐ │
│ IP: [192.168...]│ │ EXECUTION STATUS BANNER                    │ │
│ [Connect]       │ │ 🔭 SLEWING TO M31                          │ │
│ Status: ● Ready │ │ Target 2/5 • 40% Complete • 01:23 elapsed  │ │
│ Firmware: 6.45  │ └────────────────────────────────────────────┘ │
│                 │                                                 │
│ ⚡ Quick Control │ ┌────────────────────────────────────────────┐ │
│ [Execute Plan]  │ │ LIVE VIEW                                  │ │
│ [Abort]         │ │ [Preview image from telescope]             │ │
│ [Park]          │ │ Exposure: 10s • Gain: 80 • Temp: -10°C    │ │
│                 │ │ Last updated: 3s ago                       │ │
│ 🎛️ Manual Ctrl  │ └────────────────────────────────────────────┘ │
│ ▸ Goto...       │                                                 │
│ ▸ Focus         │ ┌────────────────────────────────────────────┐ │
│ ▸ Exposure      │ │ TARGET PROGRESS                            │ │
│ ▸ Heater        │ │ M31 - Andromeda Galaxy (🌌 Deep-Sky)       │ │
│ ▸ System        │ │ ▓▓▓▓▓▓▓▓▓▓▓░░░░ 240/300 frames (80%)      │ │
│                 │ │ Alt: 68° • Az: 125° • FWHM: 2.3"           │ │
│ 📊 Telemetry    │ │ Stars: 2847 • Rotation: 0.3°/min           │ │
│ RA: 00h 42m     │ └────────────────────────────────────────────┘ │
│ Dec: +41° 16'   │                                                 │
│ Alt: 68.5°      │ ┌────────────────────────────────────────────┐ │
│ Az: 125.3°      │ │ PLAN QUEUE                                 │ │
│ Temp: -10°C     │ │ ✓ M42 (45min) - Complete [3.2GB]          │ │
│ Heater: ON 90%  │ │ ▶ M31 (60min) - In Progress                │ │
│ Focus: 1234     │ │ ⏳ NGC7000 (40min) - Queued                │ │
│                 │ │ ⏳ M81 (30min) - Queued                    │ │
│ 🌡️ Conditions   │ │ ⏳ JUPITER (5min 🪐) - Queued              │ │
│ [Refresh]       │ └────────────────────────────────────────────┘ │
│ Weather: Clear  │                                                 │
│ Sun: -18° (ast) │                                                 │
│ Moon: 25% (set) │                                                 │
└─────────────────┴────────────────────────────────────────────────┘
```

### Three Operation Modes

**1. Automated Plan Execution** (Primary workflow)

```python
# backend/app/services/execution_engine.py

class ExecutionEngine:
    """Automated plan execution with full Seestar control."""

    async def execute_plan(self, plan: ObservingPlan, execution_id: int):
        """
        Execute plan with full automation:
        - Slew to each target
        - Plate solve for precise centering
        - Autofocus
        - Start imaging (mode appropriate: deep-sky vs planetary)
        - Monitor quality (FWHM, star count)
        - Transfer files on completion
        - Move to next target

        State machine: IDLE → SLEWING → SOLVING → FOCUSING → IMAGING → TRANSFERRING → NEXT
        """

        for target in plan.scheduled_targets:
            try:
                # Update state
                await self._update_execution_state(execution_id, target, 'slewing')

                # Slew to target
                await self.seestar_client.goto_target(
                    target.target.name,
                    target.target.ra_hours,
                    target.target.dec_degrees,
                    use_lp_filter=target.use_lp_filter
                )

                # Wait for slew complete + plate solve
                await self._wait_for_slew_complete()
                await self._update_execution_state(execution_id, target, 'solving')
                solve_result = await self.seestar_client.get_plate_solve_result()

                # Autofocus
                await self._update_execution_state(execution_id, target, 'focusing')
                await self.seestar_client.start_autofocus()
                await self._wait_for_autofocus_complete()

                # Start imaging (mode-specific)
                await self._update_execution_state(execution_id, target, 'imaging')
                await self._start_target_imaging(target)

                # Monitor imaging progress
                await self._monitor_imaging(execution_id, target)

                # Transfer files
                await self._update_execution_state(execution_id, target, 'transferring')
                transfer_result = await self.file_transfer_service.transfer_target_files(
                    self.seestar_client,
                    target.target.catalog_id,
                    target.target.name,
                    execution_id
                )

                # Mark target complete
                await self._update_execution_state(execution_id, target, 'completed')

            except Exception as e:
                # Error handling: retry slews, log failures, allow skip/abort
                await self._handle_target_error(execution_id, target, e)

    async def _start_target_imaging(self, target: ScheduledTarget):
        """Start imaging with mode appropriate for target type."""

        if target.target.is_planetary:
            # Planetary mode: high FPS video capture
            await self.seestar_client.configure_planetary_imaging(
                exposure_ms=10,
                gain=200,
                fps=30,
                duration_seconds=target.duration_minutes * 60
            )
            await self.seestar_client.start_planet_scan()

        else:
            # Deep-sky mode: long exposure stacking
            await self.seestar_client.iscope_start_stack(
                target_name=target.target.name,
                ra=target.target.ra_hours,
                dec=target.target.dec_degrees,
                exposure_sec=target.recommended_exposure,
                frames=target.recommended_frames,
                lp_filter=target.use_lp_filter
            )

    async def _monitor_imaging(self, execution_id: int, target: ScheduledTarget):
        """Monitor imaging progress with quality checks."""

        while True:
            # Check if stacking complete
            is_complete = await self.seestar_client.check_stacking_complete()
            if is_complete:
                break

            # Get current state
            state = await self.seestar_client.get_device_state()

            # Extract progress
            frames_captured = state.get('stack_count', 0)
            total_frames = target.recommended_frames
            progress = (frames_captured / total_frames * 100) if total_frames > 0 else 0

            # Quality check
            if frames_captured % 50 == 0:  # Every 50 frames
                # Check FWHM - if degrading significantly, may need refocus
                # (Future enhancement)
                pass

            # Emit progress update via SSE
            await self._emit_progress_update(execution_id, target, {
                'frames_captured': frames_captured,
                'total_frames': total_frames,
                'progress': progress,
                'altitude': state.get('alt', 0),
                'azimuth': state.get('az', 0)
            })

            # Wait before next check
            await asyncio.sleep(5)
```

**2. Manual Control Panel** (Expert mode)

```javascript
// frontend/index.html - Manual controls (expandable sections)

const manualControls = {
    mount: {
        title: '🔭 Mount Control',
        commands: [
            {label: 'Goto Coordinates', action: 'showGotoDialog'},
            {label: 'Manual Movement', action: 'showManualMovement'},
            {label: 'Stop Movement', action: 'stopMovement'},
            {label: 'Park Telescope', action: 'parkTelescope', confirm: true}
        ]
    },

    imaging: {
        title: '📸 Imaging',
        commands: [
            {label: 'Start View', action: 'showStartViewDialog'},
            {label: 'Start Stack', action: 'showStartStackDialog'},
            {label: 'Stop View/Stack', action: 'stopImaging'},
            {label: 'Set Exposure', action: 'showExposureDialog'},
            {label: 'Configure Dithering', action: 'showDitheringDialog'}
        ]
    },

    focus: {
        title: '🔍 Focus',
        commands: [
            {label: 'Autofocus', action: 'startAutofocus'},
            {label: 'Move to Position', action: 'showFocusPositionDialog'},
            {label: 'Manual Offset (+/-)', action: 'showFocusOffsetDialog'}
        ]
    },

    hardware: {
        title: '⚙️ Hardware',
        commands: [
            {label: 'Dew Heater Control', action: 'showHeaterDialog'},
            {label: 'DC Output', action: 'showDCOutputDialog'}
        ]
    },

    system: {
        title: '💻 System',
        commands: [
            {label: 'Get System Info', action: 'getSystemInfo'},
            {label: 'WiFi Config', action: 'showWifiDialog'},
            {label: 'Reboot', action: 'rebootTelescope', confirm: true},
            {label: 'Shutdown', action: 'shutdownTelescope', confirm: true}
        ]
    }
};

// Render expandable sections
function renderManualControls() {
    const container = document.getElementById('manual-controls');

    for (const [key, section] of Object.entries(manualControls)) {
        const sectionEl = createExpandableSection(section.title, section.commands);
        container.appendChild(sectionEl);
    }
}

// Execute command with confirmation if needed
async function executeManualCommand(command) {
    if (command.confirm) {
        const confirmed = await showConfirmDialog(
            `Are you sure you want to ${command.label}?`
        );
        if (!confirmed) return;
    }

    // Call action handler
    await window[command.action]();
}
```

**3. Live Monitoring** (Always active when connected)

```javascript
// WebSocket connection for real-time device state
class SeestarMonitor {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 5000;
        this.updateInterval = 2000;
    }

    connect(ip) {
        this.ws = new WebSocket(`ws://${window.location.host}/ws/seestar/${ip}`);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.startMonitoring();
        };

        this.ws.onmessage = (event) => {
            const state = JSON.parse(event.data);
            this.updateTelemetry(state);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected, reconnecting...');
            setTimeout(() => this.connect(ip), this.reconnectInterval);
        };
    }

    updateTelemetry(state) {
        // Update RA/Dec
        document.getElementById('telemetry-ra').textContent =
            formatRA(state.ra);
        document.getElementById('telemetry-dec').textContent =
            formatDec(state.dec);

        // Update Alt/Az
        document.getElementById('telemetry-alt').textContent =
            `${state.alt.toFixed(1)}°`;
        document.getElementById('telemetry-az').textContent =
            `${state.az.toFixed(1)}°`;

        // Update temperature & heater
        document.getElementById('telemetry-temp').textContent =
            `${state.temperature}°C`;
        document.getElementById('telemetry-heater').textContent =
            state.heater_enable ? `ON ${state.heater_power}%` : 'OFF';

        // Update focus position
        document.getElementById('telemetry-focus').textContent =
            state.focus_position;

        // Update imaging progress (if stacking)
        if (state.is_stacking) {
            const progress = (state.stack_count / state.stack_total * 100).toFixed(0);
            document.getElementById('imaging-progress').textContent =
                `${state.stack_count}/${state.stack_total} (${progress}%)`;

            // Quality metrics
            if (state.last_fwhm) {
                document.getElementById('quality-fwhm').textContent =
                    `${state.last_fwhm.toFixed(1)}"`;
            }
            if (state.star_count) {
                document.getElementById('quality-stars').textContent =
                    state.star_count;
            }
        }

        // Alert checks
        this.checkAlerts(state);
    }

    checkAlerts(state) {
        // Temperature too high
        if (state.temperature > 30) {
            showAlert('⚠️ High temperature detected', 'warning');
        }

        // Tracking lost
        if (state.tracking_lost) {
            showAlert('❌ Tracking lost - check mount', 'error');
        }

        // WiFi signal weak
        if (state.wifi_signal < -80) {
            showAlert('📡 Weak WiFi signal', 'warning');
        }
    }
}

// Server-Sent Events for execution progress
const executionEvents = new EventSource('/api/execution/events');

executionEvents.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
        case 'target_started':
            updateExecutionBanner(`Observing ${data.target_name}`);
            break;

        case 'phase_change':
            updateExecutionDetail(`${data.phase}...`);
            break;

        case 'progress_update':
            updateProgressBar(data.progress);
            break;

        case 'target_completed':
            showNotification(`✅ ${data.target_name} complete`);
            break;

        case 'file_transfer':
            updateExecutionDetail(`Transferring ${data.files_count} files...`);
            break;

        case 'error':
            showAlert(`❌ Error: ${data.message}`, 'error');
            break;
    }
};
```

### Execution Engine State Machine

```
IDLE
  ↓ (user clicks Execute Plan)
CONNECTING
  ↓ (WebSocket established)
READY
  ↓ (plan loaded)
EXECUTING
  ├─ SLEWING (goto target)
  ├─ SOLVING (plate solve)
  ├─ FOCUSING (autofocus)
  ├─ IMAGING (stacking/video)
  │   ↓ (user clicks Pause)
  │   PAUSED
  │   ↓ (user clicks Resume)
  │   IMAGING
  ├─ TRANSFERRING (download files)
  └─ NEXT_TARGET (loop back to SLEWING)
  ↓ (all targets done)
COMPLETE
  ↓ (user clicks Park)
PARKING
  ↓
PARKED

At any point:
  ↓ (user clicks Abort)
ABORTING
  ├─ Stop current operation
  ├─ Park telescope
  └─ Save partial progress
  ↓
IDLE
```

---

## Component 5: Integration Points & Data Flow

### Cross-Component Integration

**1. Catalog → Planner → Observe Flow**

```javascript
// User builds plan in Catalog browser
function addTargetToPlan(catalogId) {
    planBuilder.addTarget(catalogId);
    localStorage.setItem('customPlan', JSON.stringify(planBuilder.targets));
    updatePlanBuilderUI();
}

// View plan navigates to Planner tab
function viewPlan() {
    showTab('planner');

    // Load custom targets into planner
    const customTargets = planBuilder.targets.map(id =>
        catalog.find(t => t.catalog_id === id)
    );

    // Pre-populate form with custom targets
    document.getElementById('custom-targets').value =
        customTargets.map(t => t.name).join('\n');

    // Auto-generate plan
    generatePlan();
}

// Execute from Observe tab
async function loadPlanToObserve(plan) {
    // Create execution record
    const response = await fetch('/api/execution/create', {
        method: 'POST',
        body: JSON.stringify({plan})
    });

    const execution = await response.json();
    currentExecutionId = execution.id;

    // Load into execution engine
    await startAutomatedExecution(plan);
}
```

**2. Observe → File Transfer → Capture History Flow**

```python
# On target completion
async def on_target_complete(
    execution_id: int,
    target: ScheduledTarget,
    seestar_client: SeestarClient
):
    """Complete target workflow with file transfer and history update."""

    # 1. Transfer files from Seestar
    transfer_service = FileTransferService()
    transfer_result = await transfer_service.transfer_target_files(
        seestar_client=seestar_client,
        catalog_id=target.target.catalog_id,
        target_name=target.target.name,
        execution_id=execution_id
    )

    # 2. FileScannerService automatically called within transfer_target_files
    #    - Creates OutputFile records
    #    - Extracts FITS metadata
    #    - Updates CaptureHistory aggregates
    #    - Calculates suggested_status

    # 3. Update execution target status
    db.query(ExecutionTarget).filter_by(
        execution_id=execution_id,
        catalog_id=target.target.catalog_id
    ).update({
        'status': 'completed',
        'files_transferred': transfer_result['files_transferred'],
        'total_size_bytes': transfer_result['total_size_bytes']
    })

    # 4. Emit SSE event to frontend
    await emit_sse_event({
        'type': 'target_completed',
        'target_name': target.target.name,
        'files_transferred': transfer_result['files_transferred'],
        'total_size_gb': transfer_result['total_size_bytes'] / 1073741824
    })
```

**3. Capture History → Catalog Browser Feedback**

```python
# Enhanced /api/targets endpoint
@router.get("/targets")
async def get_targets_enriched(
    date: Optional[str] = None,
    location_id: Optional[int] = None,
    include_captured: bool = True,
    capture_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 1. Get all catalog targets
    targets = catalog_service.get_all_targets()

    # 2. Join with capture history
    capture_map = {}
    if True:  # Always load capture history for display
        captures = db.query(CaptureHistory).all()
        capture_map = {c.catalog_id: c for c in captures}

    # 3. Calculate visibility (if date/location provided)
    visibility_map = {}
    if date and location_id:
        location = db.query(Location).get(location_id)
        tz = pytz.timezone(location.timezone)
        obs_date = tz.localize(datetime.strptime(date, '%Y-%m-%d'))

        ephemeris = EphemerisService()
        for target in targets:
            visibility = ephemeris.get_best_viewing_time(
                target, location,
                obs_date.replace(hour=20),  # 8 PM
                obs_date.replace(hour=4) + timedelta(days=1)  # 4 AM next day
            )
            visibility_map[target.catalog_id] = visibility

    # 4. Filter by capture status
    if not include_captured:
        targets = [t for t in targets if t.catalog_id not in capture_map]

    if capture_status:
        targets = [t for t in targets
                   if capture_map.get(t.catalog_id, {}).status == capture_status]

    # 5. Enrich targets with visibility and capture data
    enriched = []
    for target in targets:
        data = target.dict()

        # Add visibility
        if target.catalog_id in visibility_map:
            data['visibility'] = visibility_map[target.catalog_id]

        # Add capture history
        if target.catalog_id in capture_map:
            capture = capture_map[target.catalog_id]
            data['capture_history'] = {
                'total_exposure_seconds': capture.total_exposure_seconds,
                'total_frames': capture.total_frames,
                'total_sessions': capture.total_sessions,
                'last_captured_at': capture.last_captured_at,
                'status': capture.status,
                'suggested_status': capture.suggested_status
            }

        enriched.append(data)

    # 6. Apply scoring multipliers for smart sorting
    for target in enriched:
        base_score = 1.0

        # Capture status multipliers
        if 'capture_history' in target:
            status = target['capture_history']['status']
            if status == 'complete':
                base_score *= 0.1  # De-prioritize
            elif status == 'needs_more_data':
                base_score *= 2.0  # Boost priority
            else:  # null (captured but not complete)
                base_score *= 0.5

        # Visibility multipliers
        if 'visibility' in target:
            # Setting soon = higher priority
            hours_until_set = target['visibility'].get('hours_until_set', 999)
            if hours_until_set < 3:
                base_score *= 1.5

        target['priority_score'] = base_score

    return {"targets": enriched}
```

**4. Settings → All Components**

```python
# backend/app/core/config.py

class Settings(BaseSettings):
    """Centralized configuration for all components."""

    # Output directory
    OUTPUT_DIRECTORY: str = "/mnt/synology/shared/Astronomy"
    AUTO_TRANSFER_FILES: bool = True
    AUTO_DELETE_AFTER_TRANSFER: bool = True

    # Seestar connection
    SEESTAR_DEFAULT_IP: str = "192.168.2.47"
    SEESTAR_TIMEOUT_SECONDS: int = 30
    SEESTAR_RECONNECT_ATTEMPTS: int = 3

    # Capture thresholds for status suggestions
    CAPTURE_COMPLETE_HOURS: float = 3.0
    CAPTURE_NEEDS_MORE_HOURS: float = 1.0

    # Execution settings
    AUTO_RETRY_FAILED_SLEWS: bool = True
    MAX_SLEW_RETRIES: int = 3
    QUALITY_CHECK_INTERVAL: int = 60  # seconds
    MIN_FWHM_THRESHOLD: float = 4.0  # arcseconds (trigger refocus if exceeded)

    # File scanner
    FILE_SCAN_ON_STARTUP: bool = False
    FILE_SCAN_EXTENSIONS: List[str] = ['.fit', '.fits', '.jpg', '.png', '.tiff', '.avi']

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_RECONNECT_DELAY: int = 5

    class Config:
        env_file = ".env"
```

### Real-time Communication Architecture

```
Frontend ↔ Backend
   │
   ├─ WebSocket: /ws/seestar/{ip}
   │  ├─ Device state updates (2s interval)
   │  │  ├─ RA/Dec position
   │  │  ├─ Alt/Az coordinates
   │  │  ├─ Temperature & heater status
   │  │  ├─ Focus position
   │  │  ├─ Imaging progress (frames, %)
   │  │  └─ Quality metrics (FWHM, stars)
   │  └─ Heartbeat (30s interval)
   │
   ├─ Server-Sent Events: /api/execution/events
   │  ├─ Target lifecycle events
   │  │  ├─ target_started
   │  │  ├─ phase_change (slewing/solving/focusing/imaging)
   │  │  ├─ target_completed
   │  │  └─ error
   │  ├─ Progress updates
   │  │  ├─ progress_update (percentage)
   │  │  └─ frame_captured
   │  └─ File transfer events
   │     ├─ transfer_started
   │     ├─ transfer_progress
   │     └─ transfer_completed
   │
   └─ REST API: Traditional request/response
      ├─ POST /api/seestar/connect
      ├─ POST /api/seestar/goto
      ├─ POST /api/execution/start
      ├─ GET /api/targets (enriched)
      ├─ POST /api/captures/scan
      └─ POST /api/transfer/target
```

### Shared State Management

```javascript
// Frontend global reactive state
const appState = {
    // Connection
    seestarConnected: false,
    seestarIP: '192.168.2.47',
    firmwareVersion: null,
    deviceState: null,

    // Plan building
    customPlan: [],  // Array of catalog_ids
    currentPlan: null,  // Generated ObservingPlan

    // Execution
    currentExecution: null,
    currentTarget: null,
    currentPhase: null,  // slewing/solving/focusing/imaging/transferring
    executionProgress: 0,
    targetQueue: [],
    completedTargets: [],

    // Capture history (cached for offline use)
    captureHistoryMap: {},  // catalog_id → CaptureHistory
    lastCaptureRefresh: null,

    // Settings
    userLocation: null,
    observingDate: null,

    // UI state
    activeTab: 'catalog',
    catalogFilters: {
        objectType: null,
        includeCaptured: true,
        captureStatus: null,
        sortBy: 'setting_time'
    }
};

// Reactive updates with localStorage persistence
function updateState(key, value) {
    appState[key] = value;

    // Persist to localStorage
    const persistKeys = ['customPlan', 'seestarIP', 'userLocation', 'catalogFilters'];
    if (persistKeys.includes(key)) {
        localStorage.setItem(`appState_${key}`, JSON.stringify(value));
    }

    // Trigger UI updates
    triggerUIUpdate(key);
}

// Load persisted state on page load
function loadPersistedState() {
    for (const key of ['customPlan', 'seestarIP', 'userLocation', 'catalogFilters']) {
        const saved = localStorage.getItem(`appState_${key}`);
        if (saved) {
            appState[key] = JSON.parse(saved);
        }
    }
}

// UI update triggers
const uiUpdateHandlers = {
    seestarConnected: (connected) => {
        document.getElementById('connection-status').textContent =
            connected ? 'Connected' : 'Disconnected';
        document.getElementById('status-indicator').className =
            connected ? 'status-connected' : 'status-disconnected';

        // Enable/disable controls
        document.querySelectorAll('.requires-connection').forEach(el => {
            el.disabled = !connected;
        });
    },

    customPlan: (targets) => {
        document.getElementById('plan-builder-count').textContent = targets.length;

        // Update add/remove buttons on catalog cards
        document.querySelectorAll('.catalog-card').forEach(card => {
            const catalogId = card.dataset.catalogId;
            const btn = card.querySelector('.add-to-plan-btn');

            if (targets.includes(catalogId)) {
                btn.textContent = 'Remove from Plan -';
                btn.classList.add('in-plan');
            } else {
                btn.textContent = 'Add to Plan +';
                btn.classList.remove('in-plan');
            }
        });
    },

    currentTarget: (target) => {
        if (target) {
            document.getElementById('current-target-name').textContent = target.name;
            document.getElementById('current-target-mode').textContent =
                target.imaging_mode === 'planetary' ? '🪐 Planetary' : '🌌 Deep-Sky';
        }
    },

    executionProgress: (progress) => {
        document.getElementById('execution-progress-bar').style.width = `${progress}%`;
        document.getElementById('execution-progress-number').textContent = `${progress}%`;
    }
};

function triggerUIUpdate(key) {
    if (uiUpdateHandlers[key]) {
        uiUpdateHandlers[key](appState[key]);
    }
}
```

### Planetary vs Deep-Sky Mode Handling

**Object Type Detection:**

```python
# backend/app/models/catalog.py

class DSOTarget(BaseModel):
    catalog_id: str
    name: str
    object_type: str  # galaxy, nebula, cluster, planetary_nebula, planet
    ra_hours: float
    dec_degrees: float
    magnitude: float
    size_arcmin: float
    description: Optional[str]

    @property
    def is_planetary(self) -> bool:
        """Check if target requires planetary imaging mode."""
        return self.object_type == "planet" or self.catalog_id in [
            "MOON", "MARS", "JUPITER", "SATURN", "VENUS",
            "MERCURY", "URANUS", "NEPTUNE"
        ]

    @property
    def imaging_mode(self) -> str:
        """Return 'planetary' or 'deepsky' based on target type."""
        return "planetary" if self.is_planetary else "deepsky"
```

**Mode-Specific Execution:**

```python
# backend/app/services/execution_engine.py

async def _start_target_imaging(self, target: ScheduledTarget):
    """Start imaging with mode appropriate for target type."""

    if target.target.is_planetary:
        # Planetary mode: high FPS video capture
        self.logger.info(f"Starting planetary video capture for {target.target.name}")

        await self.seestar_client.configure_planetary_imaging(
            exposure_ms=10,      # Very short exposures
            gain=200,            # High gain for bright planets
            fps=30,              # Video frame rate
            duration_seconds=min(target.duration_minutes * 60, 300)  # Cap at 5min
        )

        await self.seestar_client.start_planet_scan()

    else:
        # Deep-sky mode: long exposure stacking
        self.logger.info(f"Starting deep-sky stacking for {target.target.name}")

        await self.seestar_client.iscope_start_stack(
            target_name=target.target.name,
            ra=target.target.ra_hours,
            dec=target.target.dec_degrees,
            exposure_sec=target.recommended_exposure,
            frames=target.recommended_frames,
            lp_filter=target.use_lp_filter
        )
```

**UI Differentiation:**

```javascript
// Catalog browser shows different capture info
function renderTargetCard(target) {
    const modeIcon = target.imaging_mode === 'planetary'
        ? '🪐 Planetary'
        : '🌌 Deep-Sky';

    const captureInfo = target.imaging_mode === 'planetary'
        ? `Video: ${target.recommended_duration}min @ ${target.recommended_fps}fps`
        : `Exposure: ${target.recommended_exposure}s × ${target.recommended_frames} frames`;

    return `
        <div class="catalog-card" data-catalog-id="${target.catalog_id}">
            <div class="card-header">
                <h3>${target.name}</h3>
                <span class="mode-badge">${modeIcon}</span>
            </div>
            <div class="card-body">
                <p>${target.object_type} • ${target.magnitude} mag • ${target.size_arcmin}'</p>
                <p>${captureInfo}</p>
                ${renderCaptureHistory(target.capture_history)}
                ${renderVisibility(target.visibility)}
            </div>
        </div>
    `;
}

// Observe tab shows mode-specific settings
function updateImagingSettings(target) {
    const planetaryPanel = document.getElementById('planetary-settings');
    const deepskyPanel = document.getElementById('deepsky-settings');

    if (target.imaging_mode === 'planetary') {
        planetaryPanel.style.display = 'block';
        deepskyPanel.style.display = 'none';

        // Populate planetary settings
        document.getElementById('planetary-fps').value = target.recommended_fps;
        document.getElementById('planetary-duration').value = target.recommended_duration;
        document.getElementById('planetary-gain').value = 200;

    } else {
        planetaryPanel.style.display = 'none';
        deepskyPanel.style.display = 'block';

        // Populate deep-sky settings
        document.getElementById('deepsky-exposure').value = target.recommended_exposure;
        document.getElementById('deepsky-frames').value = target.recommended_frames;
        document.getElementById('deepsky-gain').value = 80;
        document.getElementById('deepsky-lpfilter').checked = target.use_lp_filter;
        document.getElementById('deepsky-dithering').checked = target.recommended_frames > 50;
    }
}
```

---

## Implementation Summary

### Database Migrations

```bash
# Create migration for capture models
alembic revision --autogenerate -m "Add capture history and output files tables"
alembic upgrade head
```

### New Backend Files

```
backend/
├── app/
│   ├── models/
│   │   └── capture_models.py          # NEW: CaptureHistory, OutputFile
│   ├── services/
│   │   ├── file_scanner_service.py     # NEW: FITS scanning & fuzzy matching
│   │   ├── file_transfer_service.py    # NEW: Seestar file download
│   │   └── execution_engine.py         # NEW: Automated plan execution
│   ├── api/
│   │   ├── captures.py                 # NEW: Capture history endpoints
│   │   ├── seestar.py                  # NEW: Seestar control endpoints
│   │   ├── execution.py                # NEW: Execution management
│   │   └── targets.py                  # MODIFY: Add enrichment
│   └── websocket/
│       └── seestar_monitor.py          # NEW: Real-time device state
```

### Frontend Modifications

```
frontend/
└── index.html
    ├── Catalog tab         # MODIFY: Add plan builder, visibility, capture indicators
    ├── Planner tab         # MODIFY: Accept custom targets from catalog
    ├── Observe tab         # MAJOR OVERHAUL: Seestar integration
    └── Settings tab        # MODIFY: Add output directory, transfer settings
```

### Configuration Updates

```ini
# .env additions

# Output directory
OUTPUT_DIRECTORY=/mnt/synology/shared/Astronomy
AUTO_TRANSFER_FILES=true
AUTO_DELETE_AFTER_TRANSFER=true

# Seestar
SEESTAR_DEFAULT_IP=192.168.2.47
SEESTAR_TIMEOUT_SECONDS=30

# Capture thresholds
CAPTURE_COMPLETE_HOURS=3.0
CAPTURE_NEEDS_MORE_HOURS=1.0

# Execution
AUTO_RETRY_FAILED_SLEWS=true
MAX_SLEW_RETRIES=3
QUALITY_CHECK_INTERVAL=60
```

### Dependencies

```txt
# requirements.txt additions

thefuzz>=0.20.0          # Fuzzy string matching for catalog
python-Levenshtein>=0.20.0  # Faster fuzzy matching
websockets>=12.0         # Already present for Seestar
```

---

## Testing Strategy

### Unit Tests

- `test_file_scanner_service.py` - FITS metadata extraction, fuzzy matching
- `test_file_transfer_service.py` - Download simulation, directory organization
- `test_execution_engine.py` - State machine transitions, error handling
- `test_capture_models.py` - Model relationships, aggregate calculations

### Integration Tests

- `test_catalog_enrichment.py` - API returns visibility + capture history
- `test_plan_execution_flow.py` - Full workflow from plan → execute → transfer → history
- `test_websocket_monitor.py` - Real-time state updates

### Manual Testing Checklist

- [ ] Catalog browser: Add/remove targets from plan builder
- [ ] Catalog browser: Smart sorting by setting time, capture status
- [ ] Planner: Load custom targets from catalog plan builder
- [ ] Observe: Connect to Seestar, see real-time telemetry
- [ ] Observe: Execute automated plan (all phases)
- [ ] Observe: File transfer after target completion
- [ ] Observe: Planetary vs deep-sky mode switching
- [ ] Capture history: File scan finds and links FITS files
- [ ] Capture history: Aggregate stats update correctly
- [ ] Settings: Output directory configuration

---

## Migration Path

### Phase 1: Foundation (Backend)
1. Create database models and migrations
2. Implement FileScannerService
3. Implement FileTransferService
4. Add capture API endpoints
5. Run initial file scan on existing data

### Phase 2: Enhanced Catalog (User Value)
1. Extend `/api/targets` with visibility calculations
2. Extend `/api/targets` with capture history joins
3. Update catalog browser UI (plan builder, cards)
4. Add smart sorting and filtering

### Phase 3: Execution Engine (Core Functionality)
1. Implement ExecutionEngine with state machine
2. Add WebSocket for real-time monitoring
3. Add SSE for execution events
4. Connect file transfer on target completion

### Phase 4: Observe Tab (Polish)
1. Update Observe tab layout (sidebar + main)
2. Add automated execution controls
3. Add manual control panels
4. Add live telemetry display
5. Add execution status banner and progress

### Phase 5: Testing & Refinement
1. Run unit and integration tests
2. Manual testing with live telescope
3. Performance optimization (WebSocket reconnect, SSE buffering)
4. Documentation updates

---

## Success Criteria

✅ **Capture History**
- [ ] File scanner finds and links 100% of existing FITS files
- [ ] Capture history aggregates match manual calculations
- [ ] File transfer creates organized directory structure
- [ ] Suggested status correctly categorizes targets

✅ **Catalog Browser**
- [ ] Visibility calculations show accurate peak times
- [ ] Plan builder persists across page refresh
- [ ] Smart sorting prioritizes setting/uncaptured targets
- [ ] Capture indicators clearly show status

✅ **Observe Tab**
- [ ] Automated execution completes 5-target plan unattended
- [ ] Real-time telemetry updates < 2 second latency
- [ ] File transfer downloads all files and updates history
- [ ] Planetary mode successfully captures video
- [ ] Error recovery retries failed slews

✅ **Integration**
- [ ] Catalog → Plan → Observe → History → Catalog loop works
- [ ] Completed targets de-prioritized in next planning session
- [ ] Manual controls accessible during automated execution
- [ ] WebSocket reconnects automatically on disconnect

---

## Future Enhancements

**Beyond MVP:**
- Quality-based refocus: Auto-refocus if FWHM degrades during imaging
- Multi-telescope support: Manage multiple Seestar S50s simultaneously
- Weather integration: Pause execution on cloud cover increase
- Mosaic planning: Auto-generate multi-panel mosaics for large targets
- Social sharing: Export session summaries with captures
- Mobile app: iOS/Android companion for remote monitoring
- Cloud sync: Backup plans and capture history to cloud storage
- AI target recommendation: Suggest targets based on conditions and history

---

**Ready for Implementation!**
