# File Transfer and Captures API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build file transfer service to download Seestar captures and create API endpoints to query capture history and output files.

**Architecture:** FileTransferService handles downloading files from Seestar S50 via mount path or HTTP, organizing them by date/target. Captures API exposes CaptureHistory and OutputFile data. Enhanced /api/targets endpoint includes capture statistics for each target.

**Tech Stack:** FastAPI, SQLAlchemy, aiofiles (async file operations), httpx (async HTTP client), Pydantic

---

## Task 1: Create FileTransferService Skeleton

**Files:**
- Create: `backend/app/services/file_transfer_service.py`
- Create: `backend/tests/unit/services/test_file_transfer_service.py`

**Step 1: Write the failing test**

Create `backend/tests/unit/services/test_file_transfer_service.py`:

```python
"""Tests for file transfer service."""

import pytest
from pathlib import Path
from app.services.file_transfer_service import FileTransferService


def test_file_transfer_service_init():
    """Test FileTransferService initialization."""
    service = FileTransferService()
    assert service is not None
    assert service.output_directory is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/services/test_file_transfer_service.py::test_file_transfer_service_init -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.file_transfer_service'"

**Step 3: Create minimal service structure**

Create `backend/app/services/file_transfer_service.py`:

```python
"""File transfer service for downloading Seestar S50 captures."""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from app.core.config import get_settings


class FileTransferService:
    """Downloads and organizes capture files from Seestar S50."""

    def __init__(self):
        """Initialize file transfer service."""
        self.logger = logging.getLogger(__name__)
        settings = get_settings()
        self.output_directory = Path(settings.output_directory)
        self.auto_transfer = settings.auto_transfer_files
        self.auto_delete = settings.auto_delete_after_transfer
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/unit/services/test_file_transfer_service.py::test_file_transfer_service_init -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/file_transfer_service.py backend/tests/unit/services/test_file_transfer_service.py
git commit -m "feat: create FileTransferService skeleton

- Initialize service with output directory from config
- Prepare for Seestar file transfer implementation"
```

---

## Task 2: Implement File Listing from Seestar Mount

**Files:**
- Modify: `backend/app/services/file_transfer_service.py`
- Modify: `backend/tests/unit/services/test_file_transfer_service.py`

**Step 1: Write the failing test**

Add to test file:

```python
from unittest.mock import Mock, patch, MagicMock
import os


@pytest.fixture
def mock_mount_path(tmp_path):
    """Create mock Seestar mount directory structure."""
    mount = tmp_path / "seestar_mount"
    mount.mkdir()

    # Create realistic Seestar directory structure
    # /seestar_mount/Seestar/IMG/
    img_dir = mount / "Seestar" / "IMG"
    img_dir.mkdir(parents=True)

    # Create some test files
    (img_dir / "M31_2025-12-30_001.fit").write_text("fake fits data")
    (img_dir / "M31_2025-12-30_001.jpg").write_text("fake jpg data")
    (img_dir / "M42_2025-12-30_002.fit").write_text("fake fits data")

    return mount


def test_list_files_from_mount(mock_mount_path):
    """Test listing files from mounted Seestar directory."""
    service = FileTransferService()

    # Override mount path for testing
    service.seestar_mount_path = mock_mount_path / "Seestar" / "IMG"

    files = service.list_available_files()

    assert len(files) == 3
    assert any("M31_2025-12-30_001.fit" in str(f) for f in files)
    assert any("M42_2025-12-30_002.fit" in str(f) for f in files)


def test_list_files_mount_not_available():
    """Test graceful handling when mount is not available."""
    service = FileTransferService()
    service.seestar_mount_path = Path("/nonexistent/path")

    files = service.list_available_files()

    assert files == []
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/services/test_file_transfer_service.py::test_list_files_from_mount -v`
Expected: FAIL with "AttributeError: 'FileTransferService' object has no attribute 'list_available_files'"

**Step 3: Implement file listing**

Add to `FileTransferService`:

```python
from app.core.config import get_settings


class FileTransferService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        settings = get_settings()
        self.output_directory = Path(settings.output_directory)
        self.auto_transfer = settings.auto_transfer_files
        self.auto_delete = settings.auto_delete_after_transfer

        # Seestar mount path (from device settings or config)
        # Typical: /mnt/seestar or network mount
        self.seestar_mount_path = Path("/mnt/seestar/Seestar/IMG")

    def list_available_files(self) -> List[Path]:
        """
        List all available files from Seestar mount.

        Returns:
            List of file paths from Seestar IMG directory.
            Returns empty list if mount not available.
        """
        if not self.seestar_mount_path.exists():
            self.logger.warning(f"Seestar mount path not found: {self.seestar_mount_path}")
            return []

        try:
            # Get all files recursively
            files = []
            for ext in ['.fit', '.fits', '.jpg', '.png', '.tiff', '.avi']:
                files.extend(self.seestar_mount_path.glob(f"**/*{ext}"))

            self.logger.info(f"Found {len(files)} files in {self.seestar_mount_path}")
            return files

        except Exception as e:
            self.logger.error(f"Error listing files from Seestar mount: {e}")
            return []
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/services/test_file_transfer_service.py -v -k list_files`
Expected: All list_files tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/file_transfer_service.py backend/tests/unit/services/test_file_transfer_service.py
git commit -m "feat: add file listing from Seestar mount

- Lists all capture files from Seestar IMG directory
- Handles mount not available gracefully
- Supports .fit, .fits, .jpg, .png, .tiff, .avi files"
```

---

## Task 3: Implement File Transfer with Organization

**Files:**
- Modify: `backend/app/services/file_transfer_service.py`
- Modify: `backend/tests/unit/services/test_file_transfer_service.py`

**Step 1: Write the failing test**

Add to test file:

```python
from datetime import datetime


def test_organize_file_path():
    """Test generating organized destination path for file."""
    service = FileTransferService()
    service.output_directory = Path("/output")

    source_file = Path("/seestar/M31_2025-12-30_001.fit")

    dest_path = service._get_destination_path(
        source_file,
        target_name="M31",
        observation_date=datetime(2025, 12, 30, 21, 45)
    )

    # Should organize as: /output/M31/2025-12-30/M31_2025-12-30_001.fit
    assert "M31" in str(dest_path)
    assert "2025-12-30" in str(dest_path)
    assert dest_path.name == "M31_2025-12-30_001.fit"


def test_transfer_file(mock_mount_path, tmp_path):
    """Test transferring single file with organization."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"
    service.seestar_mount_path = mock_mount_path / "Seestar" / "IMG"

    source = mock_mount_path / "Seestar" / "IMG" / "M31_2025-12-30_001.fit"

    transferred_path = service.transfer_file(
        source,
        target_name="M31",
        observation_date=datetime(2025, 12, 30, 21, 45)
    )

    assert transferred_path.exists()
    assert "M31" in str(transferred_path)
    assert "2025-12-30" in str(transferred_path)


def test_transfer_file_already_exists(mock_mount_path, tmp_path):
    """Test skipping file that already exists at destination."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"

    # Create existing file
    dest_dir = service.output_directory / "M31" / "2025-12-30"
    dest_dir.mkdir(parents=True)
    existing = dest_dir / "M31_2025-12-30_001.fit"
    existing.write_text("existing data")

    source = mock_mount_path / "Seestar" / "IMG" / "M31_2025-12-30_001.fit"

    # Should skip and return existing path
    result = service.transfer_file(
        source,
        target_name="M31",
        observation_date=datetime(2025, 12, 30, 21, 45)
    )

    assert result == existing
    assert existing.read_text() == "existing data"  # Not overwritten
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/services/test_file_transfer_service.py::test_organize_file_path -v`
Expected: FAIL with "AttributeError: '_get_destination_path'"

**Step 3: Implement file transfer**

Add to `FileTransferService`:

```python
import shutil


class FileTransferService:
    # ... existing init ...

    def _get_destination_path(
        self,
        source_file: Path,
        target_name: str,
        observation_date: datetime
    ) -> Path:
        """
        Generate organized destination path.

        Organization: {output_directory}/{target_name}/{YYYY-MM-DD}/{filename}

        Args:
            source_file: Original file path
            target_name: Catalog target name (e.g., "M31")
            observation_date: Observation datetime

        Returns:
            Organized destination path
        """
        date_str = observation_date.strftime("%Y-%m-%d")
        dest_dir = self.output_directory / target_name / date_str
        return dest_dir / source_file.name

    def transfer_file(
        self,
        source_file: Path,
        target_name: str,
        observation_date: datetime,
        delete_source: bool = False
    ) -> Path:
        """
        Transfer file to organized destination.

        Args:
            source_file: Source file path
            target_name: Catalog target name
            observation_date: Observation datetime
            delete_source: Delete source after successful transfer

        Returns:
            Destination file path
        """
        dest_path = self._get_destination_path(source_file, target_name, observation_date)

        # Skip if file already exists
        if dest_path.exists():
            self.logger.debug(f"File already exists, skipping: {dest_path}")
            return dest_path

        # Create destination directory
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Copy file
            shutil.copy2(source_file, dest_path)
            self.logger.info(f"Transferred: {source_file.name} -> {dest_path}")

            # Delete source if requested
            if delete_source:
                source_file.unlink()
                self.logger.debug(f"Deleted source file: {source_file}")

            return dest_path

        except Exception as e:
            self.logger.error(f"Error transferring file {source_file}: {e}")
            raise
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/services/test_file_transfer_service.py -v -k transfer`
Expected: All transfer tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/file_transfer_service.py backend/tests/unit/services/test_file_transfer_service.py
git commit -m "feat: implement file transfer with organization

- Organizes files by target and date
- Skips files that already exist
- Optional source deletion after transfer
- Creates directory structure automatically"
```

---

## Task 4: Implement Batch Transfer with FileScannerService Integration

**Files:**
- Modify: `backend/app/services/file_transfer_service.py`
- Modify: `backend/tests/unit/services/test_file_transfer_service.py`

**Step 1: Write the failing test**

Add to test file:

```python
from app.services.file_scanner_service import FileScannerService
from app.models.capture_models import OutputFile
from unittest.mock import MagicMock


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return MagicMock()


def test_transfer_and_scan_batch(mock_mount_path, tmp_path, mock_db_session):
    """Test transferring batch of files and scanning them."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"
    service.seestar_mount_path = mock_mount_path / "Seestar" / "IMG"

    # Transfer and scan all files
    results = service.transfer_and_scan_all(db=mock_db_session)

    assert results['transferred'] == 3
    assert results['scanned'] == 3
    assert results['errors'] == 0


def test_transfer_and_scan_with_errors(mock_mount_path, tmp_path, mock_db_session):
    """Test batch transfer handles errors gracefully."""
    service = FileTransferService()
    service.output_directory = tmp_path / "output"
    service.seestar_mount_path = mock_mount_path / "Seestar" / "IMG"

    # Add a file that will cause error (permission denied)
    bad_file = mock_mount_path / "Seestar" / "IMG" / "bad.fit"
    bad_file.write_text("data")
    bad_file.chmod(0o000)  # No permissions

    results = service.transfer_and_scan_all(db=mock_db_session)

    # Should handle error and continue with other files
    assert results['errors'] > 0
    assert results['transferred'] >= 3  # Original 3 files
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/services/test_file_transfer_service.py::test_transfer_and_scan_batch -v`
Expected: FAIL with "AttributeError: 'FileTransferService' object has no attribute 'transfer_and_scan_all'"

**Step 3: Implement batch transfer**

Add to `FileTransferService`:

```python
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.services.file_scanner_service import FileScannerService


class FileTransferService:
    def __init__(self):
        # ... existing init ...
        self.scanner = FileScannerService()

    def transfer_and_scan_all(self, db: Session) -> Dict[str, Any]:
        """
        Transfer all files from Seestar and scan them.

        This is the main orchestration method that:
        1. Lists available files from Seestar
        2. Extracts metadata to determine target/date
        3. Transfers files to organized structure
        4. Scans transferred files with FileScannerService

        Args:
            db: Database session for creating OutputFile records

        Returns:
            Dict with counts: transferred, scanned, errors
        """
        results = {
            'transferred': 0,
            'scanned': 0,
            'errors': 0,
            'skipped': 0
        }

        # Get all available files
        available_files = self.list_available_files()
        if not available_files:
            self.logger.info("No files available for transfer")
            return results

        self.logger.info(f"Found {len(available_files)} files to process")

        transferred_files = []

        # Transfer each file
        for source_file in available_files:
            try:
                # Extract metadata to get target name and date
                # For now, parse from filename (format: TARGETNAME_YYYY-MM-DD_NNN.ext)
                metadata = self.scanner._extract_fits_metadata(str(source_file))

                if not metadata or not metadata.get('target_name'):
                    self.logger.warning(f"Could not extract metadata from {source_file.name}, skipping")
                    results['skipped'] += 1
                    continue

                target_name = metadata['target_name']
                observation_date = metadata.get('observation_date') or datetime.now()

                # Transfer file
                dest_path = self.transfer_file(
                    source_file,
                    target_name,
                    observation_date,
                    delete_source=self.auto_delete
                )

                transferred_files.append(dest_path)
                results['transferred'] += 1

            except Exception as e:
                self.logger.error(f"Error processing {source_file}: {e}")
                results['errors'] += 1

        # Scan all transferred files to create OutputFile records
        if transferred_files:
            # Get the parent directory (output_directory)
            scan_count = self.scanner.scan_files(str(self.output_directory), db)
            results['scanned'] = scan_count

        self.logger.info(f"Transfer complete: {results}")
        return results
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/services/test_file_transfer_service.py -v -k batch`
Expected: All batch tests PASS

**Step 5: Commit**

```bash
git add backend/app/services/file_transfer_service.py backend/tests/unit/services/test_file_transfer_service.py
git commit -m "feat: implement batch transfer with scanner integration

- Transfers all files from Seestar mount
- Extracts metadata to organize files
- Integrates with FileScannerService for DB records
- Returns detailed results with counts
- Handles errors gracefully"
```

---

## Task 5: Create Captures API Endpoints

**Files:**
- Create: `backend/app/api/captures.py`
- Create: `backend/tests/api/test_captures_api.py`

**Step 1: Write the failing test**

Create `backend/tests/api/test_captures_api.py`:

```python
"""Tests for captures API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.capture_models import CaptureHistory, OutputFile
from datetime import datetime


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_capture_history(db_session):
    """Create sample capture history."""
    capture = CaptureHistory(
        catalog_id="M31",
        total_exposure_seconds=7200,
        total_frames=720,
        total_sessions=3,
        status="needs_more_data",
        best_fwhm=2.3,
        best_star_count=2847
    )
    db_session.add(capture)
    db_session.commit()
    return capture


def test_list_captures_empty(client):
    """Test listing captures when none exist."""
    response = client.get("/api/captures")
    assert response.status_code == 200
    assert response.json() == []


def test_list_captures(client, sample_capture_history):
    """Test listing all captures."""
    response = client.get("/api/captures")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]['catalog_id'] == "M31"
    assert data[0]['total_exposure_seconds'] == 7200


def test_get_capture_by_catalog_id(client, sample_capture_history):
    """Test getting specific capture by catalog ID."""
    response = client.get("/api/captures/M31")
    assert response.status_code == 200

    data = response.json()
    assert data['catalog_id'] == "M31"
    assert data['total_frames'] == 720


def test_get_capture_not_found(client):
    """Test getting non-existent capture."""
    response = client.get("/api/captures/NGC9999")
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/api/test_captures_api.py::test_list_captures_empty -v`
Expected: FAIL with 404 (route not found)

**Step 3: Create Captures API**

Create `backend/app/api/captures.py`:

```python
"""API endpoints for capture history and output files."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.capture_models import CaptureHistory, OutputFile


router = APIRouter(prefix="/captures", tags=["captures"])


# ========================================================================
# Pydantic Schemas
# ========================================================================


class CaptureHistoryResponse(BaseModel):
    """Response model for capture history."""

    id: int
    catalog_id: str
    total_exposure_seconds: int
    total_frames: int
    total_sessions: int
    first_captured_at: Optional[datetime]
    last_captured_at: Optional[datetime]
    status: Optional[str]
    suggested_status: Optional[str]
    best_fwhm: Optional[float]
    best_star_count: Optional[int]
    updated_at: datetime

    class Config:
        from_attributes = True


class OutputFileResponse(BaseModel):
    """Response model for output file."""

    id: int
    file_path: str
    file_type: str
    file_size_bytes: int
    catalog_id: str
    catalog_id_confidence: float
    exposure_seconds: Optional[int]
    filter_name: Optional[str]
    observation_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ========================================================================
# Capture History Endpoints
# ========================================================================


@router.get("", response_model=List[CaptureHistoryResponse])
async def list_captures(
    status: Optional[str] = Query(None, description="Filter by status"),
    min_exposure_hours: Optional[float] = Query(None, description="Minimum total exposure hours"),
    db: Session = Depends(get_db)
):
    """List all capture history records."""
    query = db.query(CaptureHistory)

    if status:
        query = query.filter(CaptureHistory.status == status)

    if min_exposure_hours:
        min_seconds = int(min_exposure_hours * 3600)
        query = query.filter(CaptureHistory.total_exposure_seconds >= min_seconds)

    return query.order_by(CaptureHistory.last_captured_at.desc()).all()


@router.get("/{catalog_id}", response_model=CaptureHistoryResponse)
async def get_capture(catalog_id: str, db: Session = Depends(get_db)):
    """Get capture history for specific target."""
    capture = db.query(CaptureHistory).filter(
        CaptureHistory.catalog_id == catalog_id
    ).first()

    if not capture:
        raise HTTPException(status_code=404, detail=f"No capture history for {catalog_id}")

    return capture


@router.get("/{catalog_id}/files", response_model=List[OutputFileResponse])
async def get_capture_files(catalog_id: str, db: Session = Depends(get_db)):
    """Get all output files for specific target."""
    files = db.query(OutputFile).filter(
        OutputFile.catalog_id == catalog_id
    ).order_by(OutputFile.observation_date.desc()).all()

    return files


# ========================================================================
# Output Files Endpoints
# ========================================================================


@router.get("/files/all", response_model=List[OutputFileResponse])
async def list_all_files(
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    min_confidence: Optional[float] = Query(None, description="Minimum catalog match confidence"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all output files."""
    query = db.query(OutputFile)

    if file_type:
        query = query.filter(OutputFile.file_type == file_type)

    if min_confidence:
        query = query.filter(OutputFile.catalog_id_confidence >= min_confidence)

    return query.order_by(OutputFile.created_at.desc()).limit(limit).offset(offset).all()
```

**Step 4: Register router in main routes**

Modify `backend/app/api/routes.py`:

```python
# Add import
from app.api.captures import router as captures_router

# Register router
router.include_router(captures_router)
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/api/test_captures_api.py -v`
Expected: All captures API tests PASS

**Step 6: Commit**

```bash
git add backend/app/api/captures.py backend/app/api/routes.py backend/tests/api/test_captures_api.py
git commit -m "feat: add Captures API endpoints

- GET /api/captures - List all capture history
- GET /api/captures/{catalog_id} - Get capture for target
- GET /api/captures/{catalog_id}/files - Get files for target
- GET /api/captures/files/all - List all output files
- Supports filtering by status, exposure, type, confidence"
```

---

## Task 6: Enhance /api/targets with Capture History

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/tests/api/test_api.py`

**Step 1: Write the failing test**

Add to `backend/tests/api/test_api.py`:

```python
from app.models.capture_models import CaptureHistory


def test_targets_include_capture_history(client, db_session):
    """Test that targets endpoint includes capture history."""
    # Create capture history for M31
    capture = CaptureHistory(
        catalog_id="M31",
        total_exposure_seconds=7200,
        total_frames=720,
        total_sessions=3
    )
    db_session.add(capture)
    db_session.commit()

    response = client.get("/api/targets?limit=10")
    assert response.status_code == 200

    targets = response.json()
    m31 = next((t for t in targets if t['catalog_id'] == 'M31'), None)

    assert m31 is not None
    assert 'capture_history' in m31
    assert m31['capture_history']['total_exposure_seconds'] == 7200
    assert m31['capture_history']['total_sessions'] == 3


def test_targets_without_capture_history(client):
    """Test targets without capture history show null."""
    response = client.get("/api/targets?limit=10")
    assert response.status_code == 200

    targets = response.json()
    # Most targets won't have capture history
    target_without_history = next(
        (t for t in targets if t.get('capture_history') is None),
        None
    )
    assert target_without_history is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/api/test_api.py::test_targets_include_capture_history -v`
Expected: FAIL with "KeyError: 'capture_history'" (field not in response)

**Step 3: Update DSOTarget model to include capture_history**

Modify the DSOTarget Pydantic model in `backend/app/models/__init__.py` or wherever it's defined:

```python
from typing import Optional
from app.models.capture_models import CaptureHistory


class DSOTarget(BaseModel):
    # ... existing fields ...

    # Add capture history field
    capture_history: Optional[dict] = None

    class Config:
        from_attributes = True
```

**Step 4: Update list_targets endpoint to join capture history**

Modify `backend/app/api/routes.py` in the `list_targets` function:

```python
from sqlalchemy.orm import joinedload
from app.models.capture_models import CaptureHistory


@router.get("/targets", response_model=List[DSOTarget])
async def list_targets(
    db: Session = Depends(get_db),
    # ... existing parameters ...
):
    """List catalog targets with optional capture history."""
    catalog = CatalogService(db)

    # Get targets as before
    targets = catalog.get_targets(
        object_types=object_types,
        min_magnitude=min_magnitude,
        max_magnitude=max_magnitude,
        constellation=constellation,
        limit=limit,
        offset=offset
    )

    # Fetch capture history for all targets in one query
    catalog_ids = [t.catalog_id for t in targets]
    capture_dict = {}

    if catalog_ids:
        captures = db.query(CaptureHistory).filter(
            CaptureHistory.catalog_id.in_(catalog_ids)
        ).all()

        capture_dict = {
            c.catalog_id: {
                'total_exposure_seconds': c.total_exposure_seconds,
                'total_frames': c.total_frames,
                'total_sessions': c.total_sessions,
                'status': c.status,
                'suggested_status': c.suggested_status,
                'best_fwhm': c.best_fwhm,
                'best_star_count': c.best_star_count,
                'last_captured_at': c.last_captured_at
            }
            for c in captures
        }

    # Add capture history to each target
    result = []
    for target in targets:
        target_dict = target.dict() if hasattr(target, 'dict') else target.__dict__
        target_dict['capture_history'] = capture_dict.get(target.catalog_id)
        result.append(target_dict)

    return result
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/api/test_api.py -v -k capture_history`
Expected: capture_history tests PASS

**Step 6: Commit**

```bash
git add backend/app/api/routes.py backend/app/models/__init__.py backend/tests/api/test_api.py
git commit -m "feat: enhance /api/targets with capture history

- Adds capture_history field to DSOTarget response
- Efficiently fetches capture data in single query
- Shows total exposure, frames, sessions per target
- Null for targets without captures"
```

---

## Task 7: Add File Transfer Trigger Endpoint

**Files:**
- Modify: `backend/app/api/captures.py`
- Modify: `backend/tests/api/test_captures_api.py`

**Step 1: Write the failing test**

Add to `backend/tests/api/test_captures_api.py`:

```python
from unittest.mock import patch, MagicMock


def test_trigger_file_transfer(client):
    """Test triggering file transfer from Seestar."""
    with patch('app.services.file_transfer_service.FileTransferService') as MockService:
        mock_service = MagicMock()
        mock_service.transfer_and_scan_all.return_value = {
            'transferred': 5,
            'scanned': 5,
            'errors': 0,
            'skipped': 0
        }
        MockService.return_value = mock_service

        response = client.post("/api/captures/transfer")

        assert response.status_code == 200
        data = response.json()
        assert data['transferred'] == 5
        assert data['scanned'] == 5


def test_trigger_file_transfer_with_errors(client):
    """Test file transfer handles errors."""
    with patch('app.services.file_transfer_service.FileTransferService') as MockService:
        mock_service = MagicMock()
        mock_service.transfer_and_scan_all.return_value = {
            'transferred': 3,
            'scanned': 3,
            'errors': 2,
            'skipped': 1
        }
        MockService.return_value = mock_service

        response = client.post("/api/captures/transfer")

        assert response.status_code == 200
        data = response.json()
        assert data['errors'] == 2
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/api/test_captures_api.py::test_trigger_file_transfer -v`
Expected: FAIL with 404 (route not found)

**Step 3: Add transfer trigger endpoint**

Add to `backend/app/api/captures.py`:

```python
from app.services.file_transfer_service import FileTransferService


class TransferResultResponse(BaseModel):
    """Response model for file transfer results."""

    transferred: int
    scanned: int
    errors: int
    skipped: int
    message: str


@router.post("/transfer", response_model=TransferResultResponse)
async def trigger_file_transfer(db: Session = Depends(get_db)):
    """
    Trigger file transfer from Seestar.

    This endpoint:
    1. Lists all files from Seestar mount
    2. Transfers them to organized directory structure
    3. Scans transferred files to create OutputFile records
    4. Updates CaptureHistory aggregates

    Returns:
        Results with counts of transferred, scanned, errors, skipped
    """
    try:
        transfer_service = FileTransferService()
        results = transfer_service.transfer_and_scan_all(db)

        message = f"Transferred {results['transferred']} files"
        if results['errors'] > 0:
            message += f" with {results['errors']} errors"
        if results['skipped'] > 0:
            message += f" ({results['skipped']} skipped)"

        return TransferResultResponse(
            transferred=results['transferred'],
            scanned=results['scanned'],
            errors=results['errors'],
            skipped=results['skipped'],
            message=message
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/api/test_captures_api.py -v -k transfer`
Expected: transfer tests PASS

**Step 5: Commit**

```bash
git add backend/app/api/captures.py backend/tests/api/test_captures_api.py
git commit -m "feat: add file transfer trigger endpoint

- POST /api/captures/transfer - Trigger batch transfer
- Transfers files from Seestar mount
- Scans and creates database records
- Returns detailed results with counts"
```

---

## Task 8: Add Capture Statistics Aggregation

**Files:**
- Create: `backend/app/services/capture_stats_service.py`
- Create: `backend/tests/unit/services/test_capture_stats_service.py`

**Step 1: Write the failing test**

Create `backend/tests/unit/services/test_capture_stats_service.py`:

```python
"""Tests for capture statistics service."""

import pytest
from datetime import datetime
from app.services.capture_stats_service import CaptureStatsService
from app.models.capture_models import CaptureHistory, OutputFile


@pytest.fixture
def sample_output_files(db_session):
    """Create sample output files for testing."""
    files = [
        OutputFile(
            file_path="/output/M31/2025-12-30/file1.fit",
            file_type="stacked_fits",
            file_size_bytes=1000000,
            catalog_id="M31",
            catalog_id_confidence=1.0,
            exposure_seconds=10,
            observation_date=datetime(2025, 12, 30, 21, 0)
        ),
        OutputFile(
            file_path="/output/M31/2025-12-30/file2.fit",
            file_type="stacked_fits",
            file_size_bytes=1000000,
            catalog_id="M31",
            catalog_id_confidence=1.0,
            exposure_seconds=10,
            observation_date=datetime(2025, 12, 30, 22, 0)
        ),
        OutputFile(
            file_path="/output/M31/2025-12-31/file3.fit",
            file_type="stacked_fits",
            file_size_bytes=1000000,
            catalog_id="M31",
            catalog_id_confidence=1.0,
            exposure_seconds=10,
            observation_date=datetime(2025, 12, 31, 20, 0)
        ),
    ]

    for f in files:
        db_session.add(f)
    db_session.commit()

    return files


def test_aggregate_capture_history(db_session, sample_output_files):
    """Test aggregating output files into capture history."""
    service = CaptureStatsService(db_session)

    service.update_capture_history("M31")

    capture = db_session.query(CaptureHistory).filter(
        CaptureHistory.catalog_id == "M31"
    ).first()

    assert capture is not None
    assert capture.total_frames == 3
    assert capture.total_exposure_seconds == 30
    assert capture.total_sessions == 2  # Two different dates
    assert capture.first_captured_at == datetime(2025, 12, 30, 21, 0)
    assert capture.last_captured_at == datetime(2025, 12, 31, 20, 0)


def test_update_suggested_status(db_session, sample_output_files):
    """Test suggested status calculation."""
    service = CaptureStatsService(db_session)

    service.update_capture_history("M31")

    capture = db_session.query(CaptureHistory).filter(
        CaptureHistory.catalog_id == "M31"
    ).first()

    # With 30 seconds total, should suggest "needs_more_data"
    assert capture.suggested_status == "needs_more_data"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/unit/services/test_capture_stats_service.py::test_aggregate_capture_history -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.capture_stats_service'"

**Step 3: Create statistics service**

Create `backend/app/services/capture_stats_service.py`:

```python
"""Service for aggregating capture statistics."""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.models.capture_models import CaptureHistory, OutputFile
from app.core.config import get_settings


class CaptureStatsService:
    """Aggregates output files into capture history statistics."""

    def __init__(self, db: Session):
        """Initialize capture stats service."""
        self.db = db
        self.logger = logging.getLogger(__name__)
        settings = get_settings()
        self.complete_threshold_hours = settings.capture_complete_hours
        self.needs_more_threshold_hours = settings.capture_needs_more_hours

    def update_capture_history(self, catalog_id: str) -> CaptureHistory:
        """
        Update or create capture history for target.

        Aggregates all output files for the catalog_id and updates:
        - Total exposure time
        - Total frames
        - Total sessions (unique dates)
        - First/last capture times
        - Best quality metrics
        - Suggested status

        Args:
            catalog_id: Catalog identifier (e.g., "M31")

        Returns:
            Updated or created CaptureHistory record
        """
        # Get all files for this target
        files = self.db.query(OutputFile).filter(
            OutputFile.catalog_id == catalog_id
        ).all()

        if not files:
            self.logger.debug(f"No files found for {catalog_id}")
            return None

        # Calculate aggregates
        total_exposure = sum(f.exposure_seconds or 0 for f in files)
        total_frames = len(files)

        # Count unique sessions (unique dates)
        unique_dates = set()
        for f in files:
            if f.observation_date:
                date_str = f.observation_date.strftime("%Y-%m-%d")
                unique_dates.add(date_str)
        total_sessions = len(unique_dates)

        # Get first/last capture times
        dates = [f.observation_date for f in files if f.observation_date]
        first_captured = min(dates) if dates else None
        last_captured = max(dates) if dates else None

        # Get best quality metrics
        best_fwhm = min((f.fwhm for f in files if f.fwhm), default=None)
        best_star_count = max((f.star_count for f in files if f.star_count), default=None)

        # Calculate suggested status
        total_hours = total_exposure / 3600.0
        if total_hours >= self.complete_threshold_hours:
            suggested_status = "complete"
        elif total_hours >= self.needs_more_threshold_hours:
            suggested_status = "needs_more_data"
        else:
            suggested_status = None  # Not enough data yet

        # Update or create capture history
        capture = self.db.query(CaptureHistory).filter(
            CaptureHistory.catalog_id == catalog_id
        ).first()

        if capture:
            # Update existing
            capture.total_exposure_seconds = total_exposure
            capture.total_frames = total_frames
            capture.total_sessions = total_sessions
            capture.first_captured_at = first_captured
            capture.last_captured_at = last_captured
            capture.best_fwhm = best_fwhm
            capture.best_star_count = best_star_count
            capture.suggested_status = suggested_status
        else:
            # Create new
            capture = CaptureHistory(
                catalog_id=catalog_id,
                total_exposure_seconds=total_exposure,
                total_frames=total_frames,
                total_sessions=total_sessions,
                first_captured_at=first_captured,
                last_captured_at=last_captured,
                best_fwhm=best_fwhm,
                best_star_count=best_star_count,
                suggested_status=suggested_status
            )
            self.db.add(capture)

        self.db.commit()
        self.logger.info(f"Updated capture history for {catalog_id}: {total_frames} frames, {total_hours:.1f}h")

        return capture

    def update_all_capture_histories(self) -> int:
        """
        Update capture history for all targets with output files.

        Returns:
            Number of targets updated
        """
        # Get unique catalog IDs from output files
        catalog_ids = self.db.query(OutputFile.catalog_id).distinct().all()
        catalog_ids = [c[0] for c in catalog_ids]

        count = 0
        for catalog_id in catalog_ids:
            self.update_capture_history(catalog_id)
            count += 1

        self.logger.info(f"Updated {count} capture histories")
        return count
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/services/test_capture_stats_service.py -v`
Expected: All stats tests PASS

**Step 5: Integrate stats update into FileTransferService**

Modify `backend/app/services/file_transfer_service.py`:

```python
from app.services.capture_stats_service import CaptureStatsService


class FileTransferService:
    def transfer_and_scan_all(self, db: Session) -> Dict[str, Any]:
        # ... existing transfer logic ...

        # After scanning, update capture statistics
        if results['scanned'] > 0:
            stats_service = CaptureStatsService(db)
            updated_count = stats_service.update_all_capture_histories()
            results['updated_histories'] = updated_count

        return results
```

**Step 6: Commit**

```bash
git add backend/app/services/capture_stats_service.py backend/app/services/file_transfer_service.py backend/tests/unit/services/test_capture_stats_service.py
git commit -m "feat: add capture statistics aggregation

- CaptureStatsService aggregates OutputFile records
- Calculates total exposure, frames, sessions
- Determines best quality metrics
- Suggests status based on exposure thresholds
- Integrates with file transfer workflow"
```

---

## Summary

This plan implements Phase 2 of the capture history system:

**8 Tasks Total:**
1. ✅ FileTransferService skeleton
2. ✅ File listing from Seestar mount
3. ✅ File transfer with organization
4. ✅ Batch transfer with scanner integration
5. ✅ Captures API endpoints
6. ✅ Enhanced /api/targets with capture history
7. ✅ File transfer trigger endpoint
8. ✅ Capture statistics aggregation

**Tech Stack:**
- FastAPI (REST API)
- SQLAlchemy (ORM)
- Pydantic (validation)
- aiofiles/httpx (async I/O)

**What This Enables:**
- Automatic file downloads from Seestar S50
- Organized file storage by target and date
- Query capture history via API
- See capture stats in catalog browser
- Trigger manual transfers via endpoint

**Next Steps:**
- ExecutionEngine for automated capture
- WebSocket for real-time updates
- Frontend catalog browser integration
- Seestar HTTP file transfer (if mount not available)

---
