"""Tests for catalog service."""

import pytest
from datetime import datetime
import pytz
from unittest.mock import MagicMock

from app.models import DSOTarget, Location, TargetVisibility
from app.services.catalog_service import CatalogService
from app.services.ephemeris_service import EphemerisService


def test_add_visibility_info():
    """Test adding visibility info to target."""
    # Mock database session
    db = MagicMock()
    service = CatalogService(db)

    # Mock ephemeris service
    ephemeris = MagicMock(spec=EphemerisService)
    ephemeris.calculate_position.return_value = (45.2, 180.5)  # alt, az
    ephemeris.calculate_twilight_times.return_value = {
        "astronomical_twilight_end": pytz.timezone("America/Denver").localize(datetime(2025, 11, 15, 19, 30)),
        "astronomical_twilight_start": pytz.timezone("America/Denver").localize(datetime(2025, 11, 16, 5, 30))
    }
    ephemeris.get_best_viewing_time.return_value = (
        pytz.timezone("America/Denver").localize(datetime(2025, 11, 15, 23, 30)),
        62.5
    )

    target = DSOTarget(
        name="M31",
        catalog_id="M31",
        ra_hours=0.71,
        dec_degrees=41.27,
        object_type="galaxy",
        magnitude=3.4,
        size_arcmin=190.0,
        description="Andromeda Galaxy"
    )

    location = Location(
        latitude=45.9183,
        longitude=-111.5433,
        elevation=1234,
        timezone="America/Denver"
    )

    current_time = pytz.timezone("America/Denver").localize(datetime(2025, 11, 15, 21, 0))

    # Add visibility
    enriched = service.add_visibility_info(target, location, ephemeris, current_time)

    assert enriched.visibility is not None
    assert enriched.visibility.current_altitude == 45.2
    assert enriched.visibility.status == "visible"
    assert enriched.visibility.best_altitude_tonight == 62.5
