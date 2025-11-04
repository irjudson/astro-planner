#!/usr/bin/env python3
"""Quick test of comet service functionality."""

import sys
sys.path.insert(0, 'backend')

from datetime import datetime
from app.services.comet_service import CometService
from app.models import CometTarget, OrbitalElements, Location

# Create a test comet (C/2020 F3 NEOWISE-like parameters)
orbital_elements = OrbitalElements(
    epoch_jd=2459000.5,  # Approximate epoch
    perihelion_distance_au=0.29,
    eccentricity=0.999,  # Nearly parabolic
    inclination_deg=128.9,
    arg_perihelion_deg=37.3,
    ascending_node_deg=61.0,
    perihelion_time_jd=2459034.0  # July 3, 2020
)

test_comet = CometTarget(
    designation="C/2020 F3",
    name="NEOWISE",
    orbital_elements=orbital_elements,
    absolute_magnitude=3.0,
    magnitude_slope=4.0,
    current_magnitude=7.0,
    comet_type="long-period",
    activity_status="active",
    discovery_date="2020-03-27",
    data_source="manual",
    notes="Test comet for validation"
)

print("Testing Comet Service")
print("=" * 60)

# Initialize service
service = CometService()
print("✓ Service initialized")

# Add comet
comet_id = service.add_comet(test_comet)
print(f"✓ Added test comet with ID: {comet_id}")

# Retrieve comet
retrieved = service.get_comet_by_designation("C/2020 F3")
if retrieved:
    print(f"✓ Retrieved comet: {retrieved.name} ({retrieved.designation})")
else:
    print("✗ Failed to retrieve comet")
    sys.exit(1)

# Compute ephemeris for current time
time_utc = datetime.now()
ephemeris = service.compute_ephemeris(retrieved, time_utc)
print(f"✓ Computed ephemeris for {time_utc.isoformat()}")
print(f"  RA: {ephemeris.ra_hours:.2f} hours")
print(f"  Dec: {ephemeris.dec_degrees:.2f} degrees")
print(f"  Distance: {ephemeris.geo_distance_au:.3f} AU")
if ephemeris.magnitude:
    print(f"  Magnitude: {ephemeris.magnitude:.1f}")

# Check visibility from Three Forks, MT
location = Location(
    name="Three Forks, MT",
    latitude=45.9183,
    longitude=-111.5433,
    elevation=1234.0,
    timezone="America/Denver"
)

visibility = service.compute_visibility(retrieved, location, time_utc)
print(f"✓ Computed visibility from {location.name}")
print(f"  Altitude: {visibility.altitude_deg:.1f}°")
print(f"  Azimuth: {visibility.azimuth_deg:.1f}°")
print(f"  Visible: {visibility.is_visible}")
print(f"  Dark enough: {visibility.is_dark_enough}")
print(f"  Recommended: {visibility.recommended}")

print("\n✓ All tests passed!")
