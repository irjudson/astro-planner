"""
Integration tests for the processing pipeline.

These tests verify the complete processing workflow:
1. Create session
2. Upload files
3. Process with various presets
4. Download results
"""

import pytest
import numpy as np
from pathlib import Path
from astropy.io import fits
from fastapi.testclient import TestClient
import tempfile
import os

from app.main import app
from app.database import get_db, engine, get_test_db
from app.models.processing_models import Base

# Test client
client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Set up test database with transactional rollback."""
    app.dependency_overrides[get_db] = get_test_db
    yield
    app.dependency_overrides = {}


@pytest.fixture
def sample_fits_file():
    """Create a sample FITS file for testing."""
    # Create synthetic star field
    size = 512
    image_data = np.random.poisson(lam=100, size=(size, size)).astype(np.float32)

    # Add some "stars" (bright spots)
    for _ in range(50):
        x = np.random.randint(50, size - 50)
        y = np.random.randint(50, size - 50)
        brightness = np.random.uniform(1000, 5000)

        # Create Gaussian star profile
        y_grid, x_grid = np.ogrid[-10:10, -10:10]
        gaussian = brightness * np.exp(-(x_grid**2 + y_grid**2) / (2 * 2**2))

        # Add to image
        image_data[y-10:y+10, x-10:x+10] += gaussian

    # Create FITS file
    hdu = fits.PrimaryHDU(data=image_data)
    hdu.header['OBJECT'] = 'Test Object'
    hdu.header['EXPTIME'] = 300.0
    hdu.header['TELESCOP'] = 'Seestar S50'

    # Save to temporary file
    temp_dir = tempfile.mkdtemp()
    fits_path = os.path.join(temp_dir, 'test_image.fits')
    hdu.writeto(fits_path, overwrite=True)

    yield fits_path

    # Cleanup
    os.remove(fits_path)
    os.rmdir(temp_dir)


def test_health_endpoint():
    """Test that the API health endpoint responds."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_session(setup_database):
    """Test creating a processing session."""
    response = client.post(
        "/api/process/sessions",
        json={"session_name": "test_session_001"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_name"] == "test_session_001"
    assert data["status"] == "uploading"
    assert "id" in data


def test_list_sessions(setup_database):
    """Test listing processing sessions."""
    # Create a few sessions
    for i in range(3):
        client.post(
            "/api/process/sessions",
            json={"session_name": f"test_session_{i}"}
        )

    # List sessions
    response = client.get("/api/process/sessions")
    assert response.status_code == 200

    sessions = response.json()
    assert len(sessions) >= 3


def test_upload_file(setup_database, sample_fits_file):
    """Test uploading a FITS file to a session."""
    # Create session
    session_response = client.post(
        "/api/process/sessions",
        json={"session_name": "upload_test"}
    )
    session_id = session_response.json()["id"]

    # Upload file
    with open(sample_fits_file, 'rb') as f:
        response = client.post(
            f"/api/process/sessions/{session_id}/upload",
            files={"file": ("test.fits", f, "application/fits")},
            data={"file_type": "stacked"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.fits"
    assert data["file_type"] == "stacked"
    assert data["size_bytes"] > 0


def test_finalize_session(setup_database, sample_fits_file):
    """Test finalizing a session."""
    # Create session and upload file
    session_response = client.post(
        "/api/process/sessions",
        json={"session_name": "finalize_test"}
    )
    session_id = session_response.json()["id"]

    with open(sample_fits_file, 'rb') as f:
        client.post(
            f"/api/process/sessions/{session_id}/upload",
            files={"file": ("test.fits", f, "application/fits")},
            data={"file_type": "stacked"}
        )

    # Finalize
    response = client.post(f"/api/process/sessions/{session_id}/finalize")
    assert response.status_code == 200

    # Check status changed
    session = client.get(f"/api/process/sessions/{session_id}").json()
    assert session["status"] == "ready"


def test_process_with_quick_dso(setup_database, sample_fits_file):
    """Test processing with quick_dso preset."""
    # Create session and upload
    session_response = client.post(
        "/api/process/sessions",
        json={"session_name": "quick_dso_test"}
    )
    session_id = session_response.json()["id"]

    with open(sample_fits_file, 'rb') as f:
        client.post(
            f"/api/process/sessions/{session_id}/upload",
            files={"file": ("test.fits", f, "application/fits")},
            data={"file_type": "stacked"}
        )

    client.post(f"/api/process/sessions/{session_id}/finalize")

    # Start processing
    response = client.post(
        f"/api/process/sessions/{session_id}/process",
        json={"pipeline_name": "quick_dso"}
    )

    assert response.status_code == 200
    job = response.json()
    assert "id" in job
    assert job["status"] in ["pending", "running"]


def test_job_status(setup_database, sample_fits_file):
    """Test checking job status."""
    # Create session, upload, and start processing
    session_response = client.post(
        "/api/process/sessions",
        json={"session_name": "status_test"}
    )
    session_id = session_response.json()["id"]

    with open(sample_fits_file, 'rb') as f:
        client.post(
            f"/api/process/sessions/{session_id}/upload",
            files={"file": ("test.fits", f, "application/fits")},
            data={"file_type": "stacked"}
        )

    client.post(f"/api/process/sessions/{session_id}/finalize")

    job_response = client.post(
        f"/api/process/sessions/{session_id}/process",
        json={"pipeline_name": "quick_dso"}
    )
    job_id = job_response.json()["id"]

    # Check status
    import time
    max_wait = 60  # Wait up to 60 seconds
    start_time = time.time()

    while time.time() - start_time < max_wait:
        response = client.get(f"/api/process/jobs/{job_id}")
        assert response.status_code == 200

        job = response.json()
        assert "status" in job
        assert "progress_percent" in job

        if job["status"] in ["complete", "failed"]:
            break

        time.sleep(2)

    # Should have completed or failed by now
    final_status = client.get(f"/api/process/jobs/{job_id}").json()
    assert final_status["status"] in ["complete", "failed"]

    # If failed, print error for debugging
    if final_status["status"] == "failed":
        print(f"Job failed: {final_status.get('error_message')}")


def test_delete_session(setup_database):
    """Test deleting a session."""
    # Create session
    session_response = client.post(
        "/api/process/sessions",
        json={"session_name": "delete_test"}
    )
    session_id = session_response.json()["id"]

    # Delete
    response = client.delete(f"/api/process/sessions/{session_id}")
    assert response.status_code == 200

    # Verify deleted
    response = client.get(f"/api/process/sessions/{session_id}")
    assert response.status_code == 404


def test_invalid_session_id():
    """Test handling of invalid session ID."""
    response = client.get("/api/process/sessions/99999")
    assert response.status_code == 404


def test_invalid_job_id():
    """Test handling of invalid job ID."""
    response = client.get("/api/process/jobs/99999")
    assert response.status_code == 404


def test_process_without_files(setup_database):
    """Test that processing fails without uploaded files."""
    # Create empty session
    session_response = client.post(
        "/api/process/sessions",
        json={"session_name": "empty_test"}
    )
    session_id = session_response.json()["id"]

    # Try to process
    response = client.post(
        f"/api/process/sessions/{session_id}/process",
        json={"pipeline_name": "quick_dso"}
    )

    # Should fail (no files uploaded)
    assert response.status_code in [400, 422]


@pytest.mark.parametrize("preset", ["quick_dso", "export_pixinsight"])
def test_all_presets(setup_database, sample_fits_file, preset):
    """Test all processing presets."""
    # Create session and upload
    session_response = client.post(
        "/api/process/sessions",
        json={"session_name": f"preset_test_{preset}"}
    )
    session_id = session_response.json()["id"]

    with open(sample_fits_file, 'rb') as f:
        client.post(
            f"/api/process/sessions/{session_id}/upload",
            files={"file": ("test.fits", f, "application/fits")},
            data={"file_type": "stacked"}
        )

    client.post(f"/api/process/sessions/{session_id}/finalize")

    # Start processing
    response = client.post(
        f"/api/process/sessions/{session_id}/process",
        json={"pipeline_name": preset}
    )

    assert response.status_code == 200


# Smoke tests for direct processor
def test_direct_processor_load_fits(sample_fits_file):
    """Test loading FITS file with direct processor."""
    from app.services.direct_processor import DirectProcessor

    processor = DirectProcessor()
    data, header = processor.load_fits(sample_fits_file)

    assert data is not None
    assert data.shape == (512, 512)
    assert header['OBJECT'] == 'Test Object'


def test_direct_processor_stretch(sample_fits_file):
    """Test histogram stretching."""
    from app.services.direct_processor import DirectProcessor

    processor = DirectProcessor()
    data, header = processor.load_fits(sample_fits_file)

    stretched = processor.histogram_stretch(
        data,
        target_median=0.25,
        shadows_clip=0.0
    )

    assert stretched is not None
    assert stretched.shape == data.shape
    assert stretched.min() >= 0
    assert stretched.max() <= 1


def test_direct_processor_export_jpeg(sample_fits_file):
    """Test JPEG export."""
    from app.services.direct_processor import DirectProcessor
    import tempfile
    import os

    processor = DirectProcessor()
    data, header = processor.load_fits(sample_fits_file)

    stretched = processor.histogram_stretch(data, target_median=0.25)

    # Export to temporary file
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, 'test_output.jpg')

    base_name = Path(output_path).stem
    processor.export_image(
        stretched,
        Path(temp_dir),
        base_name,
        format='jpeg',
        quality=85
    )

    # Verify file exists and has content
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0

    # Cleanup
    os.remove(output_path)
    os.rmdir(temp_dir)


def test_direct_processor_export_tiff(sample_fits_file):
    """Test TIFF export."""
    from app.services.direct_processor import DirectProcessor
    import tempfile
    import os

    processor = DirectProcessor()
    data, header = processor.load_fits(sample_fits_file)

    # Export to temporary file
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, 'test_output.tif')

    base_name = Path(output_path).stem
    processor.export_image(
        data,
        Path(temp_dir),
        base_name,
        format='tiff',
        bit_depth=16
    )

    # Verify file exists and has content
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0

    # Cleanup
    os.remove(output_path)
    os.rmdir(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
