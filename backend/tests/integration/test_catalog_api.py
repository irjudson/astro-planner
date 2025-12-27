"""Integration tests for catalog API."""

import pytest


def test_list_targets_with_visibility(client):
    """Test /api/targets endpoint with visibility calculations."""
    # Note: This requires location to be configured in settings
    response = client.get("/api/targets?limit=5&include_visibility=true")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

    # If location configured, should have visibility
    if len(data) > 0:
        target = data[0]
        assert "name" in target
        assert "catalog_id" in target
        # visibility may or may not be present depending on location config


def test_list_targets_sort_by_magnitude(client):
    """Test sorting by magnitude."""
    response = client.get("/api/targets?limit=10&sort_by=magnitude")

    assert response.status_code == 200
    data = response.json()

    # Should be sorted by magnitude ascending (brightest first)
    if len(data) > 1:
        assert data[0]["magnitude"] <= data[1]["magnitude"]


def test_list_targets_sort_by_size(client):
    """Test sorting by size."""
    response = client.get("/api/targets?limit=10&sort_by=size")

    assert response.status_code == 200
    data = response.json()

    # Should be sorted by size descending (largest first)
    if len(data) > 1:
        assert data[0]["size_arcmin"] >= data[1]["size_arcmin"]


def test_list_targets_sort_by_name(client):
    """Test sorting by name."""
    response = client.get("/api/targets?limit=10&sort_by=name")

    assert response.status_code == 200
    data = response.json()

    # Should be sorted alphabetically
    if len(data) > 1:
        assert data[0]["catalog_id"] <= data[1]["catalog_id"]
