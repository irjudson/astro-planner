"""Tests for Caldwell catalog integration."""

import pytest

from app.services.caldwell_catalog import CaldwellCatalog, CaldwellObject


class TestCaldwellObject:
    """Test CaldwellObject model."""

    def test_caldwell_object_creation(self):
        """Test creating a Caldwell object."""
        obj = CaldwellObject(
            caldwell_id="C1",
            ngc_id="NGC 188",
            common_name="",
            object_type="Open Cluster",
            constellation="Cepheus",
            ra_hours=0.785,
            dec_degrees=85.255,
            magnitude=8.1,
            size_arcmin=14.0,
        )
        assert obj.caldwell_id == "C1"
        assert obj.ngc_id == "NGC 188"
        assert obj.object_type == "Open Cluster"
        assert obj.constellation == "Cepheus"

    def test_caldwell_object_with_common_name(self):
        """Test Caldwell object with common name."""
        obj = CaldwellObject(
            caldwell_id="C14",
            ngc_id="NGC 869/884",
            common_name="Double Cluster",
            object_type="Open Cluster",
            constellation="Perseus",
            ra_hours=2.333,
            dec_degrees=57.133,
            magnitude=4.3,
            size_arcmin=30.0,
        )
        assert obj.common_name == "Double Cluster"


class TestCaldwellCatalog:
    """Test CaldwellCatalog service."""

    @pytest.fixture
    def catalog(self):
        """Create catalog instance."""
        return CaldwellCatalog()

    def test_catalog_initialization(self, catalog):
        """Test catalog loads objects."""
        assert len(catalog.objects) == 109
        assert all(isinstance(obj, CaldwellObject) for obj in catalog.objects)

    def test_get_by_caldwell_id(self, catalog):
        """Test getting object by Caldwell ID."""
        obj = catalog.get_by_id("C1")
        assert obj is not None
        assert obj.caldwell_id == "C1"
        assert obj.constellation == "Cepheus"

    def test_get_by_caldwell_id_not_found(self, catalog):
        """Test getting non-existent Caldwell ID."""
        obj = catalog.get_by_id("C999")
        assert obj is None

    def test_get_by_ngc_id(self, catalog):
        """Test getting object by NGC ID."""
        obj = catalog.get_by_ngc_id("NGC 188")
        assert obj is not None
        assert obj.caldwell_id == "C1"

    def test_get_by_common_name(self, catalog):
        """Test getting object by common name."""
        obj = catalog.get_by_common_name("Double Cluster")
        assert obj is not None
        assert obj.caldwell_id == "C14"

    def test_search_by_constellation(self, catalog):
        """Test searching by constellation."""
        objects = catalog.search_by_constellation("Perseus")
        assert len(objects) > 0
        assert all(obj.constellation == "Perseus" for obj in objects)

    def test_search_by_type(self, catalog):
        """Test searching by object type."""
        clusters = catalog.search_by_type("Open Cluster")
        assert len(clusters) > 0
        assert all(obj.object_type == "Open Cluster" for obj in clusters)

    def test_search_by_magnitude_range(self, catalog):
        """Test searching by magnitude range."""
        bright = catalog.search_by_magnitude(max_magnitude=6.0)
        assert len(bright) > 0
        assert all(obj.magnitude <= 6.0 for obj in bright)

    def test_get_observable_objects(self, catalog):
        """Test getting observable objects for location."""
        # Northern hemisphere location
        objects = catalog.get_observable(latitude=40.0, min_altitude=30.0)
        assert len(objects) > 0
        # Should include northern objects
        assert any(obj.dec_degrees > 30 for obj in objects)

    def test_caldwell_ngc_cross_reference(self, catalog):
        """Test cross-referencing with NGC catalog."""
        # C14 is the Double Cluster (NGC 869/884)
        c14 = catalog.get_by_id("C14")
        assert "869" in c14.ngc_id or "884" in c14.ngc_id
        assert c14.common_name == "Double Cluster"
