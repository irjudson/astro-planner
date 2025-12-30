# Capture History Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement capture history tracking foundation - database models, file scanner service, file transfer service, and API endpoints.

**Architecture:** SQLAlchemy models for aggregate capture stats and file records, FileScannerService for FITS metadata extraction with fuzzy target matching, FileTransferService for automated Seestar downloads, RESTful API for capture management.

**Tech Stack:** SQLAlchemy, Alembic, Astropy (FITS), thefuzz (fuzzy matching), FastAPI, pytest

---

## Task 1: Create CaptureHistory Database Model

**Files:**
- Create: `backend/app/models/capture_models.py`
- Test: `backend/tests/unit/test_capture_models.py`

**Step 1: Write the failing test**

Create test file with model instantiation test:

```python
"""Tests for capture history models."""

import pytest
from datetime import datetime
from app.models.capture_models import CaptureHistory


def test_capture_history_creation():
    """Test creating a CaptureHistory record."""
    capture = CaptureHistory(
        catalog_id="M31",
        total_exposure_seconds=7200,  # 2 hours
        total_frames=720,
        total_sessions=3,
        first_captured_at=datetime(2025, 12, 15, 20, 0),
        last_captured_at=datetime(2025, 12, 20, 22, 30),
        status="needs_more_data",
        suggested_status="needs_more_data",
        best_fwhm=2.3,
        best_star_count=2847
    )

    assert capture.catalog_id == "M31"
    assert capture.total_exposure_seconds == 7200
    assert capture.total_frames == 720
    assert capture.status == "needs_more_data"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_capture_models.py::test_capture_history_creation -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.models.capture_models'"

**Step 3: Write minimal implementation**

Create `backend/app/models/capture_models.py`:

```python
"""Capture history database models."""

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

    # Relationships (will add when OutputFile exists)
    # output_files = relationship("OutputFile", back_populates="capture_history")
```

Update `backend/app/models/__init__.py` to export the model:

```python
# Add to existing imports
from app.models.capture_models import CaptureHistory

# Add to __all__
__all__ = [
    # ... existing exports ...
    "CaptureHistory",
]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_capture_models.py::test_capture_history_creation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/capture_models.py backend/app/models/__init__.py backend/tests/unit/test_capture_models.py
git commit -m "feat: add CaptureHistory model for aggregate capture statistics

- SQLAlchemy model with catalog_id as unique key
- Tracks total exposure, frames, sessions
- Stores status (user-controlled) and suggested_status (auto-calculated)
- Quality metrics: best FWHM and star count
- Timestamps for first/last capture and updates"
```

---

## Task 2: Create OutputFile Database Model

**Files:**
- Modify: `backend/app/models/capture_models.py`
- Modify: `backend/tests/unit/test_capture_models.py`

**Step 1: Write the failing test**

Add to test file:

```python
from app.models.capture_models import CaptureHistory, OutputFile


def test_output_file_creation():
    """Test creating an OutputFile record."""
    output_file = OutputFile(
        file_path="/mnt/astronomy/M31/2025-12-29/M31_stacked.fit",
        file_type="stacked_fits",
        file_size_bytes=458392847,
        catalog_id="M31",
        catalog_id_confidence=0.95,
        execution_id=None,
        execution_target_id=None,
        exposure_seconds=10,
        filter_name="LP",
        temperature_celsius=-10.0,
        gain=80,
        fwhm=2.3,
        star_count=2847,
        observation_date=datetime(2025, 12, 29, 21, 45)
    )

    assert output_file.file_path == "/mnt/astronomy/M31/2025-12-29/M31_stacked.fit"
    assert output_file.file_type == "stacked_fits"
    assert output_file.catalog_id == "M31"
    assert output_file.catalog_id_confidence == 0.95


def test_capture_history_output_file_relationship():
    """Test relationship between CaptureHistory and OutputFile."""
    # This will be tested after relationships are set up
    pass  # Placeholder for now
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_capture_models.py::test_output_file_creation -v`
Expected: FAIL with "ImportError: cannot import name 'OutputFile'"

**Step 3: Write minimal implementation**

Add to `backend/app/models/capture_models.py`:

```python
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

    # Relationships (will add back_populates when ready)
    # capture_history = relationship("CaptureHistory", back_populates="output_files")
```

Update `backend/app/models/__init__.py`:

```python
from app.models.capture_models import CaptureHistory, OutputFile

__all__ = [
    # ... existing ...
    "CaptureHistory",
    "OutputFile",
]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_capture_models.py::test_output_file_creation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/capture_models.py backend/app/models/__init__.py backend/tests/unit/test_capture_models.py
git commit -m "feat: add OutputFile model for linking files to targets

- Links FITS/image files to catalog targets via fuzzy matching
- Stores file metadata: path, type, size
- Extracts FITS metadata: exposure, filter, temperature, gain
- Quality metrics: FWHM, star count
- Links to executions (nullable for pre-existing files)"
```

---

## Task 3: Create Database Migration

**Files:**
- Create: `backend/alembic/versions/XXXX_add_capture_history_tables.py` (autogenerated)

**Step 1: Generate migration**

Run: `cd backend && alembic revision --autogenerate -m "Add capture history and output files tables"`

**Step 2: Review generated migration**

Check the generated file in `backend/alembic/versions/` to ensure:
- `capture_history` table created with all columns
- `output_files` table created with all columns
- Indexes on `catalog_id` fields
- Foreign keys to `telescope_executions` and `execution_targets` (if those tables exist)

**Step 3: Run migration**

Run: `cd backend && alembic upgrade head`
Expected: Migration applies successfully

**Step 4: Verify migration**

Run: `cd backend && alembic current`
Expected: Shows the new migration as current

**Step 5: Test downgrade/upgrade cycle**

```bash
cd backend
alembic downgrade -1
alembic upgrade head
```

Expected: Both commands succeed

**Step 6: Commit**

```bash
git add backend/alembic/versions/*_add_capture_history_tables.py
git commit -m "feat: add database migration for capture history tables

- Creates capture_history table with aggregate stats
- Creates output_files table with file metadata
- Indexes on catalog_id for efficient lookups
- Foreign keys to telescope execution tables"
```

---

## Task 4: Add Configuration Settings

**Files:**
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/unit/test_config.py` (create if needed)

**Step 1: Write the failing test**

Create `backend/tests/unit/test_config.py` if it doesn't exist:

```python
"""Tests for configuration settings."""

import pytest
from app.core.config import Settings


def test_capture_settings_defaults():
    """Test capture-related configuration defaults."""
    settings = Settings()

    assert settings.OUTPUT_DIRECTORY == "/mnt/synology/shared/Astronomy"
    assert settings.AUTO_TRANSFER_FILES is True
    assert settings.AUTO_DELETE_AFTER_TRANSFER is True
    assert settings.CAPTURE_COMPLETE_HOURS == 3.0
    assert settings.CAPTURE_NEEDS_MORE_HOURS == 1.0
    assert settings.FILE_SCAN_EXTENSIONS == ['.fit', '.fits', '.jpg', '.png', '.tiff', '.avi']
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_config.py::test_capture_settings_defaults -v`
Expected: FAIL with "AttributeError: 'Settings' object has no attribute 'OUTPUT_DIRECTORY'"

**Step 3: Add configuration settings**

Modify `backend/app/core/config.py`:

```python
from typing import List

class Settings(BaseSettings):
    # ... existing settings ...

    # Output directory for capture files
    OUTPUT_DIRECTORY: str = "/mnt/synology/shared/Astronomy"
    AUTO_TRANSFER_FILES: bool = True
    AUTO_DELETE_AFTER_TRANSFER: bool = True

    # Capture thresholds for status suggestions
    CAPTURE_COMPLETE_HOURS: float = 3.0
    CAPTURE_NEEDS_MORE_HOURS: float = 1.0

    # File scanner settings
    FILE_SCAN_ON_STARTUP: bool = False
    FILE_SCAN_EXTENSIONS: List[str] = ['.fit', '.fits', '.jpg', '.png', '.tiff', '.avi']
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_config.py::test_capture_settings_defaults -v`
Expected: PASS

**Step 5: Update .env.example**

Add to `.env.example`:

```ini
# Capture History Settings
OUTPUT_DIRECTORY=/mnt/synology/shared/Astronomy
AUTO_TRANSFER_FILES=true
AUTO_DELETE_AFTER_TRANSFER=true
CAPTURE_COMPLETE_HOURS=3.0
CAPTURE_NEEDS_MORE_HOURS=1.0
FILE_SCAN_ON_STARTUP=false
```

**Step 6: Commit**

```bash
git add backend/app/core/config.py backend/tests/unit/test_config.py .env.example
git commit -m "feat: add configuration settings for capture history

- OUTPUT_DIRECTORY for organized file storage
- AUTO_TRANSFER_FILES and AUTO_DELETE flags
- Capture status thresholds (hours of exposure)
- File scanner settings and extensions list"
```

---

## Task 5: Implement FileScannerService - Setup and Structure

**Files:**
- Create: `backend/app/services/file_scanner_service.py`
- Create: `backend/tests/unit/test_file_scanner_service.py`

**Step 1: Write the failing test (basic structure)**

```python
"""Tests for file scanner service."""

import pytest
from pathlib import Path
from app.services.file_scanner_service import FileScannerService


def test_file_scanner_service_init():
    """Test FileScannerService initialization."""
    scanner = FileScannerService()
    assert scanner is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py::test_file_scanner_service_init -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create minimal service structure**

Create `backend/app/services/file_scanner_service.py`:

```python
"""File scanner service for discovering and linking capture files."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.config import settings
from app.models.capture_models import CaptureHistory, OutputFile


class FileScannerService:
    """Discovers and links capture files to catalog targets."""

    def __init__(self):
        """Initialize the file scanner service."""
        self.logger = logging.getLogger(__name__)
        self.settings = settings
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py::test_file_scanner_service_init -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/file_scanner_service.py backend/tests/unit/test_file_scanner_service.py
git commit -m "feat: create FileScannerService skeleton

- Initialize service with logger and settings
- Prepare for FITS metadata extraction
- Prepare for fuzzy target matching"
```

---

## Task 6: Implement Fuzzy Matching for Target Names

**Files:**
- Modify: `backend/app/services/file_scanner_service.py`
- Modify: `backend/tests/unit/test_file_scanner_service.py`

**Step 1: Write the failing test**

Add to test file:

```python
from app.services.catalog_service import CatalogService


@pytest.fixture
def scanner_with_catalog():
    """Create scanner with catalog service."""
    scanner = FileScannerService()
    catalog = CatalogService()
    scanner.catalog = catalog
    return scanner


def test_fuzzy_match_exact(scanner_with_catalog):
    """Test fuzzy matching with exact catalog ID."""
    catalog_id, confidence = scanner_with_catalog._fuzzy_match_catalog("M31")
    assert catalog_id == "M31"
    assert confidence == 1.0


def test_fuzzy_match_with_space(scanner_with_catalog):
    """Test fuzzy matching handles spaces."""
    catalog_id, confidence = scanner_with_catalog._fuzzy_match_catalog("M 31")
    assert catalog_id == "M31"
    assert confidence > 0.9


def test_fuzzy_match_alternate_name(scanner_with_catalog):
    """Test fuzzy matching with alternate name."""
    catalog_id, confidence = scanner_with_catalog._fuzzy_match_catalog("Andromeda")
    assert catalog_id == "M31"
    assert confidence > 0.7


def test_fuzzy_match_no_match(scanner_with_catalog):
    """Test fuzzy matching returns None for poor matches."""
    result = scanner_with_catalog._fuzzy_match_catalog("XYZ999NonExistent")
    assert result is None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py::test_fuzzy_match_exact -v`
Expected: FAIL with "AttributeError: '_fuzzy_match_catalog'"

**Step 3: Implement fuzzy matching**

Add to `FileScannerService`:

```python
from thefuzz import fuzz, process
from app.services.catalog_service import CatalogService


class FileScannerService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.catalog = CatalogService()

    def _fuzzy_match_catalog(self, target_name: str) -> Optional[Tuple[str, float]]:
        """
        Fuzzy match target name to catalog.

        Returns (catalog_id, confidence_score) or None.
        Uses thefuzz library with token_sort_ratio.
        Handles: "M 31" vs "M31" vs "NGC 224" vs "Andromeda"
        """
        if not target_name:
            return None

        # Get all catalog targets
        targets = self.catalog.get_all_targets()

        # Exact match first (case insensitive)
        for target in targets:
            if target.catalog_id.lower() == target_name.lower():
                return (target.catalog_id, 1.0)

        # Build search list: catalog_ids and names
        search_list = []
        target_map = {}

        for target in targets:
            search_list.append(target.catalog_id)
            target_map[target.catalog_id] = target.catalog_id

            search_list.append(target.name)
            target_map[target.name] = target.catalog_id

        # Fuzzy match using token_sort_ratio (handles word order)
        best_match, score = process.extractOne(
            target_name,
            search_list,
            scorer=fuzz.token_sort_ratio
        )

        # Confidence threshold: 70% minimum
        if score >= 70:
            catalog_id = target_map[best_match]
            confidence = score / 100.0
            return (catalog_id, confidence)

        return None
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py -v -k fuzzy`
Expected: All fuzzy match tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/file_scanner_service.py backend/tests/unit/test_file_scanner_service.py
git commit -m "feat: add fuzzy matching for catalog target names

- Uses thefuzz with token_sort_ratio for flexible matching
- Handles variations: 'M 31' vs 'M31' vs 'Andromeda'
- Returns confidence score for match quality
- 70% threshold for accepting matches"
```

---

## Task 7: Implement FITS Metadata Extraction

**Files:**
- Modify: `backend/app/services/file_scanner_service.py`
- Modify: `backend/tests/unit/test_file_scanner_service.py`
- Create: `backend/tests/fixtures/test_fits_file.fit` (test fixture)

**Step 1: Create test FITS file fixture**

Create minimal FITS file for testing (or mock the astropy.io.fits calls):

```python
# Add to test file
from unittest.mock import Mock, patch
from astropy.io import fits


@pytest.fixture
def mock_fits_file(tmp_path):
    """Create a mock FITS file with test headers."""
    fits_path = tmp_path / "test.fit"

    # Create minimal FITS with headers
    hdu = fits.PrimaryHDU()
    hdu.header['OBJECT'] = 'M31'
    hdu.header['EXPTIME'] = 10.0
    hdu.header['FILTER'] = 'LP'
    hdu.header['CCD-TEMP'] = -10.0
    hdu.header['GAIN'] = 80
    hdu.header['DATE-OBS'] = '2025-12-29T21:45:00'

    hdul = fits.HDUList([hdu])
    hdul.writeto(fits_path)

    return fits_path


def test_extract_fits_metadata(scanner_with_catalog, mock_fits_file):
    """Test extracting metadata from FITS file."""
    metadata = scanner_with_catalog._extract_fits_metadata(str(mock_fits_file))

    assert metadata['target_name'] == 'M31'
    assert metadata['exposure_seconds'] == 10
    assert metadata['filter_name'] == 'LP'
    assert metadata['temperature_celsius'] == -10.0
    assert metadata['gain'] == 80
    assert 'observation_date' in metadata
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py::test_extract_fits_metadata -v`
Expected: FAIL with "AttributeError: '_extract_fits_metadata'"

**Step 3: Implement FITS metadata extraction**

Add to `FileScannerService`:

```python
from astropy.io import fits
from datetime import datetime


def _extract_fits_metadata(self, fits_path: str) -> Dict[str, Any]:
    """Extract metadata from FITS header using Astropy."""
    try:
        with fits.open(fits_path) as hdul:
            header = hdul[0].header

            metadata = {}

            # Target name
            metadata['target_name'] = header.get('OBJECT', '').strip()

            # Exposure time (in seconds)
            exptime = header.get('EXPTIME', header.get('EXPOSURE', 0))
            metadata['exposure_seconds'] = int(float(exptime)) if exptime else None

            # Filter
            metadata['filter_name'] = header.get('FILTER', '').strip() or None

            # Temperature (Celsius)
            temp = header.get('CCD-TEMP', header.get('SET-TEMP', None))
            metadata['temperature_celsius'] = float(temp) if temp is not None else None

            # Gain
            gain = header.get('GAIN', None)
            metadata['gain'] = int(gain) if gain is not None else None

            # Observation date/time
            date_obs = header.get('DATE-OBS', '')
            if date_obs:
                try:
                    # Parse ISO format: 2025-12-29T21:45:00
                    metadata['observation_date'] = datetime.fromisoformat(date_obs.replace('Z', '+00:00'))
                except ValueError:
                    metadata['observation_date'] = None
            else:
                metadata['observation_date'] = None

            return metadata

    except Exception as e:
        self.logger.error(f"Error extracting FITS metadata from {fits_path}: {e}")
        return {
            'target_name': '',
            'exposure_seconds': None,
            'filter_name': None,
            'temperature_celsius': None,
            'gain': None,
            'observation_date': None
        }
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py::test_extract_fits_metadata -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/file_scanner_service.py backend/tests/unit/test_file_scanner_service.py
git commit -m "feat: add FITS metadata extraction using Astropy

- Extracts OBJECT, EXPTIME, FILTER, CCD-TEMP, GAIN
- Parses DATE-OBS into datetime
- Handles missing headers gracefully
- Returns structured metadata dictionary"
```

---

## Task 8: Implement Quality Metrics Calculation (Placeholder)

**Files:**
- Modify: `backend/app/services/file_scanner_service.py`
- Modify: `backend/tests/unit/test_file_scanner_service.py`

**Step 1: Write the test (placeholder for now)**

```python
def test_calculate_quality_metrics_placeholder(scanner_with_catalog, mock_fits_file):
    """Test quality metrics calculation (placeholder)."""
    metrics = scanner_with_catalog._calculate_quality_metrics(str(mock_fits_file))

    # For MVP, return None - will implement star detection later
    assert metrics['fwhm'] is None
    assert metrics['star_count'] is None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py::test_calculate_quality_metrics_placeholder -v`
Expected: FAIL

**Step 3: Implement placeholder**

Add to `FileScannerService`:

```python
def _calculate_quality_metrics(self, fits_path: str) -> Dict[str, float]:
    """
    Calculate FWHM and star count from FITS data.

    TODO: Implement actual star detection and FWHM calculation.
    For MVP, returns None - requires image analysis library.
    """
    return {
        'fwhm': None,
        'star_count': None
    }
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py::test_calculate_quality_metrics_placeholder -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/file_scanner_service.py backend/tests/unit/test_file_scanner_service.py
git commit -m "feat: add quality metrics placeholder for future enhancement

- FWHM and star_count return None for MVP
- TODO: Implement star detection and FWHM calculation
- Requires sep or photutils library integration"
```

---

## Task 9: Implement scan_files Method

**Files:**
- Modify: `backend/app/services/file_scanner_service.py`
- Modify: `backend/tests/unit/test_file_scanner_service.py`

**Step 1: Write the test**

```python
from app.models.capture_models import OutputFile
from app.database import SessionLocal


def test_scan_files_creates_output_file(scanner_with_catalog, mock_fits_file, tmp_path):
    """Test scan_files creates OutputFile records."""
    db = SessionLocal()

    try:
        # Scan the mock FITS file with known catalog_id
        result = scanner_with_catalog.scan_files(
            db=db,
            file_paths=[str(mock_fits_file)],
            catalog_id="M31",  # Direct match, no fuzzy needed
            execution_id=None
        )

        assert len(result) == 1
        output_file = result[0]

        assert output_file.file_path == str(mock_fits_file)
        assert output_file.catalog_id == "M31"
        assert output_file.catalog_id_confidence == 1.0
        assert output_file.exposure_seconds == 10
        assert output_file.filter_name == "LP"

    finally:
        db.close()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py::test_scan_files_creates_output_file -v`
Expected: FAIL with "'FileScannerService' object has no attribute 'scan_files'"

**Step 3: Implement scan_files method**

Add to `FileScannerService`:

```python
def scan_files(
    self,
    db: Session,
    file_paths: List[str],
    catalog_id: str = None,
    execution_id: int = None
) -> List[OutputFile]:
    """
    Scan specific files (e.g., after transfer from Seestar).

    If catalog_id provided, use it directly (skip fuzzy match).
    Links to execution_id if provided.
    """
    output_files = []

    for file_path in file_paths:
        try:
            path = Path(file_path)

            # Check file exists
            if not path.exists():
                self.logger.warning(f"File not found: {file_path}")
                continue

            # Check if already scanned
            existing = db.query(OutputFile).filter_by(file_path=str(path)).first()
            if existing:
                self.logger.info(f"File already scanned: {file_path}")
                output_files.append(existing)
                continue

            # Determine file type from extension
            ext = path.suffix.lower()
            if ext in ['.fit', '.fits']:
                file_type = 'raw_fits' if 'light' in path.name.lower() else 'stacked_fits'
            elif ext == '.jpg':
                file_type = 'jpg'
            elif ext == '.png':
                file_type = 'png'
            elif ext == '.tiff':
                file_type = 'tiff'
            elif ext == '.avi':
                file_type = 'video'
            else:
                file_type = 'unknown'

            # Get file size
            file_size = path.stat().st_size

            # Extract metadata if FITS
            if ext in ['.fit', '.fits']:
                metadata = self._extract_fits_metadata(str(path))
                quality = self._calculate_quality_metrics(str(path))
            else:
                metadata = {'target_name': '', 'exposure_seconds': None, 'filter_name': None,
                           'temperature_celsius': None, 'gain': None, 'observation_date': None}
                quality = {'fwhm': None, 'star_count': None}

            # Determine catalog_id
            if catalog_id:
                # Direct match provided
                final_catalog_id = catalog_id
                confidence = 1.0
            elif metadata['target_name']:
                # Fuzzy match from FITS OBJECT header
                match = self._fuzzy_match_catalog(metadata['target_name'])
                if match:
                    final_catalog_id, confidence = match
                else:
                    # Try parent directory name as fallback
                    parent_name = path.parent.name
                    match = self._fuzzy_match_catalog(parent_name)
                    if match:
                        final_catalog_id, confidence = match
                    else:
                        self.logger.warning(f"No catalog match for: {metadata['target_name']}")
                        continue
            else:
                # Try parent directory name
                parent_name = path.parent.name
                match = self._fuzzy_match_catalog(parent_name)
                if match:
                    final_catalog_id, confidence = match
                else:
                    self.logger.warning(f"No catalog match for file: {file_path}")
                    continue

            # Create OutputFile record
            output_file = OutputFile(
                file_path=str(path),
                file_type=file_type,
                file_size_bytes=file_size,
                catalog_id=final_catalog_id,
                catalog_id_confidence=confidence,
                execution_id=execution_id,
                exposure_seconds=metadata['exposure_seconds'],
                filter_name=metadata['filter_name'],
                temperature_celsius=metadata['temperature_celsius'],
                gain=metadata['gain'],
                fwhm=quality['fwhm'],
                star_count=quality['star_count'],
                observation_date=metadata['observation_date']
            )

            db.add(output_file)
            db.commit()
            db.refresh(output_file)

            output_files.append(output_file)
            self.logger.info(f"Scanned file: {file_path} -> {final_catalog_id}")

        except Exception as e:
            self.logger.error(f"Error scanning file {file_path}: {e}")
            db.rollback()
            continue

    return output_files
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/test_file_scanner_service.py::test_scan_files_creates_output_file -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/file_scanner_service.py backend/tests/unit/test_file_scanner_service.py
git commit -m "feat: implement scan_files method for file scanning

- Creates OutputFile records in database
- Extracts FITS metadata when applicable
- Fuzzy matches target names to catalog
- Falls back to parent directory name
- Skips already-scanned files
- Links to execution_id if provided"
```

---

## Success Criteria

After completing all tasks:

**Database:**
- [ ] `capture_history` table exists with proper schema
- [ ] `output_files` table exists with proper schema
- [ ] Migration can be applied and rolled back successfully

**Models:**
- [ ] CaptureHistory and OutputFile models importable
- [ ] Models can be instantiated and saved to database
- [ ] Relationships work correctly (when OutputFile links to CaptureHistory)

**Configuration:**
- [ ] New settings available via Settings class
- [ ] Settings can be overridden via environment variables
- [ ] Defaults are sensible for production use

**FileScannerService:**
- [ ] Fuzzy matching handles common target name variations
- [ ] FITS metadata extraction works for standard headers
- [ ] scan_files creates OutputFile records correctly
- [ ] Duplicate files are detected and skipped

**Testing:**
- [ ] All unit tests pass
- [ ] No test regressions from baseline (5 passed, 1 skipped, 2 timeouts)
- [ ] Code coverage for new models and services

---

## Notes for Implementer

**CRITICAL TESTING REQUIREMENT:**
- Baseline: 5 tests passed, 1 skipped, 2 timeouts
- After EVERY commit, verify no new failures: `cd backend && pytest --tb=short -v`
- If any test that was passing now fails, you MUST fix it before proceeding

**Database Testing:**
- Use pytest fixtures with test database
- Clean up test data after each test
- Don't pollute the development database

**FITS File Testing:**
- Use astropy to create minimal test FITS files
- Or mock astropy.io.fits.open() for faster tests
- Don't commit large binary FITS files to repo

**Fuzzy Matching:**
- Test with known catalog variations
- M31 = "M 31" = "Andromeda Galaxy" should all match
- NGC numbers should match across catalogs

**Error Handling:**
- Log errors, don't crash
- Return partial results if some files fail
- Provide helpful error messages

**Future Enhancements (NOT in scope):**
- update_capture_history method (aggregate stats)
- scan_directory method (recursive scanning)
- FileTransferService implementation
- Captures API endpoints

These will be in subsequent plans after this foundation is solid.
