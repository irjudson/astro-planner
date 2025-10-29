#!/usr/bin/env python3
"""
Test script for Astro Planner API.

This script tests the main API endpoints to ensure the application is working correctly.
"""

import requests
import json
from datetime import datetime, timedelta
import sys


# API base URL
BASE_URL = "http://localhost:8000/api"


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_health():
    """Test the health check endpoint."""
    print_section("Testing Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        data = response.json()
        print(f"✓ Health check passed")
        print(f"  Status: {data['status']}")
        print(f"  Service: {data['service']}")
        print(f"  Version: {data['version']}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False


def test_list_targets():
    """Test listing all targets."""
    print_section("Testing List Targets")
    try:
        response = requests.get(f"{BASE_URL}/targets")
        response.raise_for_status()
        data = response.json()
        print(f"✓ Retrieved {len(data)} targets")
        print(f"\nSample targets:")
        for target in data[:5]:
            print(f"  - {target['name']} ({target['catalog_id']}) - {target['object_type']}")
        return True
    except Exception as e:
        print(f"✗ Failed to list targets: {e}")
        return False


def test_get_target():
    """Test getting a specific target."""
    print_section("Testing Get Specific Target")
    target_id = "M31"
    try:
        response = requests.get(f"{BASE_URL}/targets/{target_id}")
        response.raise_for_status()
        data = response.json()
        print(f"✓ Retrieved target {target_id}")
        print(f"  Name: {data['name']}")
        print(f"  Type: {data['object_type']}")
        print(f"  RA: {data['ra_hours']} hours")
        print(f"  Dec: {data['dec_degrees']} degrees")
        print(f"  Magnitude: {data['magnitude']}")
        print(f"  Size: {data['size_arcmin']} arcmin")
        return True
    except Exception as e:
        print(f"✗ Failed to get target {target_id}: {e}")
        return False


def test_calculate_twilight():
    """Test twilight calculation."""
    print_section("Testing Twilight Calculation")
    try:
        # Use default location (Three Forks, MT)
        location = {
            "name": "Three Forks, MT",
            "latitude": 45.9183,
            "longitude": -111.5433,
            "elevation": 1234.0,
            "timezone": "America/Denver"
        }

        # Use today's date
        date = datetime.now().strftime("%Y-%m-%d")

        response = requests.post(
            f"{BASE_URL}/twilight",
            params={"date": date},
            json=location
        )
        response.raise_for_status()
        data = response.json()

        print(f"✓ Twilight times calculated for {date}")
        print(f"  Sunset: {data['sunset']}")
        print(f"  Astronomical twilight end: {data['astronomical_twilight_end']}")
        print(f"  Astronomical twilight start: {data['astronomical_twilight_start']}")
        print(f"  Sunrise: {data['sunrise']}")
        return True
    except Exception as e:
        print(f"✗ Failed to calculate twilight: {e}")
        return False


def test_generate_plan():
    """Test generating a complete observing plan."""
    print_section("Testing Plan Generation")
    try:
        # Create a plan request
        request_data = {
            "location": {
                "name": "Three Forks, MT",
                "latitude": 45.9183,
                "longitude": -111.5433,
                "elevation": 1234.0,
                "timezone": "America/Denver"
            },
            "observing_date": datetime.now().strftime("%Y-%m-%d"),
            "constraints": {
                "min_altitude": 30.0,
                "max_altitude": 80.0,
                "setup_time_minutes": 15,
                "object_types": ["galaxy", "nebula", "cluster", "planetary_nebula"]
            }
        }

        print(f"Generating plan for {request_data['observing_date']}...")
        response = requests.post(
            f"{BASE_URL}/plan",
            json=request_data
        )
        response.raise_for_status()
        plan = response.json()

        print(f"✓ Plan generated successfully")
        print(f"\nSession Information:")
        print(f"  Date: {plan['session']['observing_date']}")
        print(f"  Imaging window: {plan['session']['imaging_start']} to {plan['session']['imaging_end']}")
        print(f"  Total imaging time: {plan['session']['total_imaging_minutes']} minutes")
        print(f"\nPlan Summary:")
        print(f"  Total targets: {plan['total_targets']}")
        print(f"  Night coverage: {plan['coverage_percent']:.1f}%")

        if plan['scheduled_targets']:
            print(f"\nScheduled Targets:")
            for i, target in enumerate(plan['scheduled_targets'][:5], 1):
                print(f"  {i}. {target['target']['name']} ({target['target']['catalog_id']})")
                print(f"     Time: {target['start_time']} - {target['end_time']} ({target['duration_minutes']} min)")
                print(f"     Altitude: {target['start_altitude']:.1f}° - {target['end_altitude']:.1f}°")
                print(f"     Exposure: {target['recommended_exposure']}s × {target['recommended_frames']} frames")

            if len(plan['scheduled_targets']) > 5:
                print(f"  ... and {len(plan['scheduled_targets']) - 5} more targets")

        return plan
    except Exception as e:
        print(f"✗ Failed to generate plan: {e}")
        if hasattr(e, 'response'):
            print(f"  Response: {e.response.text}")
        return None


def test_export_plan(plan):
    """Test exporting a plan in different formats."""
    print_section("Testing Plan Export")

    if not plan:
        print("✗ No plan to export (plan generation failed)")
        return False

    formats = ["json", "seestar_plan", "seestar_alp", "text", "csv"]
    success = True

    for fmt in formats:
        try:
            response = requests.post(
                f"{BASE_URL}/export",
                params={"format": fmt},
                json=plan
            )
            response.raise_for_status()
            data = response.json()

            # Check that we got data back
            if data['data']:
                print(f"✓ Exported plan as {fmt} ({len(data['data'])} chars)")
            else:
                print(f"✗ Export {fmt} returned empty data")
                success = False

        except Exception as e:
            print(f"✗ Failed to export as {fmt}: {e}")
            success = False

    return success


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  ASTRO PLANNER API TEST SUITE")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("List Targets", test_list_targets()))
    results.append(("Get Target", test_get_target()))
    results.append(("Calculate Twilight", test_calculate_twilight()))

    plan = test_generate_plan()
    results.append(("Generate Plan", plan is not None))
    results.append(("Export Plan", test_export_plan(plan)))

    # Summary
    print_section("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
