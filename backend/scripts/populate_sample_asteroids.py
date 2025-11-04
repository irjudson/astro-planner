#!/usr/bin/env python3
"""Populate database with sample asteroids (Ceres, Vesta, Pallas, Juno)."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.asteroid_service import AsteroidService
from app.models import AsteroidTarget, AsteroidOrbitalElements


def populate_sample_asteroids():
    """Add sample asteroids to the database."""
    service = AsteroidService()

    # Sample asteroids with realistic orbital elements
    # Data approximated from JPL Small-Body Database
    asteroids = [
        AsteroidTarget(
            designation="1 Ceres",
            name="Ceres",
            number=1,
            orbital_elements=AsteroidOrbitalElements(
                epoch_jd=2460000.5,  # Epoch: 2023-Feb-25
                semi_major_axis_au=2.769,
                eccentricity=0.0760,
                inclination_deg=10.59,
                arg_perihelion_deg=73.60,
                ascending_node_deg=80.31,
                mean_anomaly_deg=77.37
            ),
            absolute_magnitude=3.53,
            slope_parameter=0.12,
            current_magnitude=7.0,
            diameter_km=939.4,
            albedo=0.090,
            spectral_type="C",
            rotation_period_hours=9.07,
            asteroid_type="MBA",  # Main Belt Asteroid
            data_source="manual",
            notes="Largest asteroid and dwarf planet in the main belt"
        ),
        AsteroidTarget(
            designation="4 Vesta",
            name="Vesta",
            number=4,
            orbital_elements=AsteroidOrbitalElements(
                epoch_jd=2460000.5,
                semi_major_axis_au=2.362,
                eccentricity=0.0886,
                inclination_deg=7.14,
                arg_perihelion_deg=150.80,
                ascending_node_deg=103.85,
                mean_anomaly_deg=205.80
            ),
            absolute_magnitude=3.20,
            slope_parameter=0.32,
            current_magnitude=6.5,
            diameter_km=525.4,
            albedo=0.423,
            spectral_type="V",
            rotation_period_hours=5.34,
            asteroid_type="MBA",
            data_source="manual",
            notes="Second-largest asteroid, brightest asteroid visible from Earth"
        ),
        AsteroidTarget(
            designation="2 Pallas",
            name="Pallas",
            number=2,
            orbital_elements=AsteroidOrbitalElements(
                epoch_jd=2460000.5,
                semi_major_axis_au=2.773,
                eccentricity=0.2313,
                inclination_deg=34.83,
                arg_perihelion_deg=310.04,
                ascending_node_deg=173.09,
                mean_anomaly_deg=78.22
            ),
            absolute_magnitude=4.13,
            slope_parameter=0.11,
            current_magnitude=8.0,
            diameter_km=512.0,
            albedo=0.159,
            spectral_type="B",
            rotation_period_hours=7.81,
            asteroid_type="MBA",
            data_source="manual",
            notes="Third-largest asteroid with highly inclined orbit"
        ),
        AsteroidTarget(
            designation="3 Juno",
            name="Juno",
            number=3,
            orbital_elements=AsteroidOrbitalElements(
                epoch_jd=2460000.5,
                semi_major_axis_au=2.669,
                eccentricity=0.2577,
                inclination_deg=12.98,
                arg_perihelion_deg=248.41,
                ascending_node_deg=169.87,
                mean_anomaly_deg=100.50
            ),
            absolute_magnitude=5.33,
            slope_parameter=0.23,
            current_magnitude=9.0,
            diameter_km=246.6,
            albedo=0.238,
            spectral_type="S",
            rotation_period_hours=7.21,
            asteroid_type="MBA",
            data_source="manual",
            notes="One of the larger S-type asteroids in the main belt"
        ),
        AsteroidTarget(
            designation="433 Eros",
            name="Eros",
            number=433,
            orbital_elements=AsteroidOrbitalElements(
                epoch_jd=2460000.5,
                semi_major_axis_au=1.458,
                eccentricity=0.2229,
                inclination_deg=10.83,
                arg_perihelion_deg=178.64,
                ascending_node_deg=304.40,
                mean_anomaly_deg=320.30
            ),
            absolute_magnitude=10.4,
            slope_parameter=0.46,
            current_magnitude=12.0,
            diameter_km=16.8,
            albedo=0.25,
            spectral_type="S",
            rotation_period_hours=5.27,
            asteroid_type="NEA",  # Near-Earth Asteroid
            data_source="manual",
            notes="Well-studied near-Earth asteroid, visited by NEAR Shoemaker spacecraft"
        ),
        AsteroidTarget(
            designation="16 Psyche",
            name="Psyche",
            number=16,
            orbital_elements=AsteroidOrbitalElements(
                epoch_jd=2460000.5,
                semi_major_axis_au=2.923,
                eccentricity=0.1339,
                inclination_deg=3.10,
                arg_perihelion_deg=228.03,
                ascending_node_deg=150.29,
                mean_anomaly_deg=235.70
            ),
            absolute_magnitude=5.9,
            slope_parameter=0.14,
            current_magnitude=9.5,
            diameter_km=226.0,
            albedo=0.120,
            spectral_type="M",
            rotation_period_hours=4.20,
            asteroid_type="MBA",
            data_source="manual",
            notes="Metallic asteroid, target of NASA's Psyche mission"
        )
    ]

    print("Populating sample asteroids...")
    print()

    for asteroid in asteroids:
        try:
            # Check if asteroid already exists
            existing = service.get_asteroid_by_designation(asteroid.designation)
            if existing:
                print(f"  ⏭️  {asteroid.name} ({asteroid.designation}) already exists, skipping")
                continue

            asteroid_id = service.add_asteroid(asteroid)
            print(f"  ✓ Added {asteroid.name} ({asteroid.designation}) - ID: {asteroid_id}")
            print(f"    Magnitude: {asteroid.current_magnitude}, "
                  f"Diameter: {asteroid.diameter_km} km, "
                  f"Type: {asteroid.spectral_type}")
        except Exception as e:
            print(f"  ✗ Error adding {asteroid.name}: {e}")

    print()
    print("✓ Sample asteroids populated successfully!")


if __name__ == "__main__":
    populate_sample_asteroids()
