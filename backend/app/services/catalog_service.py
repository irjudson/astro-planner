"""DSO catalog management service."""

from typing import List, Optional
from app.models import DSOTarget


class CatalogService:
    """Service for managing deep sky object catalog."""

    def __init__(self):
        """Initialize catalog with built-in targets."""
        self.targets = self._initialize_catalog()

    def _initialize_catalog(self) -> List[DSOTarget]:
        """
        Initialize catalog with popular targets optimized for Seestar S50.

        Criteria:
        - Appropriate size for 1.27° x 0.71° FOV
        - Bright enough for short exposures (10s max)
        - Good for alt-az mount (not too close to zenith)
        """
        catalog = [
            # Messier Objects - Galaxies
            DSOTarget(
                name="Andromeda Galaxy",
                catalog_id="M31",
                object_type="galaxy",
                ra_hours=0.712,
                dec_degrees=41.269,
                magnitude=3.4,
                size_arcmin=178.0,
                description="Large spiral galaxy in Andromeda"
            ),
            DSOTarget(
                name="Triangulum Galaxy",
                catalog_id="M33",
                object_type="galaxy",
                ra_hours=1.564,
                dec_degrees=30.660,
                magnitude=5.7,
                size_arcmin=70.8,
                description="Spiral galaxy in Triangulum"
            ),
            DSOTarget(
                name="Bode's Galaxy",
                catalog_id="M81",
                object_type="galaxy",
                ra_hours=9.928,
                dec_degrees=69.065,
                magnitude=6.9,
                size_arcmin=26.9,
                description="Spiral galaxy in Ursa Major"
            ),
            DSOTarget(
                name="Cigar Galaxy",
                catalog_id="M82",
                object_type="galaxy",
                ra_hours=9.928,
                dec_degrees=69.680,
                magnitude=8.4,
                size_arcmin=11.2,
                description="Starburst galaxy in Ursa Major"
            ),
            DSOTarget(
                name="Whirlpool Galaxy",
                catalog_id="M51",
                object_type="galaxy",
                ra_hours=13.498,
                dec_degrees=47.195,
                magnitude=8.4,
                size_arcmin=11.2,
                description="Interacting spiral galaxies in Canes Venatici"
            ),

            # Messier Objects - Nebulae
            DSOTarget(
                name="Orion Nebula",
                catalog_id="M42",
                object_type="nebula",
                ra_hours=5.583,
                dec_degrees=-5.391,
                magnitude=4.0,
                size_arcmin=65.0,
                description="Bright emission nebula in Orion"
            ),
            DSOTarget(
                name="Lagoon Nebula",
                catalog_id="M8",
                object_type="nebula",
                ra_hours=18.061,
                dec_degrees=-24.383,
                magnitude=6.0,
                size_arcmin=90.0,
                description="Emission nebula in Sagittarius"
            ),
            DSOTarget(
                name="Eagle Nebula",
                catalog_id="M16",
                object_type="nebula",
                ra_hours=18.314,
                dec_degrees=-13.783,
                magnitude=6.0,
                size_arcmin=35.0,
                description="Star-forming region with Pillars of Creation"
            ),
            DSOTarget(
                name="Omega Nebula",
                catalog_id="M17",
                object_type="nebula",
                ra_hours=18.347,
                dec_degrees=-16.183,
                magnitude=6.0,
                size_arcmin=46.0,
                description="Swan Nebula in Sagittarius"
            ),
            DSOTarget(
                name="Trifid Nebula",
                catalog_id="M20",
                object_type="nebula",
                ra_hours=18.035,
                dec_degrees=-23.033,
                magnitude=6.3,
                size_arcmin=28.0,
                description="Emission and reflection nebula"
            ),
            DSOTarget(
                name="Ring Nebula",
                catalog_id="M57",
                object_type="planetary_nebula",
                ra_hours=18.887,
                dec_degrees=33.029,
                magnitude=8.8,
                size_arcmin=1.4,
                description="Planetary nebula in Lyra"
            ),
            DSOTarget(
                name="Dumbbell Nebula",
                catalog_id="M27",
                object_type="planetary_nebula",
                ra_hours=19.991,
                dec_degrees=22.721,
                magnitude=7.5,
                size_arcmin=8.0,
                description="Planetary nebula in Vulpecula"
            ),

            # Messier Objects - Star Clusters
            DSOTarget(
                name="Pleiades",
                catalog_id="M45",
                object_type="cluster",
                ra_hours=3.783,
                dec_degrees=24.117,
                magnitude=1.6,
                size_arcmin=110.0,
                description="Open cluster in Taurus"
            ),
            DSOTarget(
                name="Beehive Cluster",
                catalog_id="M44",
                object_type="cluster",
                ra_hours=8.673,
                dec_degrees=19.983,
                magnitude=3.7,
                size_arcmin=95.0,
                description="Open cluster in Cancer"
            ),
            DSOTarget(
                name="Wild Duck Cluster",
                catalog_id="M11",
                object_type="cluster",
                ra_hours=18.850,
                dec_degrees=-6.267,
                magnitude=6.3,
                size_arcmin=14.0,
                description="Dense open cluster in Scutum"
            ),
            DSOTarget(
                name="Hercules Cluster",
                catalog_id="M13",
                object_type="cluster",
                ra_hours=16.695,
                dec_degrees=36.459,
                magnitude=5.8,
                size_arcmin=20.0,
                description="Globular cluster in Hercules"
            ),

            # NGC Objects
            DSOTarget(
                name="North America Nebula",
                catalog_id="NGC7000",
                object_type="nebula",
                ra_hours=20.975,
                dec_degrees=44.533,
                magnitude=4.0,
                size_arcmin=120.0,
                description="Emission nebula in Cygnus"
            ),
            DSOTarget(
                name="Rosette Nebula",
                catalog_id="NGC2237",
                object_type="nebula",
                ra_hours=6.533,
                dec_degrees=5.033,
                magnitude=9.0,
                size_arcmin=80.0,
                description="Emission nebula in Monoceros"
            ),
            DSOTarget(
                name="Flaming Star Nebula",
                catalog_id="IC405",
                object_type="nebula",
                ra_hours=5.270,
                dec_degrees=34.267,
                magnitude=6.0,
                size_arcmin=30.0,
                description="Emission nebula in Auriga"
            ),
            DSOTarget(
                name="Heart Nebula",
                catalog_id="IC1805",
                object_type="nebula",
                ra_hours=2.550,
                dec_degrees=61.450,
                magnitude=6.5,
                size_arcmin=60.0,
                description="Emission nebula in Cassiopeia"
            ),
            DSOTarget(
                name="Soul Nebula",
                catalog_id="IC1848",
                object_type="nebula",
                ra_hours=2.900,
                dec_degrees=60.433,
                magnitude=6.5,
                size_arcmin=60.0,
                description="Emission nebula in Cassiopeia"
            ),
            DSOTarget(
                name="Bubble Nebula",
                catalog_id="NGC7635",
                object_type="nebula",
                ra_hours=23.342,
                dec_degrees=61.200,
                magnitude=10.0,
                size_arcmin=15.0,
                description="Emission nebula in Cassiopeia"
            ),
            DSOTarget(
                name="Owl Cluster",
                catalog_id="NGC457",
                object_type="cluster",
                ra_hours=1.317,
                dec_degrees=58.283,
                magnitude=6.4,
                size_arcmin=13.0,
                description="Open cluster in Cassiopeia"
            ),
            DSOTarget(
                name="Double Cluster",
                catalog_id="NGC869",
                object_type="cluster",
                ra_hours=2.317,
                dec_degrees=57.133,
                magnitude=4.3,
                size_arcmin=30.0,
                description="Pair of open clusters in Perseus"
            ),
            DSOTarget(
                name="California Nebula",
                catalog_id="NGC1499",
                object_type="nebula",
                ra_hours=4.033,
                dec_degrees=36.367,
                magnitude=5.0,
                size_arcmin=145.0,
                description="Emission nebula in Perseus"
            ),
            DSOTarget(
                name="Horsehead Nebula",
                catalog_id="IC434",
                object_type="nebula",
                ra_hours=5.683,
                dec_degrees=-2.450,
                magnitude=6.8,
                size_arcmin=60.0,
                description="Dark nebula in Orion"
            ),
            DSOTarget(
                name="Monkey Head Nebula",
                catalog_id="NGC2174",
                object_type="nebula",
                ra_hours=6.158,
                dec_degrees=20.567,
                magnitude=6.8,
                size_arcmin=40.0,
                description="Emission nebula in Orion"
            ),
            DSOTarget(
                name="Cone Nebula",
                catalog_id="NGC2264",
                object_type="nebula",
                ra_hours=6.683,
                dec_degrees=9.900,
                magnitude=3.9,
                size_arcmin=20.0,
                description="Emission nebula in Monoceros"
            ),
        ]

        return catalog

    def get_all_targets(self) -> List[DSOTarget]:
        """Get all targets in catalog."""
        return self.targets

    def get_target_by_id(self, catalog_id: str) -> Optional[DSOTarget]:
        """Get a specific target by catalog ID."""
        for target in self.targets:
            if target.catalog_id.lower() == catalog_id.lower():
                return target
        return None

    def filter_targets(self, object_types: Optional[List[str]] = None) -> List[DSOTarget]:
        """
        Filter targets by object type.

        Args:
            object_types: List of object types to include (None = all)

        Returns:
            Filtered list of targets
        """
        if object_types is None or len(object_types) == 0:
            return self.targets

        return [
            target for target in self.targets
            if target.object_type in object_types
        ]
