# Catalog Integration Design

**Date:** 2025-12-04
**Status:** Approved

## Goal

Expand the astronomical catalog coverage to include more DSO catalogs suitable for wide-field imaging.

## Decisions

| Decision | Choice |
|----------|--------|
| Priority | More DSOs → Double/Variable Stars → Solar System → Reference → Specialty |
| Telescope focus | Wide-field / small aperture (Seestar) |
| Data source | Hybrid - bundle core catalogs, VizieR/SIMBAD for on-demand |
| Initial catalogs | Sharpless, Barnard, Herschel 400 |

## Current Catalogs

Already integrated:
- **DSO**: NGC, IC, Messier, Caldwell
- **Solar System**: Comets, Asteroids, Planets, Satellites

## Phase 1: Priority DSO Catalogs

### Sharpless Catalog (Sh2)
- **Objects**: 313 HII emission nebulae
- **Size**: Perfect for wide-field (many are 1-3 degrees)
- **Data source**: Bundle static data
- **Fields**: Sh2 number, RA/Dec, size, associated objects, constellation

### Barnard Catalog
- **Objects**: 349 dark nebulae
- **Size**: Wide-field targets
- **Data source**: Bundle static data
- **Fields**: Barnard number, RA/Dec, size, opacity class, constellation

### Herschel 400
- **Objects**: 400 NGC objects (curated observing list)
- **Size**: Mixed, but all observable with modest equipment
- **Data source**: Flag existing NGC entries + bundle metadata
- **Fields**: H400 flag on DSOCatalog, observing notes

## Phase 2: Double/Variable Stars

### Washington Double Star Catalog (WDS)
- **Objects**: ~150,000 double/multiple stars
- **Use case**: Visual observing, calibration
- **Data source**: VizieR on-demand (too large to bundle)

### AAVSO Variable Star Index
- **Objects**: Variable stars with observing campaigns
- **Use case**: Citizen science, time-domain astronomy
- **Data source**: VizieR/AAVSO API on-demand

## Phase 3: Enhanced Solar System

- Trans-Neptunian Objects (TNOs)
- Detailed asteroid families
- Periodic meteor shower radiants

## Phase 4: Reference Catalogs

### For Plate Solving
- Gaia DR3 subset (bright stars for field matching)
- Tycho-2 catalog

### For Astrometry
- UCAC4/5 reference stars

## Phase 5: Specialty Catalogs

- Arp (338 peculiar galaxies)
- Hickson Compact Groups (100 galaxy groups)
- Palomar Globular Clusters

## Database Schema

Extend `DSOCatalog` model:

```python
class DSOCatalog(Base):
    # Existing fields...

    # New catalog cross-references
    sharpless_number = Column(Integer, nullable=True)  # Sh2-XXX
    barnard_number = Column(Integer, nullable=True)    # B-XXX
    herschel_400 = Column(Boolean, default=False)      # In H400 list
    arp_number = Column(Integer, nullable=True)        # Arp XXX

    # Enhanced metadata
    opacity_class = Column(Integer, nullable=True)     # For dark nebulae (1-6)
    nebula_type = Column(String(20), nullable=True)    # emission, reflection, dark, planetary
```

## VizieR Integration Service

```python
class VizierService:
    """Query VizieR/SIMBAD for on-demand catalog data."""

    def query_wds(self, ra: float, dec: float, radius: float) -> List[DoubleStar]:
        """Query Washington Double Star catalog."""
        ...

    def query_variable(self, name: str) -> Optional[VariableStar]:
        """Query AAVSO variable star data."""
        ...

    def query_by_name(self, name: str) -> Optional[CelestialObject]:
        """SIMBAD name resolution."""
        ...
```

## Data Files

Bundle in `data/catalogs/`:
- `sharpless.json` - 313 objects with coordinates and metadata
- `barnard.json` - 349 dark nebulae
- `herschel400.json` - 400 NGC numbers with H400-specific notes

## Implementation Order

1. Add schema fields for new catalogs
2. Create Alembic migration
3. Bundle Sharpless/Barnard/H400 data files
4. Create import script to populate database
5. Extend CatalogService to filter by new catalogs
6. Add VizierService for on-demand queries
7. Update frontend to display new catalog options
