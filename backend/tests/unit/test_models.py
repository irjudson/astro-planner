"""Tests for Pydantic models."""

from datetime import datetime
import pytz
import pytest
from pydantic import ValidationError

from app.models import TargetVisibility, VisibilityStatus


def test_target_visibility_model():
    """Test TargetVisibility Pydantic model."""
    tz = pytz.timezone("America/Denver")
    best_time = tz.localize(datetime(2025, 11, 15, 23, 30))

    visibility = TargetVisibility(
        current_altitude=45.2,
        current_azimuth=180.5,
        status=VisibilityStatus.VISIBLE,
        best_time_tonight=best_time,
        best_altitude_tonight=62.5,
        is_optimal_now=False,
    )

    assert visibility.current_altitude == 45.2
    assert visibility.status == VisibilityStatus.VISIBLE
    assert visibility.best_altitude_tonight == 62.5

    # Test JSON serialization
    json_data = visibility.model_dump()
    assert json_data["status"] == "visible"


def test_target_visibility_altitude_validation():
    """Test altitude must be in valid range."""
    # Valid altitude
    visibility = TargetVisibility(current_altitude=45.0, current_azimuth=180.0, status=VisibilityStatus.VISIBLE)
    assert visibility.current_altitude == 45.0

    # Invalid: too high
    with pytest.raises(ValidationError):
        TargetVisibility(current_altitude=95.0, current_azimuth=180.0, status=VisibilityStatus.VISIBLE)

    # Invalid: too low
    with pytest.raises(ValidationError):
        TargetVisibility(current_altitude=-95.0, current_azimuth=180.0, status=VisibilityStatus.VISIBLE)


def test_target_visibility_azimuth_validation():
    """Test azimuth must be in valid range."""
    # Invalid: >= 360
    with pytest.raises(ValidationError):
        TargetVisibility(current_altitude=45.0, current_azimuth=360.0, status=VisibilityStatus.VISIBLE)

    # Invalid: negative
    with pytest.raises(ValidationError):
        TargetVisibility(current_altitude=45.0, current_azimuth=-10.0, status=VisibilityStatus.VISIBLE)


def test_target_visibility_invalid_status():
    """Test invalid status values are rejected."""
    with pytest.raises(ValidationError):
        TargetVisibility(current_altitude=45.0, current_azimuth=180.0, status="invalid_status")


def test_dso_target_with_visibility():
    """Test DSOTarget with optional visibility field."""
    from app.models import DSOTarget, TargetVisibility, VisibilityStatus
    from datetime import datetime
    import pytz

    tz = pytz.timezone("America/Denver")
    best_time = tz.localize(datetime(2025, 11, 15, 23, 30))

    visibility = TargetVisibility(
        current_altitude=45.2,
        current_azimuth=180.5,
        status=VisibilityStatus.VISIBLE,
        best_time_tonight=best_time,
        best_altitude_tonight=62.5,
        is_optimal_now=False,
    )

    target = DSOTarget(
        name="M31",
        catalog_id="M31",
        ra_hours=0.71,
        dec_degrees=41.27,
        object_type="galaxy",
        magnitude=3.4,
        size_arcmin=190.0,
        description="Andromeda Galaxy",
        visibility=visibility,
    )

    assert target.visibility is not None
    assert target.visibility.status == VisibilityStatus.VISIBLE

    # Test without visibility (should still work)
    target_no_vis = DSOTarget(
        name="M42",
        catalog_id="M42",
        ra_hours=5.58,
        dec_degrees=-5.39,
        object_type="nebula",
        magnitude=4.0,
        size_arcmin=85.0,
        description="Orion Nebula",
    )

    assert target_no_vis.visibility is None
