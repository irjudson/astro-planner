#!/usr/bin/env python3
"""
Test the simplified direct processing API.
"""

import requests
import sys
import time
from test_processing import create_test_fits

API_BASE = "http://localhost:9247/api"

def test_direct_processing():
    print("=" * 60)
    print("Testing Simplified Processing API")
    print("=" * 60)

    # Create test FITS
    print("\n📸 Creating test FITS...")
    fits_file = create_test_fits()
    print(f"✓ Created: {fits_file}")

    # Test quick preview
    print("\n⚙️  Testing Quick Preview...")
    response = requests.post(
        f"{API_BASE}/process/file",
        json={
            "file_path": fits_file,
            "processing_type": "quick_preview"
        },
        timeout=10
    )

    if response.status_code != 200:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        return False

    job = response.json()
    print(f"✓ Job started (ID: {job['id']})")

    # Poll for completion
    print("⏳ Waiting for completion...")
    start_time = time.time()
    while time.time() - start_time < 60:
        status_resp = requests.get(
            f"{API_BASE}/process/jobs/{job['id']}",
            timeout=5
        )

        job_status = status_resp.json()
        progress = job_status.get('progress_percent', 0)
        status = job_status['status']

        print(f"  {status.upper()}: {progress:.0f}%", end='\r')

        if status == 'complete':
            print(f"\n✓ Processing complete!")
            return True
        elif status == 'failed':
            print(f"\n✗ Processing failed: {job_status.get('error_message')}")
            return False

        time.sleep(2)

    print("\n⏱️  Timeout")
    return False

if __name__ == "__main__":
    success = test_direct_processing()
    sys.exit(0 if success else 1)
