# Catalog Integration Plan

## Current Catalogs (Implemented)
- ✅ **Messier (M)** - 110 objects
- ✅ **NGC (New General Catalogue)** - 7,840 objects
- ✅ **IC (Index Catalogue)** - 5,386 objects
- ✅ **Caldwell (C)** - 109 objects
- ✅ **Comets** - Dynamic via JPL Horizons API
- ✅ **Asteroids** - Dynamic via JPL Horizons API
- ✅ **Planets** - Dynamic calculations

## Phase 1: High-Value Additions for Seestar S50

### 1. Barnard Catalog (B) - Dark Nebulae
**Priority:** HIGH
**Count:** ~370 objects
**Rationale:**
- Excellent for wide-field astrophotography
- Provides context for bright nebulae
- Popular targets like B33 (Horsehead Nebula)
- Good for narrowband imaging with Seestar

**Data Source Options:**
- OpenNGC database (includes Barnard)
- SIMBAD astronomical database
- Manual curated list from Barnard's original catalog

**Example Objects:**
- B33 - Horsehead Nebula
- B72 - Snake Nebula
- B86 - Ink Spot Nebula
- B142-143 - Dark nebulae in Aquila

### 2. Sharpless Catalog (Sh2) - H-II Emission Nebulae
**Priority:** HIGH
**Count:** ~313 objects
**Rationale:**
- Perfect for H-alpha narrowband imaging
- Seestar S50 excels at emission nebulae
- Many stunning, large nebulae
- Popular astrophotography targets

**Data Source Options:**
- OpenNGC (may include some)
- Sharpless catalog database
- SIMBAD cross-reference

**Example Objects:**
- Sh2-101 - Tulip Nebula
- Sh2-132 - Lion Nebula
- Sh2-155 - Cave Nebula
- Sh2-171 - NGC 7822 region

### 3. Herschel 400 - Curated Deep Sky List
**Priority:** HIGH
**Count:** 400 objects (subset of NGC/IC)
**Rationale:**
- Curated "best of" list for visual/imaging
- Established observing program
- All bright enough for amateur telescopes
- Good progression of difficulty

**Data Source:**
- Already in NGC/IC database
- Just needs flagging/filtering
- Astronomical League official list

**Implementation:**
- Add `herschel_400` boolean flag to existing DSOCatalog table
- Filter method: `get_herschel_400_targets()`
- Minimal database changes required

## Phase 2: Cluster Catalogs (Medium Priority)

### 4. Collinder Catalog (Cr)
- ~471 open clusters
- Example: Cr 399 (Coathanger Asterism)

### 5. Melotte Catalog (Mel)
- ~245 open clusters
- Example: Mel 111 (Coma Star Cluster)

### 6. Stock Catalog (St)
- ~24 bright open clusters
- Lesser known but good targets

## Phase 3: Advanced Catalogs (Lower Priority)

### 7. Abell Catalog
- Planetary Nebulae subset (~80 brightest)
- Galaxy cluster subset (for wide field context)

### 8. Lynds Dark Nebula (LDN)
- ~1,802 dark nebulae
- For advanced astrophotography planning

### 9. Arp Catalog
- ~338 peculiar galaxies
- Interesting morphologies

## Other Catalogs to Consider

### Visual/Amateur Focus
- **Trumpler Catalog (Tr)** - ~300 open clusters
- **King Catalog** - ~100 open clusters
- **Hickson Compact Groups (HCG)** - ~100 galaxy groups
- **Palomar Globular Clusters (Pal)** - ~15 globular clusters
- **Terzan Catalog** - Globular clusters near galactic center

### Nebulae
- **Lynds Bright Nebula (LBN)** - ~1,125 bright nebulae
- **vdB Catalog (van den Bergh)** - ~158 reflection nebulae
- **Cederblad Catalog (Ced)** - Bright nebulae

### Galaxies (Professional/Advanced)
- **UGC (Uppsala General Catalogue)** - ~12,921 galaxies
- **PGC (Principal Galaxies Catalogue)** - ~73,197 galaxies
- **MCG (Morphological Catalogue of Galaxies)** - ~30,000 galaxies
- **ESO Catalog** - Southern hemisphere objects

### Special Interest
- **Planetary Nebulae (PNG/PK notation)** - Galactic coordinates system
- **Supernova Remnants (SNR)** - ~300 known
- **Wolf-Rayet Stars** - Interesting spectroscopic targets
- **Carbon Stars** - Deep red stars for imaging

### Double Stars
- **WDS (Washington Double Star Catalog)** - ~140,000 systems
- **Aladin Double Star Catalog**
- **Dunlop Catalog** - Southern double stars

### Historical/Observing Lists
- **Bennett Catalog** - 120 southern hemisphere objects
- **Dunlop Catalog** - 629 southern objects
- **SAC (Saguaro Astronomy Club) Database** - ~10,000 curated observations
- **RASC (Royal Astronomical Society of Canada) lists**
  - Finest NGC Objects
  - Deep Sky Challenge Objects

## Implementation Strategy

### Database Schema Updates
```sql
-- Add new catalog fields to DSOCatalog
ALTER TABLE dso_catalog ADD COLUMN barnard_number INTEGER;
ALTER TABLE dso_catalog ADD COLUMN sharpless_number INTEGER;
ALTER TABLE dso_catalog ADD COLUMN herschel_400 BOOLEAN DEFAULT FALSE;
ALTER TABLE dso_catalog ADD COLUMN collinder_number INTEGER;
ALTER TABLE dso_catalog ADD COLUMN melotte_number INTEGER;

-- Create indexes for new catalogs
CREATE INDEX idx_barnard ON dso_catalog(barnard_number) WHERE barnard_number IS NOT NULL;
CREATE INDEX idx_sharpless ON dso_catalog(sharpless_number) WHERE sharpless_number IS NOT NULL;
CREATE INDEX idx_herschel ON dso_catalog(herschel_400) WHERE herschel_400 = TRUE;
```

### Service Updates
```python
# Add to catalog_service.py
def get_barnard_targets(self, limit: int = 100, offset: int = 0) -> List[DSOTarget]:
    """Get Barnard dark nebulae."""

def get_sharpless_targets(self, limit: int = 100, offset: int = 0) -> List[DSOTarget]:
    """Get Sharpless emission nebulae."""

def get_herschel_400_targets(self, limit: int = 100, offset: int = 0) -> List[DSOTarget]:
    """Get Herschel 400 curated list."""
```

### API Endpoints
```python
# Add to routes.py
@router.get("/targets/barnard", response_model=List[DSOTarget])
async def get_barnard_catalog(...)

@router.get("/targets/sharpless", response_model=List[DSOTarget])
async def get_sharpless_catalog(...)

@router.get("/targets/herschel400", response_model=List[DSOTarget])
async def get_herschel_400(...)
```

## Data Acquisition Plan

### Herschel 400
- **Source:** Astronomical League official list
- **Format:** CSV/JSON mapping to NGC/IC numbers
- **Effort:** LOW - just flag existing objects

### Barnard Catalog
- **Source:** OpenNGC or SIMBAD query
- **Format:** CSV with RA/Dec, magnitude, size
- **Effort:** MEDIUM - need coordinate/magnitude data

### Sharpless Catalog
- **Source:** Original Sharpless catalog + modern coordinates
- **Format:** CSV with RA/Dec, magnitude, size, nebula type
- **Effort:** MEDIUM - some objects need updated coordinates

## Timeline Estimate

**Phase 1 Implementation:**
- Herschel 400: 1-2 days (database flag + filtering)
- Barnard: 3-5 days (data acquisition + import + testing)
- Sharpless: 3-5 days (data acquisition + import + testing)

**Total Phase 1:** 1-2 weeks

## Success Metrics

- All catalog objects queryable via API
- Proper cross-referencing (e.g., B33 = IC 434)
- Integration with existing filtering (magnitude, object type, constellation)
- Test coverage >90% for new catalog methods
- Documentation updated with catalog descriptions
- Example observing plans using new catalogs

## Notes

- Prioritize data quality over quantity
- Ensure proper attribution for catalog data sources
- Consider creating "curated lists" for Seestar S50 capabilities
- Add metadata about which objects work well for narrowband imaging
- Consider filter recommendations (L-eXtreme, dual narrowband, etc.)
