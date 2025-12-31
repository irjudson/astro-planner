"""Tests for captures API endpoints."""

import pytest
from app.models.capture_models import CaptureHistory, OutputFile
from datetime import datetime


@pytest.fixture
def sample_capture_history(override_get_db):
    """Create sample capture history."""
    db = override_get_db
    capture = CaptureHistory(
        catalog_id="M31",
        total_exposure_seconds=7200,
        total_frames=720,
        total_sessions=3,
        status="needs_more_data",
        best_fwhm=2.3,
        best_star_count=2847
    )
    db.add(capture)
    db.commit()
    db.refresh(capture)
    return capture


def test_list_captures_empty(client):
    """Test listing captures when none exist."""
    response = client.get("/api/captures")
    assert response.status_code == 200
    assert response.json() == []


def test_list_captures(client, sample_capture_history):
    """Test listing all captures."""
    response = client.get("/api/captures")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]['catalog_id'] == "M31"
    assert data[0]['total_exposure_seconds'] == 7200


def test_get_capture_by_catalog_id(client, sample_capture_history):
    """Test getting specific capture by catalog ID."""
    response = client.get("/api/captures/M31")
    assert response.status_code == 200

    data = response.json()
    assert data['catalog_id'] == "M31"
    assert data['total_frames'] == 720


def test_get_capture_not_found(client):
    """Test getting non-existent capture."""
    response = client.get("/api/captures/NGC9999")
    assert response.status_code == 404
