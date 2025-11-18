"""Caldwell catalog of deep-sky objects for amateur astronomers."""

from typing import List, Optional
from pydantic import BaseModel
import math


class CaldwellObject(BaseModel):
    """A Caldwell catalog deep-sky object."""
    
    caldwell_id: str  # e.g., "C1"
    ngc_id: str  # NGC/IC identifier
    common_name: str  # Common name if any
    object_type: str  # Galaxy, Nebula, Open Cluster, etc.
    constellation: str
    ra_hours: float  # Right Ascension in decimal hours
    dec_degrees: float  # Declination in decimal degrees
    magnitude: float  # Visual magnitude
    size_arcmin: float  # Angular size in arcminutes


class CaldwellCatalog:
    """Service for accessing the Caldwell catalog."""
    
    def __init__(self):
        """Initialize with Caldwell catalog data."""
        self.objects = self._load_catalog()
    
    def _load_catalog(self) -> List[CaldwellObject]:
        """Load all 109 Caldwell objects."""
        # Caldwell catalog data (subset shown, full catalog would have all 109)
        data = [
            # Northern objects
            ("C1", "NGC 188", "", "Open Cluster", "Cepheus", 0.785, 85.255, 8.1, 14.0),
            ("C2", "NGC 40", "", "Planetary Nebula", "Cepheus", 0.217, 72.533, 10.7, 0.6),
            ("C3", "NGC 4236", "", "Galaxy", "Draco", 12.278, 69.467, 9.7, 21.0),
            ("C4", "NGC 7023", "Iris Nebula", "Nebula", "Cepheus", 21.017, 68.167, 6.8, 18.0),
            ("C5", "IC 342", "", "Galaxy", "Camelopardalis", 3.783, 68.100, 9.2, 21.0),
            ("C6", "NGC 6543", "Cat's Eye Nebula", "Planetary Nebula", "Draco", 17.967, 66.633, 8.1, 0.3),
            ("C7", "NGC 2403", "", "Galaxy", "Camelopardalis", 7.617, 65.600, 8.9, 21.9),
            ("C8", "NGC 559", "", "Open Cluster", "Cassiopeia", 1.483, 63.300, 9.5, 4.0),
            ("C9", "Sh2-155", "Cave Nebula", "Nebula", "Cepheus", 22.933, 62.617, 7.7, 50.0),
            ("C10", "NGC 663", "", "Open Cluster", "Cassiopeia", 1.767, 61.250, 7.1, 16.0),
            ("C11", "NGC 7635", "Bubble Nebula", "Nebula", "Cassiopeia", 23.333, 61.200, 11.0, 15.0),
            ("C12", "NGC 6946", "Fireworks Galaxy", "Galaxy", "Cepheus", 20.583, 60.150, 9.0, 11.5),
            ("C13", "NGC 457", "Owl Cluster", "Open Cluster", "Cassiopeia", 1.317, 58.300, 6.4, 13.0),
            ("C14", "NGC 869/884", "Double Cluster", "Open Cluster", "Perseus", 2.333, 57.133, 4.3, 30.0),
            ("C15", "NGC 6826", "Blinking Planetary", "Planetary Nebula", "Cygnus", 19.750, 50.533, 8.8, 0.5),
            ("C16", "NGC 7243", "", "Open Cluster", "Lacerta", 22.250, 49.900, 6.4, 21.0),
            ("C17", "NGC 147", "", "Galaxy", "Cassiopeia", 0.550, 48.517, 10.4, 13.0),
            ("C18", "NGC 185", "", "Galaxy", "Cassiopeia", 0.650, 48.333, 9.3, 12.0),
            ("C19", "IC 5146", "Cocoon Nebula", "Nebula", "Cygnus", 21.883, 47.267, 10.0, 12.0),
            ("C20", "NGC 7000", "North America Nebula", "Nebula", "Cygnus", 20.983, 44.333, 4.0, 120.0),
            
            # More northern objects
            ("C21", "NGC 4449", "", "Galaxy", "Canes Venatici", 12.467, 44.100, 9.6, 5.1),
            ("C22", "NGC 7662", "Blue Snowball", "Planetary Nebula", "Andromeda", 23.433, 42.550, 8.3, 0.3),
            ("C23", "NGC 891", "", "Galaxy", "Andromeda", 2.367, 42.350, 10.0, 13.5),
            ("C24", "NGC 1275", "Perseus A", "Galaxy", "Perseus", 3.317, 41.517, 11.6, 2.6),
            ("C25", "NGC 2419", "Intergalactic Wanderer", "Globular Cluster", "Lynx", 7.633, 38.883, 10.4, 4.1),
            ("C26", "NGC 4244", "", "Galaxy", "Canes Venatici", 12.300, 37.817, 10.6, 16.0),
            ("C27", "NGC 6888", "Crescent Nebula", "Nebula", "Cygnus", 20.200, 38.350, 7.4, 20.0),
            ("C28", "NGC 752", "", "Open Cluster", "Andromeda", 1.950, 37.683, 5.7, 50.0),
            ("C29", "NGC 5005", "", "Galaxy", "Canes Venatici", 13.183, 37.050, 10.8, 5.4),
            ("C30", "NGC 7331", "", "Galaxy", "Pegasus", 22.617, 34.417, 9.5, 10.7),
            
            # More objects continuing to southern hemisphere
            ("C31", "IC 405", "Flaming Star Nebula", "Nebula", "Auriga", 5.267, 34.267, 6.0, 30.0),
            ("C32", "NGC 4631", "Whale Galaxy", "Galaxy", "Canes Venatici", 12.700, 32.533, 9.3, 15.2),
            ("C33", "NGC 6992/5", "Eastern Veil Nebula", "Nebula", "Cygnus", 20.933, 31.733, 7.0, 60.0),
            ("C34", "NGC 6960", "Western Veil Nebula", "Nebula", "Cygnus", 20.767, 30.717, 7.0, 70.0),
            ("C35", "NGC 4889", "", "Galaxy", "Coma Berenices", 13.000, 27.983, 11.4, 2.9),
            ("C36", "NGC 4559", "", "Galaxy", "Coma Berenices", 12.600, 27.967, 10.0, 10.5),
            ("C37", "NGC 6885", "", "Open Cluster", "Vulpecula", 20.200, 26.483, 5.7, 7.0),
            ("C38", "NGC 4565", "Needle Galaxy", "Galaxy", "Coma Berenices", 12.600, 25.983, 9.6, 15.9),
            ("C39", "NGC 2392", "Eskimo Nebula", "Planetary Nebula", "Gemini", 7.483, 20.917, 9.2, 0.7),
            ("C40", "NGC 3626", "", "Galaxy", "Leo", 11.333, 18.350, 10.9, 2.7),
            
            # Equatorial and southern objects
            ("C41", "Hyades", "", "Open Cluster", "Taurus", 4.450, 15.867, 0.5, 330.0),
            ("C42", "NGC 7006", "", "Globular Cluster", "Delphinus", 21.017, 16.183, 10.6, 2.8),
            ("C43", "NGC 7814", "", "Galaxy", "Pegasus", 0.050, 16.150, 10.5, 6.0),
            ("C44", "NGC 7479", "", "Galaxy", "Pegasus", 23.083, 12.317, 11.0, 4.0),
            ("C45", "NGC 5248", "", "Galaxy", "Boötes", 13.617, 8.883, 10.3, 6.2),
            ("C46", "NGC 2261", "Hubble's Variable Nebula", "Nebula", "Monoceros", 6.650, 8.733, 10.0, 2.0),
            ("C47", "NGC 6934", "", "Globular Cluster", "Delphinus", 20.583, 7.400, 8.9, 5.9),
            ("C48", "NGC 2775", "", "Galaxy", "Cancer", 9.183, 7.033, 10.3, 4.3),
            ("C49", "NGC 2237-9", "Rosette Nebula", "Nebula", "Monoceros", 6.533, 5.033, 6.0, 80.0),
            ("C50", "NGC 2244", "", "Open Cluster", "Monoceros", 6.533, 4.900, 4.8, 24.0),
            
            # Southern hemisphere objects
            ("C51", "IC 1613", "", "Galaxy", "Cetus", 1.083, 2.133, 9.3, 16.0),
            ("C52", "NGC 4697", "", "Galaxy", "Virgo", 12.800, -5.800, 9.3, 6.0),
            ("C53", "NGC 3115", "Spindle Galaxy", "Galaxy", "Sextans", 10.083, -7.717, 9.1, 7.2),
            ("C54", "NGC 2506", "", "Open Cluster", "Monoceros", 8.000, -10.783, 7.6, 7.0),
            ("C55", "NGC 7009", "Saturn Nebula", "Planetary Nebula", "Aquarius", 21.067, -11.367, 8.0, 0.4),
            ("C56", "NGC 246", "", "Planetary Nebula", "Cetus", 0.783, -11.883, 10.9, 3.8),
            ("C57", "NGC 6822", "Barnard's Galaxy", "Galaxy", "Sagittarius", 19.750, -14.800, 9.3, 15.5),
            ("C58", "NGC 2360", "", "Open Cluster", "Canis Major", 7.300, -15.633, 7.2, 13.0),
            ("C59", "NGC 3242", "Ghost of Jupiter", "Planetary Nebula", "Hydra", 10.400, -18.633, 7.8, 0.3),
            ("C60", "NGC 4038/9", "Antennae Galaxies", "Galaxy", "Corvus", 12.033, -18.867, 10.9, 5.2),
            
            ("C61", "NGC 4235", "", "Galaxy", "Corvus", 12.283, -19.950, 11.2, 4.3),
            ("C62", "NGC 247", "", "Galaxy", "Cetus", 0.783, -20.767, 9.1, 21.0),
            ("C63", "NGC 7293", "Helix Nebula", "Planetary Nebula", "Aquarius", 22.483, -20.817, 7.6, 13.0),
            ("C64", "NGC 2362", "", "Open Cluster", "Canis Major", 7.300, -24.950, 4.1, 8.0),
            ("C65", "NGC 253", "Sculptor Galaxy", "Galaxy", "Sculptor", 0.783, -25.283, 7.6, 27.5),
            ("C66", "NGC 5694", "", "Globular Cluster", "Hydra", 14.650, -26.533, 10.2, 3.6),
            ("C67", "NGC 1097", "", "Galaxy", "Fornax", 2.767, -30.283, 9.3, 9.5),
            ("C68", "NGC 6729", "", "Nebula", "Corona Australis", 19.033, -36.950, 9.7, 1.0),
            ("C69", "NGC 6302", "Bug Nebula", "Planetary Nebula", "Scorpius", 17.233, -37.100, 9.6, 0.8),
            ("C70", "NGC 300", "", "Galaxy", "Sculptor", 0.917, -37.683, 8.7, 21.9),
            
            ("C71", "NGC 2477", "", "Open Cluster", "Puppis", 7.867, -38.533, 5.8, 27.0),
            ("C72", "NGC 55", "", "Galaxy", "Sculptor", 0.250, -39.183, 8.2, 32.0),
            ("C73", "NGC 1851", "", "Globular Cluster", "Columba", 5.233, -40.050, 7.3, 11.0),
            ("C74", "NGC 3132", "Eight Burst Nebula", "Planetary Nebula", "Vela", 10.117, -40.433, 8.2, 0.8),
            ("C75", "NGC 6124", "", "Open Cluster", "Scorpius", 16.433, -40.667, 5.8, 29.0),
            ("C76", "NGC 6231", "", "Open Cluster", "Scorpius", 16.900, -41.817, 2.6, 15.0),
            ("C77", "NGC 5128", "Centaurus A", "Galaxy", "Centaurus", 13.417, -43.017, 7.0, 25.7),
            ("C78", "NGC 6541", "", "Globular Cluster", "Corona Australis", 18.133, -43.717, 6.6, 13.1),
            ("C79", "NGC 3201", "", "Globular Cluster", "Vela", 10.283, -46.417, 6.7, 18.2),
            ("C80", "NGC 5139", "Omega Centauri", "Globular Cluster", "Centaurus", 13.450, -47.483, 3.9, 36.3),
            
            ("C81", "NGC 6352", "", "Globular Cluster", "Ara", 17.417, -48.417, 8.1, 7.1),
            ("C82", "NGC 6193", "", "Open Cluster", "Ara", 16.683, -48.767, 5.2, 15.0),
            ("C83", "NGC 4945", "", "Galaxy", "Centaurus", 13.083, -49.467, 9.5, 20.0),
            ("C84", "NGC 5286", "", "Globular Cluster", "Centaurus", 13.767, -51.367, 7.6, 9.1),
            ("C85", "IC 2391", "", "Open Cluster", "Vela", 8.683, -53.033, 2.5, 50.0),
            ("C86", "NGC 6397", "", "Globular Cluster", "Ara", 17.667, -53.667, 5.7, 25.7),
            ("C87", "NGC 1261", "", "Globular Cluster", "Horologium", 3.200, -55.217, 8.4, 6.9),
            ("C88", "NGC 5823", "", "Open Cluster", "Circinus", 15.083, -55.600, 7.9, 10.0),
            ("C89", "NGC 6087", "", "Open Cluster", "Norma", 16.317, -57.933, 5.4, 12.0),
            ("C90", "NGC 2867", "", "Planetary Nebula", "Carina", 9.350, -58.317, 9.7, 0.2),
            
            ("C91", "NGC 3532", "", "Open Cluster", "Carina", 11.100, -58.667, 3.0, 55.0),
            ("C92", "NGC 3372", "Eta Carinae Nebula", "Nebula", "Carina", 10.750, -59.867, 3.0, 120.0),
            ("C93", "NGC 6752", "", "Globular Cluster", "Pavo", 19.183, -59.983, 5.4, 20.4),
            ("C94", "NGC 4755", "Jewel Box", "Open Cluster", "Crux", 12.883, -60.350, 4.2, 10.0),
            ("C95", "NGC 6025", "", "Open Cluster", "Triangulum Australe", 16.050, -60.450, 5.1, 12.0),
            ("C96", "NGC 2516", "", "Open Cluster", "Carina", 7.967, -60.867, 3.8, 30.0),
            ("C97", "NGC 3766", "", "Open Cluster", "Centaurus", 11.600, -61.600, 5.3, 12.0),
            ("C98", "NGC 4609", "", "Open Cluster", "Crux", 12.700, -62.967, 6.9, 5.0),
            ("C99", "Coalsack", "", "Dark Nebula", "Crux", 12.883, -63.000, 1.0, 400.0),
            ("C100", "IC 2944", "", "Nebula", "Centaurus", 11.600, -63.033, 4.5, 15.0),
            
            ("C101", "NGC 6744", "", "Galaxy", "Pavo", 19.150, -63.867, 9.0, 20.0),
            ("C102", "IC 2602", "Southern Pleiades", "Open Cluster", "Carina", 10.717, -64.400, 1.9, 50.0),
            ("C103", "NGC 2070", "Tarantula Nebula", "Nebula", "Dorado", 5.650, -69.100, 5.0, 40.0),
            ("C104", "NGC 362", "", "Globular Cluster", "Tucana", 1.050, -70.850, 6.6, 12.9),
            ("C105", "NGC 4833", "", "Globular Cluster", "Musca", 13.000, -70.883, 7.4, 13.5),
            ("C106", "NGC 104", "47 Tucanae", "Globular Cluster", "Tucana", 0.400, -72.083, 4.0, 30.9),
            ("C107", "NGC 6101", "", "Globular Cluster", "Apus", 16.433, -72.200, 9.3, 10.7),
            ("C108", "NGC 4372", "", "Globular Cluster", "Musca", 12.417, -72.667, 7.8, 18.6),
            ("C109", "NGC 3195", "", "Planetary Nebula", "Chamaeleon", 10.150, -80.850, 11.6, 0.6),
        ]
        
        return [
            CaldwellObject(
                caldwell_id=cid,
                ngc_id=ngc,
                common_name=name,
                object_type=obj_type,
                constellation=const,
                ra_hours=ra,
                dec_degrees=dec,
                magnitude=mag,
                size_arcmin=size
            )
            for cid, ngc, name, obj_type, const, ra, dec, mag, size in data
        ]
    
    def get_by_id(self, caldwell_id: str) -> Optional[CaldwellObject]:
        """Get object by Caldwell ID (e.g., 'C1')."""
        for obj in self.objects:
            if obj.caldwell_id == caldwell_id:
                return obj
        return None
    
    def get_by_ngc_id(self, ngc_id: str) -> Optional[CaldwellObject]:
        """Get object by NGC/IC ID."""
        for obj in self.objects:
            if ngc_id in obj.ngc_id:
                return obj
        return None
    
    def get_by_common_name(self, name: str) -> Optional[CaldwellObject]:
        """Get object by common name."""
        name_lower = name.lower()
        for obj in self.objects:
            if obj.common_name.lower() == name_lower:
                return obj
        return None
    
    def search_by_constellation(self, constellation: str) -> List[CaldwellObject]:
        """Get all objects in a constellation."""
        return [obj for obj in self.objects if obj.constellation == constellation]
    
    def search_by_type(self, object_type: str) -> List[CaldwellObject]:
        """Get all objects of a specific type."""
        return [obj for obj in self.objects if obj.object_type == object_type]
    
    def search_by_magnitude(
        self,
        min_magnitude: Optional[float] = None,
        max_magnitude: Optional[float] = None
    ) -> List[CaldwellObject]:
        """Get objects within magnitude range."""
        results = self.objects
        if min_magnitude is not None:
            results = [obj for obj in results if obj.magnitude >= min_magnitude]
        if max_magnitude is not None:
            results = [obj for obj in results if obj.magnitude <= max_magnitude]
        return results
    
    def get_observable(
        self,
        latitude: float,
        min_altitude: float = 0.0
    ) -> List[CaldwellObject]:
        """
        Get objects observable from a given latitude.
        
        Simple calculation: objects with dec > (latitude - 90 + min_altitude)
        are potentially observable.
        """
        min_dec = latitude - 90.0 + min_altitude
        return [obj for obj in self.objects if obj.dec_degrees >= min_dec]
