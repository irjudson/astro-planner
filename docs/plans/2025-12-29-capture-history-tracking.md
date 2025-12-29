# Capture History Tracking Implementation Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Track capture history and integrate it with planning to avoid re-observing completed targets and prioritize targets needing more data.

**Architecture:** Add capture history tracking with file scanning service that links captured/processed files to targets and executions. Integrate with planner scoring to deprioritize captured targets and boost targets needing more data.

**Tech Stack:** SQLAlchemy (models), FastAPI (endpoints), FileScannerService (discovery), fuzzy matching (thefuzzywuzzy), FITS metadata extraction (astropy)

---

## Architecture Overview

### Core Components

1. **CaptureHistory Model** - Tracks aggregated capture statistics per target
   - Links to catalog targets via `catalog_id`
   - Stores total exposure time, frame count, sessions, last captured date
   - User-controlled status: `null` (captured), `complete`, `needs_more_data`
   - Auto-suggested status based on exposure thresholds

2. **OutputFile Model** - Links captured/processed files to targets and executions
   - File path (organized by target name in configurable output directory)
   - Links to `catalog_id`, `execution_id`, `execution_target_id`
   - Extracted metadata: exposure time, filter, temperature, quality metrics
   - File type: raw FITS, stacked, processed JPG/PNG/TIFF

3. **FileScannerService** - Discovers and links files to targets
   - Scans configurable output directory (default: `/mnt/synology/shared/Astronomy`)
   - Extracts target from FITS OBJECT header, falls back to directory name
   - Matches to catalog via fuzzy matching (handles "M 31" vs "M31" vs "NGC 224")
   - Updates CaptureHistory aggregate stats

4. **Enhanced Planner Integration**
   - Planning UI: "Include captured targets" checkbox with status filters
   - Score multipliers: captured (0.5x), complete (0.1x), needs_more_data (2.0x)
   - Display capture info on target cards: "Last captured 2025-12-15, 2.5hrs total"

---

## Data Models and Relationships

### CaptureHistory Model

**File:** `backend/app/models/capture_models.py`

```python
class CaptureHistory(Base):
    """Aggregated capture history for a catalog target."""

    __tablename__ = "capture_history"

    id = Column(Integer, primary_key=True)
    catalog_id = Column(String(50), unique=True, nullable=False, index=True)

    # Aggregate statistics
    total_exposure_seconds = Column(Integer, default=0)
    total_frames = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    first_captured_at = Column(DateTime, nullable=True)
    last_captured_at = Column(DateTime, nullable=True)

    # User-controlled status
    status = Column(String(20), nullable=True)  # null, 'complete', 'needs_more_data'
    suggested_status = Column(String(20), nullable=True)  # Auto-suggestion

    # Quality metrics (from best capture)
    best_fwhm = Column(Float, nullable=True)
    best_star_count = Column(Integer, nullable=True)

    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    output_files = relationship("OutputFile", back_populates="capture_history")
```

### OutputFile Model

**File:** `backend/app/models/capture_models.py`

```python
class OutputFile(Base):
    """Links captured/processed files to targets and executions."""

    __tablename__ = "output_files"

    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False, unique=True, index=True)
    file_type = Column(String(20), nullable=False)  # raw_fits, stacked_fits, jpg, png, tiff
    file_size_bytes = Column(BigInteger, nullable=False)

    # Target linking
    catalog_id = Column(String(50), nullable=False, index=True)
    catalog_id_confidence = Column(Float, default=1.0)  # Fuzzy match confidence

    # Execution linking (nullable - files may exist before executions tracked)
    execution_id = Column(Integer, ForeignKey("telescope_executions.id"), nullable=True)
    execution_target_id = Column(Integer, ForeignKey("telescope_execution_targets.id"), nullable=True)

    # FITS metadata
    exposure_seconds = Column(Float, nullable=True)
    filter_name = Column(String(10), nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    frame_count = Column(Integer, nullable=True)  # For stacked files

    # Quality metrics
    fwhm = Column(Float, nullable=True)
    star_count = Column(Integer, nullable=True)

    # Timestamps
    file_created_at = Column(DateTime, nullable=True)  # From filesystem
    discovered_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    capture_history = relationship("CaptureHistory", foreign_keys=[catalog_id],
                                   primaryjoin="OutputFile.catalog_id==CaptureHistory.catalog_id")
    execution = relationship("TelescopeExecution", back_populates="output_files")
    execution_target = relationship("TelescopeExecutionTarget", back_populates="output_files")
```

### Model Updates

**TelescopeExecution** - Add relationship:
```python
output_files = relationship("OutputFile", back_populates="execution")
```

**TelescopeExecutionTarget** - Add relationship:
```python
output_files = relationship("OutputFile", back_populates="execution_target")
```

---

## File Scanner Service

### FileScannerService

**File:** `backend/app/services/file_scanner_service.py`

**Responsibilities:**
1. Scan configurable output directory recursively for FITS/image files
2. Extract target identification from FITS headers (OBJECT field) with filename fallback
3. Fuzzy match extracted names to catalog (handle "M 31" vs "M31" vs "NGC 224")
4. Create/update OutputFile records
5. Recalculate CaptureHistory aggregate statistics
6. Auto-suggest status based on exposure thresholds

**Key Methods:**

```python
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass
from thefuzzywuzzy import fuzz
from astropy.io import fits
from sqlalchemy.orm import Session

@dataclass
class TargetMatch:
    """Result from extracting target name from file."""
    target_name: str
    source: str  # 'fits_header', 'directory', 'filename'
    confidence: float  # 0.0-1.0

@dataclass
class CatalogMatch:
    """Result from matching target name to catalog."""
    catalog_id: str
    match_score: int  # 0-100 from fuzzy match
    match_type: str  # 'exact_id', 'exact_name', 'fuzzy'

@dataclass
class ScanResult:
    """Result from directory scan."""
    files_scanned: int
    files_added: int
    files_updated: int
    targets_updated: int
    errors: List[str]
    duration_seconds: float

class FileScannerService:
    """Service for scanning output directory and tracking captured files."""

    def __init__(self, db: Session):
        self.db = db

    def scan_output_directory(self, output_dir: Path) -> ScanResult:
        """
        Scan directory and update database with discovered files.

        Args:
            output_dir: Root directory to scan (e.g., /mnt/synology/shared/Astronomy)

        Returns:
            ScanResult with statistics
        """
        # Walk directory tree for FITS/JPG/PNG/TIFF files
        # For each file:
        #   - Check if already in database (by file_path)
        #   - Extract target name (FITS header → directory → filename)
        #   - Fuzzy match to catalog
        #   - Extract metadata (exposure, filter, quality)
        #   - Create/update OutputFile record
        # Aggregate and update CaptureHistory for affected targets

    def extract_target_from_fits(self, fits_path: Path) -> TargetMatch:
        """
        Extract target name from FITS OBJECT header, fallback to path parsing.

        Args:
            fits_path: Path to FITS file

        Returns:
            TargetMatch with extracted name and confidence
        """
        # Try FITS OBJECT header first (confidence: 1.0)
        # Fall back to parent directory name (confidence: 0.8)
        # Fall back to filename parsing (confidence: 0.6)

    def extract_target_from_path(self, file_path: Path) -> TargetMatch:
        """Extract target name from file path (directory or filename)."""
        # Check parent directory name first
        # Parse filename if directory is generic

    def match_to_catalog(self, target_name: str, db: Session) -> Optional[CatalogMatch]:
        """
        Fuzzy match target name to catalog_id with confidence score.

        Args:
            target_name: Extracted target name (e.g., "M 31", "NGC 224")
            db: Database session

        Returns:
            CatalogMatch with catalog_id and match score, or None
        """
        # 1. Try exact match on catalog_id
        # 2. Try exact match on common_name
        # 3. Try fuzzy match with thefuzzywuzzy (threshold: 80)
        # Return best match with score

    def extract_fits_metadata(self, fits_path: Path) -> dict:
        """
        Extract metadata from FITS header.

        Returns:
            Dict with exposure_seconds, filter_name, temperature_celsius, etc.
        """

    def update_capture_history(self, catalog_id: str) -> CaptureHistory:
        """
        Recalculate aggregate stats from all OutputFiles for this target.

        Args:
            catalog_id: Catalog ID to update

        Returns:
            Updated CaptureHistory record
        """
        # Query all OutputFiles for catalog_id
        # Calculate:
        #   - SUM(exposure_seconds)
        #   - COUNT(files) as total_frames
        #   - COUNT(DISTINCT DATE(file_created_at)) as total_sessions
        #   - MIN(file_created_at), MAX(file_created_at)
        #   - MAX(star_count), MIN(fwhm) for quality
        # Suggest status based on total exposure
        # Update CaptureHistory record

    def suggest_status(self, total_exposure_seconds: int) -> Optional[str]:
        """
        Auto-suggest status based on total exposure time.

        Rules:
          - >= 7200s (2 hours) → 'complete'
          - < 1800s (30 min) → 'needs_more_data'
          - Otherwise → None (let user decide)
        """
```

---

## Planner Integration

### Enhanced Scoring

**File:** `backend/app/services/scheduler_service.py`

**Modified Method:**

```python
def calculate_target_score(
    self,
    target: DSOTarget,
    time: datetime,
    constraints: ObservingConstraints,
    capture_history: Optional[CaptureHistory] = None
) -> TargetScore:
    """
    Calculate score with capture history multiplier.

    Args:
        target: Target to score
        time: Time to evaluate
        constraints: Observing constraints (includes capture filtering)
        capture_history: Optional capture history for this target

    Returns:
        TargetScore with final score after capture multiplier
    """

    # Existing scoring logic (altitude, moon separation, transit, etc.)
    base_score = self._calculate_base_score(target, time, constraints)

    # Apply capture history multiplier if enabled
    if capture_history and constraints.apply_capture_filtering:
        multiplier = self._get_capture_multiplier(capture_history, constraints)
        final_score = base_score * multiplier
    else:
        final_score = base_score

    return TargetScore(
        total_score=final_score,
        # ... other fields
    )

def _get_capture_multiplier(
    self,
    history: CaptureHistory,
    constraints: ObservingConstraints
) -> float:
    """
    Get score multiplier based on capture status and user preferences.

    Args:
        history: Capture history record
        constraints: User's filtering preferences

    Returns:
        Multiplier to apply to base score
    """

    # User's actual status choice takes precedence over suggestion
    status = history.status or history.suggested_status

    # Apply multipliers from constraints
    if status == 'complete':
        return constraints.complete_multiplier  # Default: 0.1
    elif status == 'needs_more_data':
        return constraints.needs_more_data_multiplier  # Default: 2.0
    else:  # Captured but no specific status
        return constraints.captured_multiplier  # Default: 0.5
```

**Modified Method:**

```python
def schedule_session(
    self,
    targets: List[DSOTarget],
    location: Location,
    session: SessionInfo,
    constraints: ObservingConstraints,
    weather_forecasts: List[WeatherForecast],
) -> List[ScheduledTarget]:
    """Schedule targets with capture history integration."""

    # Load capture history for all targets if filtering enabled
    capture_histories = {}
    if constraints.apply_capture_filtering:
        catalog_ids = [t.catalog_id for t in targets]
        histories = self.db.query(CaptureHistory).filter(
            CaptureHistory.catalog_id.in_(catalog_ids)
        ).all()
        capture_histories = {h.catalog_id: h for h in histories}

    # Existing scheduling logic, but pass capture_history to calculate_target_score
    # Filter out targets based on status preferences
    if constraints.apply_capture_filtering:
        targets = [
            t for t in targets
            if self._should_include_target(t, capture_histories.get(t.catalog_id), constraints)
        ]

    # ... rest of scheduling logic

def _should_include_target(
    self,
    target: DSOTarget,
    history: Optional[CaptureHistory],
    constraints: ObservingConstraints
) -> bool:
    """Check if target should be included based on capture status filtering."""

    if not history:
        return True  # No history = not captured, always include

    status = history.status or history.suggested_status

    if status == 'complete' and not constraints.include_complete:
        return False
    if status == 'needs_more_data' and not constraints.include_needs_more_data:
        return False
    if status is None and not constraints.include_captured:
        return False

    return True
```

### Enhanced ObservingConstraints

**File:** `backend/app/models/models.py`

**Added Fields:**

```python
class ObservingConstraints(BaseModel):
    """Constraints for observing plan generation."""

    # ... existing fields (min_altitude_degrees, max_moon_illumination, etc.) ...

    # Capture history filtering
    apply_capture_filtering: bool = False  # "Include captured targets" checkbox
    include_complete: bool = True
    include_captured: bool = True
    include_needs_more_data: bool = True

    # Score multipliers
    complete_multiplier: float = 0.1
    captured_multiplier: float = 0.5
    needs_more_data_multiplier: float = 2.0
```

---

## Execution Tracking and File Creation

### Real-time Tracking During Execution

**File:** `backend/app/services/telescope_execution_service.py`

**New/Modified Methods:**

```python
class TelescopeExecutionService:

    def __init__(self, db: Session):
        self.db = db
        self.file_scanner = FileScannerService(db)

    def start_execution(self, plan: ObservingPlan, saved_plan_id: Optional[int]) -> TelescopeExecution:
        """
        Create execution record when starting observation.

        Args:
            plan: Observing plan to execute
            saved_plan_id: Optional ID of saved plan this execution is from

        Returns:
            Created TelescopeExecution record
        """
        execution = TelescopeExecution(
            execution_id=generate_uuid(),
            saved_plan_id=saved_plan_id,  # Link to saved plan if executed from one
            total_targets=len(plan.scheduled_targets),
            telescope_host=get_telescope_host(),
            # ... other fields
        )
        self.db.add(execution)

        # Create TelescopeExecutionTarget records for each scheduled target
        for idx, st in enumerate(plan.scheduled_targets):
            execution_target = TelescopeExecutionTarget(
                execution_id=execution.id,
                target_index=idx,
                target_name=st.target.common_name,
                catalog_id=st.target.catalog_id,
                # ... other fields from ScheduledTarget
            )
            self.db.add(execution_target)

        self.db.commit()
        return execution

    def on_capture_complete(
        self,
        execution_target_id: int,
        fits_path: Path,
        metadata: dict
    ):
        """
        Called when telescope saves a FITS file.

        Creates OutputFile record immediately and updates CaptureHistory.

        Args:
            execution_target_id: ID of execution target
            fits_path: Path where FITS was saved
            metadata: FITS header metadata
        """
        execution_target = self.db.query(TelescopeExecutionTarget).get(execution_target_id)

        # Create OutputFile record immediately
        output_file = OutputFile(
            file_path=str(fits_path),
            file_type='raw_fits',
            file_size_bytes=fits_path.stat().st_size,
            catalog_id=execution_target.catalog_id,
            execution_id=execution_target.execution_id,
            execution_target_id=execution_target_id,
            exposure_seconds=metadata.get('EXPTIME'),
            filter_name=metadata.get('FILTER'),
            temperature_celsius=metadata.get('CCD-TEMP'),
            file_created_at=datetime.fromtimestamp(fits_path.stat().st_mtime),
            catalog_id_confidence=1.0,  # Directly from execution, fully confident
        )
        self.db.add(output_file)
        self.db.commit()

        # Update CaptureHistory in real-time
        self.file_scanner.update_capture_history(execution_target.catalog_id)
```

### Post-Processing Integration

**File:** `backend/app/services/processing_service.py` (or tasks)

**Modified Method:**

```python
def on_processing_complete(
    self,
    job: ProcessingJob,
    output_files: List[Path]
):
    """
    Link processed files to original raw FITS execution.

    Args:
        job: Completed processing job
        output_files: List of generated output files (JPG/PNG/TIFF)
    """

    # Find the raw FITS OutputFile record
    raw_file = self.db.query(OutputFile).filter_by(
        file_path=str(job.input_file_path)
    ).first()

    if not raw_file:
        # File not tracked (possibly pre-existing), try to scan it
        logger.warning(f"Raw FITS not tracked: {job.input_file_path}")
        return

    for output_path in output_files:
        file_type = self._detect_type(output_path)  # jpg, png, tiff, stacked_fits

        processed_file = OutputFile(
            file_path=str(output_path),
            file_type=file_type,
            file_size_bytes=output_path.stat().st_size,
            catalog_id=raw_file.catalog_id,
            execution_id=raw_file.execution_id,
            execution_target_id=raw_file.execution_target_id,
            catalog_id_confidence=raw_file.catalog_id_confidence,
            file_created_at=datetime.fromtimestamp(output_path.stat().st_mtime),
            # Inherit metadata from raw file
            exposure_seconds=raw_file.exposure_seconds,
            filter_name=raw_file.filter_name,
        )
        self.db.add(processed_file)

    self.db.commit()

def _detect_type(self, path: Path) -> str:
    """Detect file type from extension."""
    ext = path.suffix.lower()
    if ext in ['.fit', '.fits']:
        return 'stacked_fits'
    elif ext in ['.jpg', '.jpeg']:
        return 'jpg'
    elif ext == '.png':
        return 'png'
    elif ext in ['.tif', '.tiff']:
        return 'tiff'
    else:
        return 'unknown'
```

---

## API Endpoints and UI Integration

### New API Router

**File:** `backend/app/api/capture_history.py`

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import CaptureHistory, OutputFile
from app.services.file_scanner_service import FileScannerService, ScanResult
from pathlib import Path
import os

router = APIRouter(prefix="/api/capture", tags=["capture-history"])

@router.post("/scan", response_model=ScanResult)
async def scan_output_directory(
    background: bool = False,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Trigger file scanner to discover new captures.

    Args:
        background: If True, run scan in background

    Returns:
        ScanResult with files found and targets updated
    """
    output_dir = Path(os.getenv("OUTPUT_DIR", "/mnt/synology/shared/Astronomy"))

    if not output_dir.exists():
        raise HTTPException(status_code=404, detail=f"Output directory not found: {output_dir}")

    scanner = FileScannerService(db)

    if background:
        background_tasks.add_task(scanner.scan_output_directory, output_dir)
        return {"message": "Scan started in background"}
    else:
        result = scanner.scan_output_directory(output_dir)
        return result

@router.get("/history", response_model=List[dict])
async def list_capture_history(
    object_types: Optional[str] = None,  # Comma-separated
    status: Optional[str] = None,
    min_exposure: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List all capture history with filtering.

    Args:
        object_types: Filter by object types (comma-separated)
        status: Filter by status (complete, needs_more_data, captured)
        min_exposure: Minimum total exposure in seconds

    Returns:
        List of capture history records with target details
    """
    query = db.query(CaptureHistory)

    if status:
        if status == 'captured':
            query = query.filter(CaptureHistory.status.is_(None))
        else:
            query = query.filter(CaptureHistory.status == status)

    if min_exposure:
        query = query.filter(CaptureHistory.total_exposure_seconds >= min_exposure)

    histories = query.all()

    # Join with catalog to get target details
    # ... implementation

    return histories

@router.get("/history/{catalog_id}")
async def get_capture_details(
    catalog_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed capture history for specific target.

    Returns:
        CaptureHistory + list of OutputFiles grouped by session
    """
    history = db.query(CaptureHistory).filter_by(catalog_id=catalog_id).first()

    if not history:
        raise HTTPException(status_code=404, detail=f"No capture history for {catalog_id}")

    files = db.query(OutputFile).filter_by(catalog_id=catalog_id).order_by(
        OutputFile.file_created_at.desc()
    ).all()

    return {
        "history": history,
        "files": files,
        "total_files": len(files)
    }

@router.patch("/history/{catalog_id}/status")
async def update_capture_status(
    catalog_id: str,
    status: Optional[str] = None,  # null, 'complete', 'needs_more_data'
    db: Session = Depends(get_db)
):
    """
    User updates capture status (complete/needs_more_data/null).

    Args:
        catalog_id: Target catalog ID
        status: New status (null to clear)

    Returns:
        Updated CaptureHistory
    """
    history = db.query(CaptureHistory).filter_by(catalog_id=catalog_id).first()

    if not history:
        raise HTTPException(status_code=404, detail=f"No capture history for {catalog_id}")

    # Validate status
    valid_statuses = [None, 'complete', 'needs_more_data']
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    history.status = status
    # Clear suggested_status once user makes explicit choice
    history.suggested_status = None

    db.commit()
    db.refresh(history)

    return history

@router.get("/files/{catalog_id}")
async def list_target_files(
    catalog_id: str,
    db: Session = Depends(get_db)
):
    """
    List all output files for a target.

    Returns:
        OutputFiles grouped by session/date
    """
    files = db.query(OutputFile).filter_by(catalog_id=catalog_id).order_by(
        OutputFile.file_created_at.desc()
    ).all()

    # Group by date
    from collections import defaultdict
    grouped = defaultdict(list)
    for f in files:
        date_key = f.file_created_at.date() if f.file_created_at else "unknown"
        grouped[str(date_key)].append(f)

    return {
        "catalog_id": catalog_id,
        "total_files": len(files),
        "sessions": grouped
    }
```

**Add to main router:**

```python
# backend/app/api/routes.py
from app.api import capture_history

app.include_router(capture_history.router)
```

### Frontend Changes

**Planner Tab** (`frontend/src/components/Planner.tsx`):

Add capture filtering controls:

```typescript
// New state
const [includeCapturedTargets, setIncludeCapturedTargets] = useState(false);
const [includeComplete, setIncludeComplete] = useState(true);
const [includeCaptured, setIncludeCaptured] = useState(true);
const [includeNeedsMoreData, setIncludeNeedsMoreData] = useState(true);

// UI section (before "Generate Plan" button)
<div className="capture-filtering">
  <label>
    <input
      type="checkbox"
      checked={includeCapturedTargets}
      onChange={(e) => setIncludeCapturedTargets(e.target.checked)}
    />
    Include already captured targets
  </label>

  {includeCapturedTargets && (
    <div className="capture-options">
      <label>
        <input type="checkbox" checked={includeNeedsMoreData}
               onChange={(e) => setIncludeNeedsMoreData(e.target.checked)} />
        Needs More Data (2.0x priority)
      </label>
      <label>
        <input type="checkbox" checked={includeCaptured}
               onChange={(e) => setIncludeCaptured(e.target.checked)} />
        Captured (0.5x priority)
      </label>
      <label>
        <input type="checkbox" checked={includeComplete}
               onChange={(e) => setIncludeComplete(e.target.checked)} />
        Complete (0.1x priority)
      </label>
    </div>
  )}
</div>

// Pass to API in constraints
const constraints = {
  // ... existing fields
  apply_capture_filtering: includeCapturedTargets,
  include_complete: includeComplete,
  include_captured: includeCaptured,
  include_needs_more_data: includeNeedsMoreData,
};
```

**Target Cards** - Display capture info:

```typescript
// Fetch capture history when loading plan
const [captureHistories, setCaptureHistories] = useState<Map<string, CaptureHistory>>(new Map());

// In target card render
{captureHistories.has(target.catalog_id) && (
  <div className="capture-badge">
    <span className={`status-${history.status || 'captured'}`}>
      {history.status === 'complete' ? '✓ Complete' :
       history.status === 'needs_more_data' ? '⚠ Needs More Data' :
       '📷 Captured'}
    </span>
    <div className="capture-tooltip">
      Last captured {formatDate(history.last_captured_at)}<br/>
      {formatDuration(history.total_exposure_seconds)} total across {history.total_sessions} sessions
    </div>
  </div>
)}
```

**New "Capture History" Tab** (`frontend/src/components/CaptureHistory.tsx`):

```typescript
export function CaptureHistory() {
  const [histories, setHistories] = useState([]);
  const [scanning, setScanning] = useState(false);

  const scanFiles = async () => {
    setScanning(true);
    const result = await fetch('/api/capture/scan', { method: 'POST' }).then(r => r.json());
    setScanning(false);
    loadHistories();
  };

  const loadHistories = async () => {
    const data = await fetch('/api/capture/history').then(r => r.json());
    setHistories(data);
  };

  const updateStatus = async (catalogId: string, status: string | null) => {
    await fetch(`/api/capture/history/${catalogId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
      headers: { 'Content-Type': 'application/json' }
    });
    loadHistories();
  };

  return (
    <div className="capture-history">
      <div className="toolbar">
        <button onClick={scanFiles} disabled={scanning}>
          {scanning ? 'Scanning...' : 'Scan for New Files'}
        </button>
      </div>

      <table>
        <thead>
          <tr>
            <th>Target</th>
            <th>Status</th>
            <th>Total Exposure</th>
            <th>Sessions</th>
            <th>Last Captured</th>
            <th>Files</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {histories.map(h => (
            <tr key={h.catalog_id}>
              <td>{h.target_name}</td>
              <td>
                <select value={h.status || ''}
                        onChange={(e) => updateStatus(h.catalog_id, e.target.value || null)}>
                  <option value="">Captured</option>
                  <option value="needs_more_data">Needs More Data</option>
                  <option value="complete">Complete</option>
                </select>
              </td>
              <td>{formatDuration(h.total_exposure_seconds)}</td>
              <td>{h.total_sessions}</td>
              <td>{formatDate(h.last_captured_at)}</td>
              <td><Link to={`/capture/${h.catalog_id}`}>{h.total_frames} files</Link></td>
              <td><button>View Details</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Output directory for captured/processed files
OUTPUT_DIR=/mnt/synology/shared/Astronomy
```

### Settings Model

**File:** `backend/app/models/settings_models.py`

Add default settings:

```python
{
    "key": "capture.output_dir",
    "value": "/mnt/synology/shared/Astronomy",
    "description": "Directory where captured and processed files are stored",
    "category": "capture"
},
{
    "key": "capture.auto_scan_on_startup",
    "value": "false",
    "description": "Automatically scan output directory on application startup",
    "category": "capture"
},
```

---

## Database Migration

**File:** `backend/alembic/versions/YYYYMMDD_add_capture_history.py`

```python
"""Add capture history and output files tables

Revision ID: xxxxx
Revises: previous_revision
Create Date: 2025-12-29
"""

def upgrade():
    # Create capture_history table
    op.create_table(
        'capture_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('catalog_id', sa.String(50), nullable=False),
        sa.Column('total_exposure_seconds', sa.Integer(), default=0),
        sa.Column('total_frames', sa.Integer(), default=0),
        sa.Column('total_sessions', sa.Integer(), default=0),
        sa.Column('first_captured_at', sa.DateTime(), nullable=True),
        sa.Column('last_captured_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('suggested_status', sa.String(20), nullable=True),
        sa.Column('best_fwhm', sa.Float(), nullable=True),
        sa.Column('best_star_count', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('catalog_id')
    )
    op.create_index('ix_capture_history_catalog_id', 'capture_history', ['catalog_id'])

    # Create output_files table
    op.create_table(
        'output_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('catalog_id', sa.String(50), nullable=False),
        sa.Column('catalog_id_confidence', sa.Float(), default=1.0),
        sa.Column('execution_id', sa.Integer(), nullable=True),
        sa.Column('execution_target_id', sa.Integer(), nullable=True),
        sa.Column('exposure_seconds', sa.Float(), nullable=True),
        sa.Column('filter_name', sa.String(10), nullable=True),
        sa.Column('temperature_celsius', sa.Float(), nullable=True),
        sa.Column('frame_count', sa.Integer(), nullable=True),
        sa.Column('fwhm', sa.Float(), nullable=True),
        sa.Column('star_count', sa.Integer(), nullable=True),
        sa.Column('file_created_at', sa.DateTime(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), default=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['execution_id'], ['telescope_executions.id']),
        sa.ForeignKeyConstraint(['execution_target_id'], ['telescope_execution_targets.id']),
        sa.UniqueConstraint('file_path')
    )
    op.create_index('ix_output_files_file_path', 'output_files', ['file_path'])
    op.create_index('ix_output_files_catalog_id', 'output_files', ['catalog_id'])

    # Add relationships to telescope_executions
    # (relationships are Python-side only, no schema changes needed)

def downgrade():
    op.drop_table('output_files')
    op.drop_table('capture_history')
```

---

## Testing Strategy

### Unit Tests

**File:** `backend/tests/unit/services/test_file_scanner_service.py`

Test cases:
- `test_extract_target_from_fits_header()` - FITS OBJECT header extraction
- `test_extract_target_from_directory()` - Directory name fallback
- `test_extract_target_from_filename()` - Filename parsing fallback
- `test_match_to_catalog_exact_id()` - Exact catalog_id match
- `test_match_to_catalog_exact_name()` - Exact common_name match
- `test_match_to_catalog_fuzzy()` - Fuzzy matching ("M 31" → "M31")
- `test_update_capture_history_aggregation()` - Aggregate stats calculation
- `test_suggest_status_complete()` - Status suggestion for 2+ hours
- `test_suggest_status_needs_more_data()` - Status suggestion for < 30 min

**File:** `backend/tests/unit/services/test_scheduler_service.py`

Test cases:
- `test_capture_multiplier_complete()` - Score multiplier for complete targets
- `test_capture_multiplier_needs_more_data()` - Score boost for targets needing data
- `test_filter_complete_targets()` - Exclude complete when unchecked
- `test_include_all_captured_targets()` - Include all when checked

### Integration Tests

**File:** `backend/tests/integration/test_capture_history_api.py`

Test cases:
- `test_scan_output_directory()` - Full scan workflow
- `test_update_capture_status()` - User status update
- `test_plan_with_capture_filtering()` - End-to-end plan generation with filtering

---

## Implementation Phases

### Phase 1: Data Models and Migration
1. Create `capture_models.py` with CaptureHistory and OutputFile
2. Create database migration
3. Run migration and verify tables created
4. Update `__init__.py` exports

### Phase 2: File Scanner Service
1. Implement FileScannerService core logic
2. Add FITS metadata extraction
3. Add fuzzy catalog matching
4. Add aggregate stats calculation
5. Unit test all methods

### Phase 3: API Endpoints
1. Create `capture_history.py` router
2. Implement scan endpoint
3. Implement history list/detail endpoints
4. Implement status update endpoint
5. Register router in main app

### Phase 4: Planner Integration
1. Add ObservingConstraints fields
2. Modify scheduler scoring logic
3. Add capture history loading
4. Add filtering logic
5. Unit test scoring and filtering

### Phase 5: Execution Tracking
1. Modify TelescopeExecutionService
2. Add real-time OutputFile creation
3. Add processing integration
4. Test execution workflow

### Phase 6: Frontend UI
1. Add capture filtering controls to Planner tab
2. Add capture badges to target cards
3. Create CaptureHistory tab component
4. Add status update UI
5. Add file browser for target details

### Phase 7: Testing and Polish
1. Run full test suite
2. Test scan on real data directory
3. Test end-to-end planning workflow
4. Fix bugs and edge cases
5. Documentation and user guide

---

## Future Enhancements

- **Smart scheduling**: "Fill in gaps with captured targets if needed"
- **Quality-based re-observation**: Auto-suggest re-capture if FWHM > threshold
- **Capture goals**: "Need 3 hours on M31" → track progress toward goal
- **Catalog browser**: Filter catalog by "not yet captured"
- **Statistics dashboard**: Total targets captured, total exposure time, etc.
- **Export capture log**: CSV/JSON export of all capture history
