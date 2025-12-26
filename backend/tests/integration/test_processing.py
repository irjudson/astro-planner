#!/usr/bin/env python3
"""
Quick test script for processing pipeline.

This script creates a synthetic FITS file and tests the complete
processing workflow end-to-end.

Usage:
    python test_processing.py

Requirements:
    - Docker services running (docker-compose up)
    - API accessible at localhost:9247
"""

import requests
import numpy as np
from astropy.io import fits
import tempfile
import time
import sys
import os

# Configuration
API_BASE = "http://localhost:9247/api"
TIMEOUT = 120  # seconds to wait for processing


def create_test_fits():
    """Create a synthetic star field FITS file."""
    print("📸 Creating synthetic star field...")

    # Image parameters
    size = 1024
    num_stars = 100

    # Create background
    image_data = np.random.poisson(lam=100, size=(size, size)).astype(np.float32)

    # Add stars
    for _ in range(num_stars):
        x = np.random.randint(50, size - 50)
        y = np.random.randint(50, size - 50)
        brightness = np.random.uniform(1000, 10000)
        fwhm = np.random.uniform(2, 4)

        # Create Gaussian star profile
        radius = int(fwhm * 5)
        y_grid, x_grid = np.ogrid[-radius : radius + 1, -radius : radius + 1]
        gaussian = brightness * np.exp(-(x_grid**2 + y_grid**2) / (2 * fwhm**2))

        # Add to image (with bounds checking)
        y_start = max(0, y - radius)
        y_end = min(size, y + radius + 1)
        x_start = max(0, x - radius)
        x_end = min(size, x + radius + 1)

        gy_start = radius - (y - y_start)
        gy_end = gy_start + (y_end - y_start)
        gx_start = radius - (x - x_start)
        gx_end = gx_start + (x_end - x_start)

        image_data[y_start:y_end, x_start:x_end] += gaussian[gy_start:gy_end, gx_start:gx_end]

    # Create FITS HDU
    hdu = fits.PrimaryHDU(data=image_data)
    hdu.header["OBJECT"] = "Test Star Field"
    hdu.header["EXPTIME"] = 300.0
    hdu.header["TELESCOP"] = "Seestar S50"
    hdu.header["DATE-OBS"] = "2025-11-07T00:00:00"

    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".fits", delete=False)
    hdu.writeto(temp_file.name, overwrite=True)

    print(f"✓ Created test FITS: {temp_file.name}")
    print(f"  Size: {size}x{size} pixels")
    print(f"  Stars: {num_stars}")
    print(f"  File size: {os.path.getsize(temp_file.name) / 1024 / 1024:.2f} MB")

    return temp_file.name


def test_api_health():
    """Test that the API is reachable."""
    print("\n🏥 Checking API health...")

    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        response.raise_for_status()

        data = response.json()
        print(f"✓ API is healthy: {data}")
        return True

    except Exception as e:
        print(f"✗ API health check failed: {e}")
        print("\n💡 Make sure Docker services are running:")
        print("   docker-compose up -d")
        return False


def create_session():
    """Create a processing session."""
    print("\n📁 Creating processing session...")

    session_name = f"test_session_{int(time.time())}"

    try:
        response = requests.post(f"{API_BASE}/process/sessions", json={"session_name": session_name}, timeout=10)
        response.raise_for_status()

        session = response.json()
        print(f"✓ Created session: {session['session_name']} (ID: {session['id']})")
        return session["id"]

    except Exception as e:
        print(f"✗ Failed to create session: {e}")
        return None


def upload_file(session_id, fits_file):
    """Upload FITS file to session."""
    print(f"\n📤 Uploading FITS file...")

    try:
        with open(fits_file, "rb") as f:
            files = {"file": (os.path.basename(fits_file), f, "application/fits")}
            data = {"file_type": "stacked"}

            response = requests.post(
                f"{API_BASE}/process/sessions/{session_id}/upload", files=files, data=data, timeout=30
            )
            response.raise_for_status()

        result = response.json()
        print(f"✓ Uploaded: {result['filename']} ({result['size_bytes'] / 1024 / 1024:.2f} MB)")
        return True

    except Exception as e:
        print(f"✗ Upload failed: {e}")
        return False


def finalize_session(session_id):
    """Finalize the session."""
    print(f"\n✅ Finalizing session...")

    try:
        response = requests.post(f"{API_BASE}/process/sessions/{session_id}/finalize", timeout=10)
        response.raise_for_status()

        print(f"✓ Session finalized and ready for processing")
        return True

    except Exception as e:
        print(f"✗ Finalize failed: {e}")
        return False


def start_processing(session_id, preset="quick_dso"):
    """Start processing job."""
    print(f"\n⚙️  Starting processing with preset '{preset}'...")

    try:
        response = requests.post(
            f"{API_BASE}/process/sessions/{session_id}/process", json={"pipeline_name": preset}, timeout=10
        )
        response.raise_for_status()

        job = response.json()
        print(f"✓ Processing job started (ID: {job['id']})")
        return job["id"]

    except Exception as e:
        print(f"✗ Failed to start processing: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response: {e.response.text}")
        return None


def monitor_job(job_id, timeout=TIMEOUT):
    """Monitor job progress until completion."""
    print(f"\n⏳ Monitoring job progress (timeout: {timeout}s)...")

    start_time = time.time()
    last_status = None
    last_progress = -1

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{API_BASE}/process/jobs/{job_id}", timeout=5)
            response.raise_for_status()

            job = response.json()
            status = job["status"]
            progress = job.get("progress_percent", 0)
            current_step = job.get("current_step", "")

            # Print updates
            if status != last_status or progress != last_progress:
                status_icon = {"pending": "⏸️", "running": "🔄", "complete": "✅", "failed": "❌"}.get(status, "❓")

                print(f"  {status_icon} {status.upper()}: {progress:.1f}% - {current_step}")
                last_status = status
                last_progress = progress

            # Check if done
            if status in ["complete", "failed"]:
                if status == "complete":
                    print(f"\n✅ Processing completed successfully!")
                    if "output_file" in job:
                        print(f"   Output: {job['output_file']}")
                    return True
                else:
                    print(f"\n❌ Processing failed!")
                    if "error_message" in job:
                        print(f"   Error: {job['error_message']}")
                    return False

            time.sleep(2)

        except Exception as e:
            print(f"✗ Error checking job status: {e}")
            time.sleep(2)

    print(f"\n⏱️  Timeout reached after {timeout}s")
    return False


def download_result(job_id, output_dir="."):
    """Download the processed result."""
    print(f"\n📥 Downloading result...")

    try:
        response = requests.get(f"{API_BASE}/process/jobs/{job_id}/download", timeout=30, stream=True)
        response.raise_for_status()

        # Get filename from Content-Disposition header
        filename = "result.jpg"
        if "Content-Disposition" in response.headers:
            import re

            match = re.search(r'filename="(.+)"', response.headers["Content-Disposition"])
            if match:
                filename = match.group(1)

        output_path = os.path.join(output_dir, filename)

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✓ Downloaded: {output_path} ({os.path.getsize(output_path) / 1024:.1f} KB)")
        return output_path

    except Exception as e:
        print(f"✗ Download failed: {e}")
        return None


def main():
    """Run the complete test workflow."""
    print("=" * 60)
    print("🧪 Astro Planner Processing Pipeline Test")
    print("=" * 60)

    # Step 1: Check API
    if not test_api_health():
        print("\n❌ Test failed: API not accessible")
        sys.exit(1)

    # Step 2: Create test FITS
    fits_file = None
    try:
        fits_file = create_test_fits()

        # Step 3: Create session
        session_id = create_session()
        if not session_id:
            print("\n❌ Test failed: Could not create session")
            sys.exit(1)

        # Step 4: Upload file
        if not upload_file(session_id, fits_file):
            print("\n❌ Test failed: Could not upload file")
            sys.exit(1)

        # Step 5: Finalize session
        if not finalize_session(session_id):
            print("\n❌ Test failed: Could not finalize session")
            sys.exit(1)

        # Step 6: Start processing
        job_id = start_processing(session_id, preset="quick_dso")
        if not job_id:
            print("\n❌ Test failed: Could not start processing")
            sys.exit(1)

        # Step 7: Monitor until completion
        success = monitor_job(job_id)
        if not success:
            print("\n❌ Test failed: Processing did not complete successfully")
            sys.exit(1)

        # Step 8: Download result
        result_file = download_result(job_id)
        if result_file:
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED!")
            print("=" * 60)
            print(f"\n📄 Result saved to: {result_file}")
            sys.exit(0)
        else:
            print("\n⚠️  Processing succeeded but download failed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # Cleanup
        if fits_file and os.path.exists(fits_file):
            os.remove(fits_file)
            print(f"\n🧹 Cleaned up temporary file: {fits_file}")


if __name__ == "__main__":
    main()
