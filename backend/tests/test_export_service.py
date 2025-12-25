"""Tests for export service."""

import csv
import json
from datetime import datetime
from io import StringIO

import pytest

from app.models import DSOTarget, Location, ObservingPlan, ScheduledTarget, SessionInfo, TargetScore, WeatherForecast
from app.services.export_service import ExportService


@pytest.fixture
def export_service():
    """Create export service instance."""
    return ExportService()


@pytest.fixture
def sample_location():
    """Create sample location."""
    return Location(
        name="Three Forks, MT", latitude=45.92, longitude=-111.28, elevation=1234.0, timezone="America/Denver"
    )


@pytest.fixture
def sample_session():
    """Create sample observing session."""
    return SessionInfo(
        observing_date="2025-01-15",
        sunset=datetime(2025, 1, 15, 17, 30),
        civil_twilight_end=datetime(2025, 1, 15, 18, 0),
        nautical_twilight_end=datetime(2025, 1, 15, 18, 30),
        astronomical_twilight_end=datetime(2025, 1, 15, 19, 0),
        astronomical_twilight_start=datetime(2025, 1, 16, 6, 0),
        nautical_twilight_start=datetime(2025, 1, 16, 6, 30),
        civil_twilight_start=datetime(2025, 1, 16, 7, 0),
        sunrise=datetime(2025, 1, 16, 7, 45),
        imaging_start=datetime(2025, 1, 15, 19, 30),
        imaging_end=datetime(2025, 1, 16, 5, 30),
        total_imaging_minutes=600,
    )


@pytest.fixture
def sample_target():
    """Create sample DSO target."""
    return DSOTarget(
        name="Andromeda Galaxy",
        catalog_id="M31",
        object_type="galaxy",
        ra_hours=0.7122,
        dec_degrees=41.269,
        magnitude=3.4,
        size_arcmin=190.0,
        description="Nearest major galaxy",
    )


@pytest.fixture
def sample_scheduled_target(sample_target):
    """Create sample scheduled target."""
    return ScheduledTarget(
        target=sample_target,
        start_time=datetime(2025, 1, 15, 20, 0),
        end_time=datetime(2025, 1, 15, 23, 0),
        duration_minutes=180,
        start_altitude=45.0,
        end_altitude=60.0,
        start_azimuth=120.0,
        end_azimuth=180.0,
        field_rotation_rate=0.5,
        recommended_exposure=10,
        recommended_frames=180,
        score=TargetScore(visibility_score=0.95, weather_score=0.90, object_score=0.85, total_score=0.90),
    )


@pytest.fixture
def sample_weather():
    """Create sample weather forecast."""
    return [
        WeatherForecast(
            timestamp=datetime(2025, 1, 15, 20, 0),
            cloud_cover=10.0,
            humidity=40.0,
            temperature=5.0,
            wind_speed=5.0,
            conditions="Clear",
            seeing_arcseconds=3.0,
            transparency_magnitude=5.5,
        ),
        WeatherForecast(
            timestamp=datetime(2025, 1, 15, 22, 0),
            cloud_cover=15.0,
            humidity=45.0,
            temperature=3.0,
            wind_speed=7.0,
            conditions="Partly cloudy",
            seeing_arcseconds=3.2,
            transparency_magnitude=5.0,
        ),
    ]


@pytest.fixture
def sample_plan(sample_location, sample_session, sample_scheduled_target, sample_weather):
    """Create sample observing plan."""
    return ObservingPlan(
        location=sample_location,
        session=sample_session,
        scheduled_targets=[sample_scheduled_target],
        weather_forecast=sample_weather,
        total_targets=1,
        coverage_percent=30.0,
        generated_at=datetime(2025, 1, 14, 12, 0, 0),
    )


@pytest.fixture
def sample_plan_no_weather(sample_location, sample_session, sample_scheduled_target):
    """Create sample observing plan without weather."""
    return ObservingPlan(
        location=sample_location,
        session=sample_session,
        scheduled_targets=[sample_scheduled_target],
        weather_forecast=[],  # Empty list, not None
        total_targets=1,
        coverage_percent=30.0,
        generated_at=datetime(2025, 1, 14, 12, 0, 0),
    )


class TestExportJSON:
    """Test JSON export functionality."""

    def test_export_json_returns_valid_json(self, export_service, sample_plan):
        """Test that export_json returns valid JSON."""
        result = export_service.export_json(sample_plan)

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed is not None

    def test_export_json_contains_location(self, export_service, sample_plan):
        """Test that JSON export contains location data."""
        result = export_service.export_json(sample_plan)
        parsed = json.loads(result)

        assert "location" in parsed
        assert parsed["location"]["name"] == "Three Forks, MT"
        assert parsed["location"]["latitude"] == 45.92

    def test_export_json_contains_targets(self, export_service, sample_plan):
        """Test that JSON export contains target data."""
        result = export_service.export_json(sample_plan)
        parsed = json.loads(result)

        assert "scheduled_targets" in parsed
        assert len(parsed["scheduled_targets"]) == 1
        assert parsed["scheduled_targets"][0]["target"]["name"] == "Andromeda Galaxy"


class TestExportSeestarPlanMode:
    """Test Seestar Plan Mode export functionality."""

    def test_export_seestar_plan_returns_valid_json(self, export_service, sample_plan):
        """Test that seestar_plan export returns valid JSON."""
        result = export_service.export_seestar_plan_mode(sample_plan)

        parsed = json.loads(result)
        assert parsed is not None

    def test_export_seestar_plan_has_format_marker(self, export_service, sample_plan):
        """Test that seestar_plan export has format marker."""
        result = export_service.export_seestar_plan_mode(sample_plan)
        parsed = json.loads(result)

        assert parsed["format"] == "seestar_plan_v1"

    def test_export_seestar_plan_contains_location(self, export_service, sample_plan):
        """Test that seestar_plan export contains location."""
        result = export_service.export_seestar_plan_mode(sample_plan)
        parsed = json.loads(result)

        assert "location" in parsed
        assert parsed["location"]["name"] == "Three Forks, MT"
        assert parsed["location"]["timezone"] == "America/Denver"

    def test_export_seestar_plan_contains_targets(self, export_service, sample_plan):
        """Test that seestar_plan export contains targets with correct fields."""
        result = export_service.export_seestar_plan_mode(sample_plan)
        parsed = json.loads(result)

        assert "targets" in parsed
        assert len(parsed["targets"]) == 1

        target = parsed["targets"][0]
        assert target["target_name"] == "Andromeda Galaxy"
        assert target["ra"] == 0.7122
        assert target["dec"] == 41.269
        assert target["duration_min"] == 180
        assert target["gain"] == 80
        assert target["exposure_sec"] == 10
        assert target["frames"] == 180
        assert target["filter"] == "LP"

    def test_export_seestar_plan_contains_session_info(self, export_service, sample_plan):
        """Test that seestar_plan export contains session info."""
        result = export_service.export_seestar_plan_mode(sample_plan)
        parsed = json.loads(result)

        assert "session_date" in parsed
        assert "imaging_start" in parsed
        assert "imaging_end" in parsed
        assert "generated_at" in parsed


class TestExportSeestarALP:
    """Test Seestar ALP CSV export functionality."""

    def test_export_seestar_alp_returns_string(self, export_service, sample_plan):
        """Test that seestar_alp export returns a string."""
        result = export_service.export_seestar_alp(sample_plan)
        assert isinstance(result, str)

    def test_export_seestar_alp_has_header_comments(self, export_service, sample_plan):
        """Test that seestar_alp export has header comments."""
        result = export_service.export_seestar_alp(sample_plan)

        assert "# Seestar S50 Observing Plan" in result
        assert "# Location: Three Forks, MT" in result
        assert "# Total Targets: 1" in result
        assert "# Import Instructions:" in result

    def test_export_seestar_alp_has_csv_header(self, export_service, sample_plan):
        """Test that seestar_alp export has CSV header."""
        result = export_service.export_seestar_alp(sample_plan)

        assert "TARGET_NAME,RA_HOURS,DEC_DEGREES,START_TIME,DURATION_MIN,EXPOSURE_SEC,FRAMES" in result

    def test_export_seestar_alp_has_data_row(self, export_service, sample_plan):
        """Test that seestar_alp export has data rows."""
        result = export_service.export_seestar_alp(sample_plan)
        lines = result.split("\n")

        # Find data lines (not comments, not header)
        data_lines = [line for line in lines if line and not line.startswith("#") and not line.startswith("TARGET_NAME")]

        assert len(data_lines) == 1
        assert "M31" in data_lines[0]
        assert "0.7122" in data_lines[0]
        assert "180" in data_lines[0]  # Duration


class TestExportText:
    """Test text export functionality."""

    def test_export_text_returns_string(self, export_service, sample_plan):
        """Test that text export returns a string."""
        result = export_service.export_text(sample_plan)
        assert isinstance(result, str)

    def test_export_text_has_header(self, export_service, sample_plan):
        """Test that text export has header."""
        result = export_service.export_text(sample_plan)

        assert "SEESTAR S50 OBSERVING PLAN" in result
        assert "=" * 80 in result

    def test_export_text_contains_location(self, export_service, sample_plan):
        """Test that text export contains location info."""
        result = export_service.export_text(sample_plan)

        assert "Location: Three Forks, MT" in result
        assert "Coordinates: 45.9200" in result
        assert "Elevation: 1234m" in result

    def test_export_text_contains_session_info(self, export_service, sample_plan):
        """Test that text export contains session info."""
        result = export_service.export_text(sample_plan)

        assert "Observing Date: 2025-01-15" in result
        assert "Total Imaging Time: 600 minutes" in result

    def test_export_text_contains_weather_when_present(self, export_service, sample_plan):
        """Test that text export contains weather summary when present."""
        result = export_service.export_text(sample_plan)

        assert "Weather Forecast (Average):" in result
        assert "Cloud Cover:" in result
        assert "Humidity:" in result

    def test_export_text_no_weather_section_when_absent(self, export_service, sample_plan_no_weather):
        """Test that text export omits weather when not present."""
        result = export_service.export_text(sample_plan_no_weather)

        assert "Weather Forecast (Average):" not in result

    def test_export_text_contains_targets(self, export_service, sample_plan):
        """Test that text export contains target info."""
        result = export_service.export_text(sample_plan)

        assert "SCHEDULED TARGETS" in result
        assert "1. Andromeda Galaxy (M31)" in result
        assert "Type: Galaxy" in result
        assert "Altitude:" in result
        assert "Score:" in result

    def test_export_text_contains_target_description(self, export_service, sample_plan):
        """Test that text export contains target description."""
        result = export_service.export_text(sample_plan)

        assert "Notes: Nearest major galaxy" in result


class TestExportCSV:
    """Test CSV export functionality."""

    def test_export_csv_returns_string(self, export_service, sample_plan):
        """Test that CSV export returns a string."""
        result = export_service.export_csv(sample_plan)
        assert isinstance(result, str)

    def test_export_csv_is_valid_csv(self, export_service, sample_plan):
        """Test that CSV export is valid CSV."""
        result = export_service.export_csv(sample_plan)

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        # Should have header + 1 data row
        assert len(rows) == 2

    def test_export_csv_has_correct_header(self, export_service, sample_plan):
        """Test that CSV export has correct header."""
        result = export_service.export_csv(sample_plan)

        reader = csv.reader(StringIO(result))
        header = next(reader)

        assert "Target Name" in header
        assert "Catalog ID" in header
        assert "RA (hours)" in header
        assert "Dec (degrees)" in header
        assert "Start Time" in header
        assert "Duration (min)" in header
        assert "Total Score" in header

    def test_export_csv_has_correct_data(self, export_service, sample_plan):
        """Test that CSV export has correct data."""
        result = export_service.export_csv(sample_plan)

        reader = csv.DictReader(StringIO(result))
        row = next(reader)

        assert row["Target Name"] == "Andromeda Galaxy"
        assert row["Catalog ID"] == "M31"
        assert row["Type"] == "galaxy"
        assert row["Duration (min)"] == "180"


class TestExportDispatcher:
    """Test the export dispatcher method."""

    def test_export_json_format(self, export_service, sample_plan):
        """Test export with json format."""
        result = export_service.export(sample_plan, "json")
        parsed = json.loads(result)
        assert "location" in parsed

    def test_export_seestar_plan_format(self, export_service, sample_plan):
        """Test export with seestar_plan format."""
        result = export_service.export(sample_plan, "seestar_plan")
        parsed = json.loads(result)
        assert parsed["format"] == "seestar_plan_v1"

    def test_export_seestar_alp_format(self, export_service, sample_plan):
        """Test export with seestar_alp format."""
        result = export_service.export(sample_plan, "seestar_alp")
        assert "TARGET_NAME,RA_HOURS" in result

    def test_export_text_format(self, export_service, sample_plan):
        """Test export with text format."""
        result = export_service.export(sample_plan, "text")
        assert "SEESTAR S50 OBSERVING PLAN" in result

    def test_export_csv_format(self, export_service, sample_plan):
        """Test export with csv format."""
        result = export_service.export(sample_plan, "csv")
        assert "Target Name" in result

    def test_export_case_insensitive(self, export_service, sample_plan):
        """Test that export format is case-insensitive."""
        result1 = export_service.export(sample_plan, "JSON")
        result2 = export_service.export(sample_plan, "json")
        assert result1 == result2

    def test_export_unknown_format_raises(self, export_service, sample_plan):
        """Test that unknown format raises ValueError."""
        with pytest.raises(ValueError, match="Unknown format"):
            export_service.export(sample_plan, "unknown_format")

    def test_export_unknown_format_message(self, export_service, sample_plan):
        """Test error message for unknown format."""
        try:
            export_service.export(sample_plan, "xml")
        except ValueError as e:
            assert "xml" in str(e)


class TestMultipleTargets:
    """Test export with multiple targets."""

    @pytest.fixture
    def multi_target_plan(self, sample_location, sample_session, sample_weather):
        """Create plan with multiple targets."""
        targets = [
            ScheduledTarget(
                target=DSOTarget(
                    name="Andromeda Galaxy",
                    catalog_id="M31",
                    object_type="galaxy",
                    ra_hours=0.7122,
                    dec_degrees=41.269,
                    magnitude=3.4,
                    size_arcmin=190.0,
                    description="Nearest major galaxy",
                ),
                start_time=datetime(2025, 1, 15, 20, 0),
                end_time=datetime(2025, 1, 15, 21, 30),
                duration_minutes=90,
                start_altitude=45.0,
                end_altitude=55.0,
                start_azimuth=120.0,
                end_azimuth=150.0,
                field_rotation_rate=0.5,
                recommended_exposure=10,
                recommended_frames=90,
                score=TargetScore(visibility_score=0.95, weather_score=0.90, object_score=0.85, total_score=0.90),
            ),
            ScheduledTarget(
                target=DSOTarget(
                    name="Orion Nebula",
                    catalog_id="M42",
                    object_type="nebula",
                    ra_hours=5.583,
                    dec_degrees=-5.391,
                    magnitude=4.0,
                    size_arcmin=65.0,
                    description="Famous emission nebula",
                ),
                start_time=datetime(2025, 1, 15, 22, 0),
                end_time=datetime(2025, 1, 15, 23, 30),
                duration_minutes=90,
                start_altitude=40.0,
                end_altitude=50.0,
                start_azimuth=180.0,
                end_azimuth=210.0,
                field_rotation_rate=0.4,
                recommended_exposure=10,
                recommended_frames=90,
                score=TargetScore(visibility_score=0.90, weather_score=0.85, object_score=0.90, total_score=0.88),
            ),
        ]

        return ObservingPlan(
            location=sample_location,
            session=sample_session,
            scheduled_targets=targets,
            weather_forecast=sample_weather,
            total_targets=2,
            coverage_percent=60.0,
            generated_at=datetime(2025, 1, 14, 12, 0, 0),
        )

    def test_csv_has_multiple_rows(self, export_service, multi_target_plan):
        """Test that CSV export has multiple data rows."""
        result = export_service.export_csv(multi_target_plan)

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        # Header + 2 data rows
        assert len(rows) == 3

    def test_seestar_plan_has_multiple_targets(self, export_service, multi_target_plan):
        """Test that seestar_plan has multiple targets."""
        result = export_service.export_seestar_plan_mode(multi_target_plan)
        parsed = json.loads(result)

        assert len(parsed["targets"]) == 2
        assert parsed["targets"][0]["target_name"] == "Andromeda Galaxy"
        assert parsed["targets"][1]["target_name"] == "Orion Nebula"

    def test_text_export_numbers_targets(self, export_service, multi_target_plan):
        """Test that text export numbers targets correctly."""
        result = export_service.export_text(multi_target_plan)

        assert "1. Andromeda Galaxy (M31)" in result
        assert "2. Orion Nebula (M42)" in result
