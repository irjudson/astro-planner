# Auto-Processing MVP Design

**Date:** 2025-12-07
**Status:** Approved

## Goal

Implement auto-processing that matches Seestar's output quality, taking stacked FITS files and producing JPG/PNG/TIFF outputs.

## Decisions

| Decision | Choice |
|----------|--------|
| Stretch algorithm | Arcsinh with auto-detected parameters |
| Parameter selection | Auto-detect based on image statistics |
| Output formats | JPG + PNG + TIFF (16-bit) |
| Output location | Same folder as input |
| UI trigger | File browser + batch + post-plan execution |
| Mosaic handling | Same as single frames |

## Research Findings

### Seestar's Algorithm (Reverse-Engineered)

Analysis of M81 (galaxy) and NGC 1499 (nebula) revealed:

- **Function:** Arcsinh stretch: `output = arcsinh(a * x) / arcsinh(a)`
- **Black point:** 0.5th percentile
- **White point:** 99.95th percentile
- **Stretch factor `a`:** Varies by content (5-20)
  - Galaxies (sparse bright detail): `a ≈ 20`
  - Nebulae (diffuse structure): `a ≈ 5`

### Benchmark Results

| Target | Type | Best Params | MSE |
|--------|------|-------------|-----|
| M81 | Galaxy | black=0.5%, white=99.95%, a=20 | 48.54 |
| NGC 1499 | Nebula | black=0.5%, white=99.95%, a=5 | 55.50 |

Visual comparison: indistinguishable from Seestar output.

## Core Algorithm

```python
def arcsinh_stretch(data, a):
    """Apply arcsinh stretch."""
    return np.arcsinh(a * data) / np.arcsinh(a)

def detect_stretch_params(data):
    """Auto-detect optimal stretch parameters."""
    # Fixed clip points (match Seestar)
    black_pct = 0.5
    white_pct = 99.95

    # Normalize
    bp = np.percentile(data, black_pct)
    wp = np.percentile(data, white_pct)
    normalized = np.clip((data - bp) / (wp - bp), 0, 1)

    # Detect stretch factor based on coefficient of variation
    # Higher CV (sparse bright pixels) = higher stretch
    cv = normalized.std() / (normalized.mean() + 1e-10)

    if cv > 0.5:
        a = 20  # Galaxy-like: sparse bright detail
    elif cv > 0.3:
        a = 10  # Mixed content
    else:
        a = 5   # Nebula-like: diffuse structure

    return {
        'black_point': bp,
        'white_point': wp,
        'stretch_factor': a
    }

def auto_process(fits_path):
    """Main entry point for auto-processing."""
    # Load FITS
    data = load_fits(fits_path)  # Returns (H, W, 3) float64

    # Detect parameters
    params = detect_stretch_params(data)

    # Normalize
    normalized = np.clip(
        (data - params['black_point']) /
        (params['white_point'] - params['black_point']),
        0, 1
    )

    # Stretch
    stretched = arcsinh_stretch(normalized, params['stretch_factor'])

    return stretched, params
```

## API Endpoints

### POST /api/process/auto

Process a single FITS file:

```json
// Request
{
  "file_path": "/fits/MyWorks/M81/Stacked_34_M81_*.fit",
  "formats": ["jpg", "png", "tiff"]
}

// Response
{
  "job_id": 123,
  "status": "queued"
}
```

### POST /api/process/batch

Process all stacked FITS in a folder:

```json
// Request
{
  "folder_path": "/fits/MyWorks",
  "recursive": true,
  "pattern": "Stacked_*.fit"
}

// Response
{
  "job_ids": [123, 124, 125],
  "files_found": 3
}
```

### Integration with Plan Execution

After telescope plan execution completes:
1. Telescope service triggers `POST /api/process/auto` for each target
2. Processing job linked to plan execution record
3. Frontend shows processing status with execution history

## Output Formats

| Format | Bit Depth | Compression | Use Case |
|--------|-----------|-------------|----------|
| JPG | 8-bit | 95% quality | Sharing |
| PNG | 8-bit | Lossless | Archive |
| TIFF | 16-bit | None | Further editing |

Files saved alongside input: `Stacked_*_processed.{jpg,png,tiff}`

## Implementation Files

### New Files

```
backend/app/services/auto_stretch_service.py
├── load_fits(path) -> np.ndarray
├── detect_stretch_params(data) -> dict
├── arcsinh_stretch(data, a) -> np.ndarray
├── auto_process(fits_path) -> tuple[np.ndarray, dict]
└── save_outputs(data, base_path, formats) -> list[str]
```

### Modified Files

```
backend/app/api/processing.py
├── POST /api/process/auto
└── POST /api/process/batch

backend/app/tasks/processing_tasks.py
└── auto_process_task(file_path, formats)

backend/app/services/telescope_service.py
└── trigger processing after plan execution

frontend/index.html
├── Process button in file browser
└── Job status display
```

## Testing

- Unit tests for stretch algorithm with synthetic data
- Integration tests with M81 and NGC1499 benchmark files
- Pass criteria: MSE < 100 compared to Seestar JPG

## Future Enhancements

### Phase 2: Improved Processing
- Additional stretch options (GHS, MTF)
- Color calibration / white balance
- Noise reduction
- Star size reduction

### Phase 3: Advanced Input
- Auto-detect folder structure
- Process from sub-frames (stacking)
- Watch folder for new files

### Phase 4: Siril Integration
- Use Siril CLI for calibration/stacking
- Template-based pipelines (per existing design doc)
