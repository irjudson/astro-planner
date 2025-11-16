"""Test JPL Horizons integration."""

import sys
sys.path.insert(0, 'backend')

from app.services.horizons_service import HorizonsService
from datetime import datetime

def test_horizons():
    """Test fetching comet data from JPL Horizons."""
    service = HorizonsService()

    print("Testing JPL Horizons Integration...")
    print("=" * 60)

    # Test 1: Fetch a well-known periodic comet
    print("\n1. Fetching comet 1P/Halley...")
    try:
        halley = service.fetch_comet_by_designation("1P/Halley")
        if halley:
            print(f"   ✓ Successfully fetched {halley.name or halley.designation}")
            print(f"   - Type: {halley.comet_type}")
            print(f"   - Eccentricity: {halley.orbital_elements.eccentricity:.6f}")
            print(f"   - Perihelion distance: {halley.orbital_elements.perihelion_distance_au:.4f} AU")
            print(f"   - Current magnitude: {halley.current_magnitude}")
        else:
            print("   ✗ Failed to fetch Halley's comet")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Fetch a recent comet
    print("\n2. Fetching comet C/2020 F3 (NEOWISE)...")
    try:
        neowise = service.fetch_comet_by_designation("C/2020 F3")
        if neowise:
            print(f"   ✓ Successfully fetched {neowise.designation}")
            print(f"   - Type: {neowise.comet_type}")
            print(f"   - Absolute magnitude: {neowise.absolute_magnitude}")
            print(f"   - Perihelion time: JD {neowise.orbital_elements.perihelion_time_jd}")
        else:
            print("   ✗ Failed to fetch NEOWISE")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Fetch ephemeris
    print("\n3. Fetching ephemeris for 1P/Halley...")
    try:
        from datetime import timedelta
        start = datetime(2025, 1, 1)
        end = start + timedelta(days=7)

        eph = service.fetch_ephemeris("1P/Halley", start, end, step='1d')
        if eph and eph['data']:
            print(f"   ✓ Successfully fetched {len(eph['data'])} ephemeris points")
            first = eph['data'][0]
            print(f"   - First point: RA {first['ra_hours']:.2f}h, Dec {first['dec_degrees']:.2f}°")
            print(f"   - Distance: {first['delta_au']:.3f} AU from Earth")
            print(f"   - Magnitude: {first['magnitude']}")
        else:
            print("   ✗ Failed to fetch ephemeris")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "=" * 60)
    print("Horizons integration test complete!")

if __name__ == "__main__":
    test_horizons()
