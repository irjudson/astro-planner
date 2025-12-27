"""Tests for Pydantic models."""

from datetime import datetime
import pytz

from app.models import TargetVisibility


def test_target_visibility_model():
    """Test TargetVisibility Pydantic model."""
    tz = pytz.timezone("America/Denver")
    best_time = tz.localize(datetime(2025, 11, 15, 23, 30))

    visibility = TargetVisibility(
        current_altitude=45.2,
        current_azimuth=180.5,
        status="visible",
        best_time_tonight=best_time,
        best_altitude_tonight=62.5,
        is_optimal_now=False
    )

    assert visibility.current_altitude == 45.2
    assert visibility.status == "visible"
    assert visibility.best_altitude_tonight == 62.5

    # Test JSON serialization
    json_data = visibility.model_dump()
    assert json_data["status"] == "visible"
