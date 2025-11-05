# Post-Capture Processing Design Document

**Feature**: Process Tab - Complete the astro-imaging workflow
**Status**: Design Phase
**Priority**: Medium-High
**Target**: Q2-Q3 2026
**Cost**: $0 (all free/open-source tools)

---

## Table of Contents

1. [Overview](#overview)
2. [User Workflow](#user-workflow)
3. [Seestar S50 Output Analysis](#seestar-s50-output-analysis)
4. [Technical Architecture](#technical-architecture)
5. [Processing Pipeline](#processing-pipeline)
6. [UI/UX Design](#uiux-design)
7. [Free Tools & Libraries](#free-tools--libraries)
8. [Implementation Phases](#implementation-phases)
9. [Storage & Performance](#storage--performance)
10. [Security Considerations](#security-considerations)

---

## Overview

### Vision
Complete the observing workflow with integrated post-processing:
```
Plan → Browse → Observe → Process
```

### Goals
1. **Hybrid Workflow**: Quick presets for common tasks + advanced customization
2. **Free Stack**: Leverage open-source tools (Siril, Astropy, OpenCV)
3. **Session-Aware**: Link processing to observation sessions/plans
4. **Educational**: Teach processing concepts with visual feedback
5. **Export-Friendly**: Prepare files for external tools (PixInsight, Photoshop)

### Non-Goals (Phase 1)
- ❌ Replace professional tools (PixInsight, Photoshop)
- ❌ Advanced operations (deconvolution, HDR, narrowband)
- ❌ Real-time processing during observation
- ❌ Planetary video processing (focus on DSO stacking)

---

## User Workflow

### Scenario 1: Quick Processing (Beginner)
```
1. User uploads session files (stacked FITS from Seestar)
2. System detects session metadata (target, exposure, filter)
3. User clicks "Quick Process" → Auto-applies preset
4. System runs: Calibration → Stretch → Color Balance
5. User previews result, downloads JPEG/TIFF
6. Optional: "Export for PixInsight" (16-bit TIFF)
```

### Scenario 2: Custom Workflow (Advanced)
```
1. User uploads session files
2. User builds custom pipeline:
   - Add "Gradient Removal" step
   - Add "Star Reduction" step
   - Add "Histogram Stretch" with custom black point
3. System shows preview at each step
4. User adjusts parameters, re-runs steps
5. User saves workflow as "recipe" for future sessions
6. Downloads final image + processing log
```

### Scenario 3: Session Analysis
```
1. User uploads session files
2. System analyzes:
   - FWHM/seeing quality per frame
   - Star counts and distribution
   - Background noise levels
   - Success rate (good frames vs rejected)
3. User sees session report with recommendations
4. User decides to re-process with different settings
```

---

## Seestar S50 Output Analysis

### File Formats Produced

**Primary Output** (need confirmation from Seestar docs):
- **Stacked FITS**: `M31_stacked.fit` - Main output after live stacking
- **Individual Lights**: `M31_light_001.fit`, `M31_light_002.fit`, etc.
- **Calibration Frames**:
  - Dark frames: `dark_10s_001.fit`
  - Flat frames: `flat_001.fit`
  - Bias frames: `bias_001.fit`
- **Session Log**: `M31_session.json` - Metadata (start time, coordinates, settings)
- **Preview JPEG**: `M31_preview.jpg` - Quick preview for mobile

**Metadata in FITS Headers**:
```
OBJECT = 'M31'
EXPTIME = 10.0
FILTER = 'L'
INSTRUME = 'Seestar S50'
RA = 0.712
DEC = 41.269
DATE-OBS = '2025-11-05T02:30:00'
IMAGETYP = 'Light Frame'
```

### Typical Session Structure
```
session_2025-11-05_M31/
├── M31_stacked.fit           # Main stacked image (16-bit)
├── M31_preview.jpg           # Quick preview (8-bit JPEG)
├── lights/
│   ├── M31_light_001.fit     # Individual 10s exposures
│   ├── M31_light_002.fit
│   └── ... (100 frames)
├── calibration/
│   ├── darks/
│   │   └── dark_10s_001.fit
│   ├── flats/
│   │   └── flat_001.fit
│   └── bias/
│       └── bias_001.fit
└── session_log.json          # Metadata
```

---

## Technical Architecture

### Backend Components

```python
# New services to add

backend/app/services/
├── processing_service.py      # Main processing orchestrator
├── fits_handler.py            # FITS file I/O, header parsing
├── calibration_service.py     # Dark/flat/bias application
├── stacking_service.py        # Stack individual frames (if needed)
├── stretch_service.py         # Histogram stretching
├── gradient_service.py        # Gradient/vignetting removal
├── pipeline_builder.py        # Custom workflow builder
└── session_analyzer.py        # Quality metrics, FWHM, SNR

backend/app/models/
├── processing_models.py       # Job, Pipeline, Step models
└── session_models.py          # Session, Frame, Quality models
```

### Database Schema

```sql
-- Processing sessions
CREATE TABLE processing_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,  -- Future: multi-user support
    session_name VARCHAR(100),
    observation_plan_id INTEGER,  -- Link to original plan
    upload_timestamp DATETIME,
    total_files INTEGER,
    total_size_bytes BIGINT,
    status VARCHAR(20),  -- 'uploading', 'ready', 'processing', 'complete', 'error'
    metadata JSON,  -- Session log, target info
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Individual files in session
CREATE TABLE processing_files (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES processing_sessions(id),
    filename VARCHAR(255),
    file_type VARCHAR(20),  -- 'light', 'dark', 'flat', 'bias', 'stacked'
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    exposure_seconds FLOAT,
    filter_name VARCHAR(10),
    temperature_celsius FLOAT,
    quality_score FLOAT,  -- FWHM, star count, etc.
    metadata JSON,  -- FITS headers
    uploaded_at DATETIME
);

-- Processing jobs
CREATE TABLE processing_jobs (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES processing_sessions(id),
    pipeline_id INTEGER REFERENCES processing_pipelines(id),
    status VARCHAR(20),  -- 'queued', 'running', 'complete', 'failed'
    progress_percent FLOAT,
    current_step VARCHAR(50),
    started_at DATETIME,
    completed_at DATETIME,
    output_files JSON,  -- List of generated files
    error_message TEXT,
    processing_log TEXT
);

-- Processing pipelines (saved workflows)
CREATE TABLE processing_pipelines (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    name VARCHAR(100),
    description TEXT,
    pipeline_steps JSON,  -- Array of step configurations
    is_preset BOOLEAN DEFAULT FALSE,
    created_at DATETIME,
    updated_at DATETIME
);

-- Processing steps (individual operations)
CREATE TABLE processing_steps (
    id INTEGER PRIMARY KEY,
    pipeline_id INTEGER REFERENCES processing_pipelines(id),
    step_order INTEGER,
    step_type VARCHAR(50),  -- 'calibrate', 'stack', 'stretch', 'gradient', etc.
    parameters JSON,  -- Step-specific params
    enabled BOOLEAN DEFAULT TRUE
);
```

### Processing Queue Architecture

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  FastAPI     │────→│  Redis Queue  │────→│   Celery     │
│  /process    │     │   (Job Queue) │     │   Workers    │
└──────────────┘     └───────────────┘     └──────────────┘
                                                    │
                                                    ▼
                                           ┌─────────────────┐
                                           │  Processing     │
                                           │  Pipeline       │
                                           │  (Siril/Astropy)│
                                           └─────────────────┘
                                                    │
                                                    ▼
                                           ┌─────────────────┐
                                           │  Output Files   │
                                           │  (FITS/TIFF/PNG)│
                                           └─────────────────┘
```

**Why async processing?**
- FITS stacking can take 5-30 minutes
- User shouldn't wait with browser open
- WebSocket updates for progress
- Background workers scale independently

---

## Processing Pipeline

### Quick Presets (Phase 1)

#### 1. Quick DSO Process (Beginner)
```python
pipeline_quick_dso = [
    {
        "step": "calibrate",
        "params": {
            "apply_darks": True,
            "apply_flats": True,
            "apply_bias": True
        }
    },
    {
        "step": "histogram_stretch",
        "params": {
            "algorithm": "auto",  # Auto-detect black/white points
            "midtones": 0.5
        }
    },
    {
        "step": "color_balance",
        "params": {
            "algorithm": "auto"  # Auto white balance
        }
    },
    {
        "step": "export",
        "params": {
            "format": "jpeg",
            "quality": 95,
            "bit_depth": 8
        }
    }
]
```

#### 2. Export for External Tool
```python
pipeline_export = [
    {
        "step": "calibrate",
        "params": {
            "apply_darks": True,
            "apply_flats": True,
            "apply_bias": True
        }
    },
    {
        "step": "export",
        "params": {
            "format": "tiff",
            "bit_depth": 16,  # Preserve dynamic range
            "compression": "none"
        }
    }
]
```

### Advanced Steps (Phase 2)

#### 3. Gradient Removal
```python
{
    "step": "remove_gradient",
    "params": {
        "algorithm": "dbf",  # Dynamic Background Extraction
        "smoothness": 0.5,
        "samples": 50
    }
}
```

#### 4. Star Reduction
```python
{
    "step": "star_reduction",
    "params": {
        "strength": 0.5,  # 0-1 scale
        "preserve_brightness": True,
        "halo_reduction": True
    }
}
```

#### 5. Noise Reduction
```python
{
    "step": "denoise",
    "params": {
        "algorithm": "non_local_means",
        "strength": 5.0,
        "luminance_only": True
    }
}
```

### Processing Pipeline Example Code

```python
# backend/app/services/processing_service.py

from astropy.io import fits
import numpy as np
import subprocess
import tempfile
from pathlib import Path

class ProcessingService:
    """Orchestrates processing pipeline execution."""

    def __init__(self):
        self.siril_path = "/usr/bin/siril-cli"  # Siril command-line
        self.temp_dir = Path("/tmp/astro_processing")

    async def execute_pipeline(
        self,
        session_id: int,
        pipeline_id: int,
        job_id: int
    ) -> dict:
        """Execute a processing pipeline on a session."""

        # Load session files
        session = await self.get_session(session_id)
        pipeline = await self.get_pipeline(pipeline_id)

        # Create working directory
        work_dir = self.temp_dir / f"job_{job_id}"
        work_dir.mkdir(parents=True, exist_ok=True)

        # Execute each step in pipeline
        current_file = session.stacked_file_path

        for step in pipeline.steps:
            if step.step_type == "calibrate":
                current_file = await self.apply_calibration(
                    current_file,
                    session,
                    step.parameters,
                    work_dir
                )

            elif step.step_type == "histogram_stretch":
                current_file = await self.stretch_histogram(
                    current_file,
                    step.parameters,
                    work_dir
                )

            elif step.step_type == "remove_gradient":
                current_file = await self.remove_gradient(
                    current_file,
                    step.parameters,
                    work_dir
                )

            elif step.step_type == "export":
                output_file = await self.export_image(
                    current_file,
                    step.parameters,
                    work_dir
                )

            # Update job progress
            await self.update_job_progress(job_id, step.step_order)

        return {
            "status": "complete",
            "output_file": output_file,
            "processing_log": self.get_log(work_dir)
        }

    async def apply_calibration(
        self,
        light_file: Path,
        session,
        params: dict,
        work_dir: Path
    ) -> Path:
        """Apply dark/flat/bias calibration using Siril."""

        # Create Siril script
        script = work_dir / "calibrate.ssf"
        script.write_text(f"""
requires 1.2.0
cd {work_dir}
convert light -out={work_dir}
preprocess light -dark={session.master_dark} -flat={session.master_flat} -bias={session.master_bias} -cc=dark -cc=bias -cfa -equalize_cfa
""")

        # Run Siril
        result = subprocess.run(
            [self.siril_path, "-s", str(script)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise ProcessingError(f"Calibration failed: {result.stderr}")

        return work_dir / "pp_light.fit"

    async def stretch_histogram(
        self,
        input_file: Path,
        params: dict,
        work_dir: Path
    ) -> Path:
        """Stretch histogram using custom algorithm."""

        # Load FITS
        with fits.open(input_file) as hdul:
            data = hdul[0].data.astype(np.float32)
            header = hdul[0].header

        # Apply stretch
        if params["algorithm"] == "auto":
            # Auto-detect black/white points
            black_point = np.percentile(data, 0.1)
            white_point = np.percentile(data, 99.9)
        else:
            black_point = params.get("black_point", 0)
            white_point = params.get("white_point", 65535)

        # Linear stretch
        stretched = np.clip((data - black_point) / (white_point - black_point), 0, 1)

        # Apply midtones transfer function
        midtones = params.get("midtones", 0.5)
        stretched = self.mtf(stretched, midtones)

        # Save stretched FITS
        output_file = work_dir / "stretched.fit"
        fits.writeto(output_file, stretched, header, overwrite=True)

        return output_file

    def mtf(self, data: np.ndarray, midtones: float) -> np.ndarray:
        """Midtones Transfer Function (non-linear stretch)."""
        return (midtones - 1) * data / ((2 * midtones - 1) * data - midtones)
```

---

## UI/UX Design

### Process Tab Layout

```
┌────────────────────────────────────────────────────────────────┐
│ 🎨 Process                                                     │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐    ┌──────────────────────────────┐  │
│  │  Upload Session     │    │  Recent Sessions             │  │
│  │                     │    │  ┌────────────────────────┐  │  │
│  │  Drag & drop FITS   │    │  │ M31 - Nov 5, 2025     │  │  │
│  │  files here         │    │  │ 150 frames, 4.2GB     │  │  │
│  │                     │    │  │ [Quick Process] [View]│  │  │
│  │  Or [Browse Files]  │    │  └────────────────────────┘  │  │
│  │                     │    │  ┌────────────────────────┐  │  │
│  │  Supports:          │    │  │ M42 - Nov 4, 2025     │  │  │
│  │  • FITS (.fit)      │    │  │ 200 frames, 5.8GB     │  │  │
│  │  • Seestar sessions │    │  │ [Quick Process] [View]│  │  │
│  │  • ZIP archives     │    │  └────────────────────────┘  │  │
│  └─────────────────────┘    └──────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Session View (After Upload)

```
┌────────────────────────────────────────────────────────────────┐
│ ← Back to Sessions    Session: M31 - Nov 5, 2025              │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Session Info                                             │  │
│  │ Target: M31 (Andromeda Galaxy)                           │  │
│  │ Frames: 150 lights + 20 darks + 10 flats                 │  │
│  │ Exposure: 10s per frame                                  │  │
│  │ Total Integration: 25 minutes                            │  │
│  │ Stacked: Yes (M31_stacked.fit)                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────┐    ┌──────────────────────────────┐  │
│  │  Quick Presets      │    │  Preview                     │  │
│  │                     │    │  ┌────────────────────────┐  │  │
│  │  [Quick DSO]        │    │  │                        │  │  │
│  │  [Deep Stretch]     │    │  │   [Image Preview]      │  │  │
│  │  [Export for PI]    │    │  │                        │  │  │
│  │  [Custom Pipeline]  │    │  │                        │  │  │
│  │                     │    │  └────────────────────────┘  │  │
│  │  Or build custom:   │    │  Original FITS              │  │
│  │  [+ Add Step ▼]     │    │                              │  │
│  │                     │    │  [Download] [Share]          │  │
│  └─────────────────────┘    └──────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Session Analysis                                         │  │
│  │ ─────────────────────────────────────────────────────── │  │
│  │ FWHM (Seeing): 2.1" (Good)                  ⭐⭐⭐⭐☆   │  │
│  │ Star Count: 12,458                                       │  │
│  │ Background Noise: Low                                    │  │
│  │ Rejected Frames: 5 (3.3%)                                │  │
│  │ [View Detailed Report]                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Custom Pipeline Builder

```
┌────────────────────────────────────────────────────────────────┐
│ ← Back to Session    Custom Pipeline Builder                  │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Pipeline Steps                         Preview                │
│  ┌─────────────────────────────┐    ┌──────────────────────┐  │
│  │                             │    │                      │  │
│  │  1. ✓ Calibration           │    │   [Before/After     │  │
│  │     [⚙️ Settings] [🗑️]      │    │    Slider Preview]  │  │
│  │                             │    │                      │  │
│  │  2. ⏯️ Histogram Stretch     │    │                      │  │
│  │     Black: ▬▬▬●────── 512   │    │  Step 2: Stretch    │  │
│  │     White: ─────●▬▬▬ 45000  │    │                      │  │
│  │     Mid:   ───●───── 0.5    │    │                      │  │
│  │     [⚙️ Settings] [🗑️]      │    │                      │  │
│  │                             │    │                      │  │
│  │  3. ⏸️ Gradient Removal      │    │  [Apply Changes]    │  │
│  │     [⚙️ Settings] [🗑️]      │    │                      │  │
│  │                             │    └──────────────────────┘  │
│  │  [+ Add Step ▼]             │                              │
│  │     Calibration             │    Processing Time: ~8 min   │
│  │     Histogram Stretch       │                              │
│  │     Gradient Removal        │    [▶️ Run Pipeline]         │
│  │     Star Reduction          │    [💾 Save as Preset]       │
│  │     Color Balance           │                              │
│  │     Denoise                 │                              │
│  │     Export                  │                              │
│  └─────────────────────────────┘                              │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Processing in Progress

```
┌────────────────────────────────────────────────────────────────┐
│ Processing: M31 - Quick DSO Pipeline                           │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Progress                                                │  │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░  60%                    │  │
│  │                                                          │  │
│  │  Current Step: Histogram Stretch (Step 2 of 4)          │  │
│  │  Elapsed: 4m 32s                                         │  │
│  │  Estimated Remaining: 3m 08s                             │  │
│  │                                                          │  │
│  │  ✓ Step 1: Calibration (Complete)                       │  │
│  │  ⏳ Step 2: Histogram Stretch (Running...)               │  │
│  │  ⏸️ Step 3: Color Balance (Pending)                      │  │
│  │  ⏸️ Step 4: Export (Pending)                             │  │
│  │                                                          │  │
│  │  [Cancel Processing]                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Processing Log:                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ [12:34:56] Starting calibration...                       │  │
│  │ [12:35:12] Applied 20 dark frames                        │  │
│  │ [12:35:45] Applied 10 flat frames                        │  │
│  │ [12:36:02] Calibration complete                          │  │
│  │ [12:36:15] Starting histogram stretch...                 │  │
│  │ [12:36:18] Auto black point: 512                         │  │
│  │ [12:36:19] Auto white point: 45234                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Free Tools & Libraries

### Core Processing Stack (Backend)

#### 1. Siril (Command-Line)
**Purpose**: Stacking, calibration, registration
**License**: GPL-3.0 (Free)
**Installation**: `apt install siril`
**Why**: Industry-standard free tool, command-line capable

```bash
# Example Siril script for calibration
cd /tmp/session
convert light -out=/tmp/session
preprocess light -dark=master_dark -flat=master_flat -cfa
```

#### 2. Astropy
**Purpose**: FITS I/O, header manipulation, coordinates
**License**: BSD (Free)
**Installation**: `pip install astropy`
**Why**: Standard Python astronomy library

```python
from astropy.io import fits
from astropy.wcs import WCS

# Read FITS
with fits.open('M31_stacked.fit') as hdul:
    data = hdul[0].data
    header = hdul[0].header
    wcs = WCS(header)

# Modify and save
header['PROCESSED'] = 'True'
fits.writeto('M31_processed.fit', data, header)
```

#### 3. OpenCV
**Purpose**: Image processing, noise reduction
**License**: Apache-2.0 (Free)
**Installation**: `pip install opencv-python`
**Why**: Fast, optimized computer vision

```python
import cv2

# Denoise
denoised = cv2.fastNlMeansDenoising(image, h=10)

# Gradient removal (background subtraction)
background = cv2.blur(image, (50, 50))
gradient_removed = cv2.subtract(image, background)
```

#### 4. scikit-image
**Purpose**: Advanced image processing
**License**: BSD (Free)
**Installation**: `pip install scikit-image`
**Why**: Academic-quality algorithms

```python
from skimage import exposure

# Histogram stretch
stretched = exposure.rescale_intensity(
    image,
    in_range=(black_point, white_point)
)

# Adaptive histogram equalization
equalized = exposure.equalize_adapthist(image)
```

#### 5. NumPy
**Purpose**: Array operations, mathematical transforms
**License**: BSD (Free)
**Installation**: `pip install numpy`
**Why**: Foundation of scientific Python

```python
import numpy as np

# Median combine (for master calibration)
master_dark = np.median(dark_frames, axis=0)

# Statistics
mean = np.mean(image)
std = np.std(image)
snr = mean / std
```

### Frontend Libraries

#### 1. FITS.js or fits-viewer.js
**Purpose**: Display FITS in browser
**License**: MIT (Free)
**Why**: View FITS without conversion

```javascript
// Display FITS in canvas
const fits = new FITS();
fits.load(url, function() {
  fits.displayTo('#canvas');
});
```

#### 2. Chart.js
**Purpose**: Histogram visualization
**License**: MIT (Free)
**Why**: Interactive charts for data analysis

```javascript
// Display histogram
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: bins,
    datasets: [{
      label: 'Pixel Distribution',
      data: histogram
    }]
  }
});
```

---

## Implementation Phases

### Phase 1: MVP (Q2 2026) - 4-6 weeks

**Goal**: Basic upload, quick preset, download

**Features**:
- ✅ File upload (FITS, ZIP)
- ✅ Session parsing and display
- ✅ One quick preset: "Quick DSO"
- ✅ Calibration (dark/flat/bias)
- ✅ Histogram stretch
- ✅ Export JPEG/TIFF
- ✅ Basic preview

**Dependencies**:
```python
astropy==6.0.0
opencv-python==4.8.0
pillow==10.0.0
numpy==1.24.0
celery==5.3.0
redis==5.0.0
```

**API Endpoints**:
```
POST   /api/process/upload          # Upload session files
GET    /api/process/sessions        # List sessions
GET    /api/process/sessions/{id}   # Get session details
POST   /api/process/sessions/{id}/quick  # Run quick preset
GET    /api/process/jobs/{id}       # Get job status
GET    /api/process/jobs/{id}/download  # Download result
```

### Phase 2: Custom Pipelines (Q3 2026) - 4-6 weeks

**Goal**: Advanced workflow builder

**Features**:
- ✅ Custom pipeline builder UI
- ✅ 5+ processing steps
- ✅ Parameter adjustment
- ✅ Step-by-step preview
- ✅ Save/load recipes
- ✅ Before/after comparison

**New Steps**:
- Gradient removal
- Star reduction
- Noise reduction
- Color balance
- Sharpening

### Phase 3: Analysis & Integration (Q4 2026) - 4-6 weeks

**Goal**: Session analysis and plan integration

**Features**:
- ✅ FWHM/seeing analysis
- ✅ Star count statistics
- ✅ Frame quality scoring
- ✅ Session report generation
- ✅ Link to observation plan
- ✅ Batch processing multiple sessions
- ✅ Export to PixInsight format

**New Services**:
```python
session_analyzer.py     # Quality metrics
star_detection.py       # SExtractor integration
plate_solver.py         # Astrometry.net (optional)
```

---

## Storage & Performance

### File Storage Strategy

**Phase 1**: Local filesystem
```
/app/data/processing/
├── sessions/
│   ├── session_001/
│   │   ├── uploads/       # Original files
│   │   ├── working/       # Intermediate files
│   │   └── outputs/       # Final processed files
│   └── session_002/
└── cache/
    └── previews/          # JPEG previews
```

**Phase 2**: S3-compatible storage (MinIO/AWS S3)
- Cheaper long-term storage
- CDN integration for downloads
- Automatic cleanup after 30 days

### Performance Considerations

**File Size Limits**:
- Single file: 500MB max
- Session total: 10GB max
- Automatic ZIP extraction

**Processing Timeouts**:
- Quick preset: 5 minutes max
- Custom pipeline: 30 minutes max
- Background worker timeout: 1 hour

**Optimization**:
- Downsampled previews (512x512) for real-time UI
- Progressive JPEG for fast loading
- Redis caching for session metadata
- Cleanup old sessions after 30 days

---

## Security Considerations

### File Upload Safety

1. **Validation**:
   - Allowed extensions: `.fit`, `.fits`, `.fit.gz`, `.zip`
   - Magic number validation (not just extension)
   - Maximum file size enforcement
   - Virus scanning (ClamAV) for uploaded files

2. **Sandboxing**:
   - Process files in isolated tmp directories
   - No shell command injection (use subprocess with lists)
   - Limited file system access for processing workers

3. **Resource Limits**:
   - Memory limit per job (4GB)
   - CPU limit per job (2 cores)
   - Disk space monitoring
   - Job queue size limits

### Privacy & Data Retention

1. **Data Ownership**:
   - Users own uploaded data
   - No training on user data
   - Optional: User accounts for privacy

2. **Retention Policy**:
   - Uploaded files: 7 days
   - Processed files: 30 days
   - Session metadata: 90 days
   - User can delete anytime

3. **Access Control**:
   - Session IDs are UUIDs (non-guessable)
   - No public listing of sessions
   - Optional: Authentication for sensitive data

---

## Open Questions & Research Needed

1. **Seestar S50 File Format Confirmation**
   - ❓ Exact FITS header structure
   - ❓ Does it produce stacked files or only individual frames?
   - ❓ Calibration frame availability
   - ❓ Session log format
   - **Action**: Test with actual Seestar output

2. **Siril Command-Line Capabilities**
   - ❓ Can it be fully automated via scripts?
   - ❓ Progress reporting for long operations?
   - ❓ Return codes and error handling
   - **Action**: Test Siril CLI in Docker

3. **Frontend FITS Display**
   - ❓ Best library for browser FITS viewing?
   - ❓ Performance with large files (>100MB)?
   - ❓ Stretch/zoom controls
   - **Action**: Prototype with fits-viewer.js

4. **Storage Costs**
   - ❓ Average session size from Seestar?
   - ❓ How many sessions per user per month?
   - ❓ S3 vs local storage breakeven point?
   - **Action**: Estimate based on typical usage

---

## Success Metrics

- **Adoption**: 50% of users try Process tab within first month
- **Completion**: 80% of uploads result in successful processing
- **Speed**: Quick preset completes in <3 minutes
- **Quality**: 90% user satisfaction with output quality
- **Retention**: Users return to process 3+ sessions per month

---

## Next Steps

1. **Research Phase** (1 week)
   - Test with actual Seestar S50 output files
   - Validate Siril command-line automation
   - Prototype FITS display in browser

2. **Design Review** (1 week)
   - Review with stakeholders
   - Finalize UI mockups
   - Confirm technical architecture

3. **Phase 1 Implementation** (4-6 weeks)
   - Backend processing service
   - File upload and session management
   - Quick DSO preset
   - Basic UI

4. **Testing & Iteration** (2 weeks)
   - Test with real session data
   - Performance optimization
   - User feedback

---

**Total Free/Open-Source Cost**: $0/month
**Infrastructure Cost (Phase 1)**: $0 (local filesystem)
**Infrastructure Cost (Phase 2)**: ~$10-20/month (S3/MinIO storage)

**All processing tools are free and open-source!**

---

*Last Updated*: 2025-11-05
*Status*: Design Phase - Ready for Review
*Next Action*: Test with Seestar S50 output files
