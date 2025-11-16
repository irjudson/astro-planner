# Implementation Plan: Mosaicing and Advanced Stacking

## Overview
This document outlines the complete implementation plan for adding mosaicing (multi-panel imaging) and advanced stacking capabilities to Astro Planner.

---

## Phase 1: Mosaic Planning (Weeks 1-2)

### Goal
Allow users to plan multi-panel observations that cover areas larger than the Seestar S50's FOV (1.27° × 0.71°).

### 1.1 Mosaic Panel Calculator

**New Module:** `backend/app/services/mosaic_service.py`

```python
class MosaicService:
    def calculate_mosaic_grid(
        self,
        center_ra: float,      # Target center RA in degrees
        center_dec: float,     # Target center DEC in degrees
        width_deg: float,      # Desired mosaic width in degrees
        height_deg: float,     # Desired mosaic height in degrees
        overlap_percent: float = 25,  # Overlap between panels (20-30% typical)
        fov_width: float = 1.27,      # Seestar S50 FOV width
        fov_height: float = 0.71      # Seestar S50 FOV height
    ) -> List[MosaicPanel]:
        """
        Calculate grid of panels needed to cover target area.

        Returns list of panels with:
        - panel_id (e.g., "P1", "P2", etc.)
        - ra, dec (center coordinates)
        - position in grid (row, col)
        - neighbors (for overlap tracking)
        """

    def estimate_total_time(
        self,
        panels: List[MosaicPanel],
        exposure_per_panel: int  # minutes per panel
    ) -> dict:
        """
        Calculate total imaging time including:
        - Slew time between panels
        - Focus time (every N panels)
        - Total exposure time
        - Estimated completion time
        """
```

**Features:**
- Automatic grid calculation based on desired FOV
- Handle declination compression (panels get narrower near poles)
- Overlap optimization for stitching
- Panel numbering in spiral or row-by-row pattern

### 1.2 Mosaic Planning UI

**Location:** `frontend/index.html` - Add to Planner tab

**New Controls:**
```html
<div id="mosaic-planner-section" style="display: none;">
    <h3>🧩 Mosaic Planning</h3>

    <!-- Target Selection -->
    <div>
        <label>Target Name:</label>
        <input type="text" id="mosaic-target-name" placeholder="M31, IC 1396, etc.">
        <button onclick="resolveMosaicTarget()">Resolve</button>
    </div>

    <!-- Mosaic Size -->
    <div>
        <label>Mosaic Width (degrees):</label>
        <input type="number" id="mosaic-width" value="2.5" step="0.1" min="1.27">

        <label>Mosaic Height (degrees):</label>
        <input type="number" id="mosaic-height" value="2.0" step="0.1" min="0.71">
    </div>

    <!-- Overlap -->
    <div>
        <label>Panel Overlap (%):</label>
        <input type="range" id="mosaic-overlap" min="15" max="40" value="25">
        <span id="overlap-display">25%</span>
    </div>

    <!-- Exposure per Panel -->
    <div>
        <label>Exposure per Panel (minutes):</label>
        <input type="number" id="panel-exposure" value="30" min="5">
    </div>

    <!-- Generate Button -->
    <button onclick="generateMosaicPlan()" class="btn btn-primary">
        🧩 Generate Mosaic Plan
    </button>

    <!-- Preview Canvas -->
    <canvas id="mosaic-preview" width="600" height="400"></canvas>

    <!-- Panel Summary -->
    <div id="mosaic-summary"></div>
</div>
```

**JavaScript Functions:**
```javascript
async function generateMosaicPlan() {
    const target = document.getElementById('mosaic-target-name').value;
    const width = parseFloat(document.getElementById('mosaic-width').value);
    const height = parseFloat(document.getElementById('mosaic-height').value);
    const overlap = parseFloat(document.getElementById('mosaic-overlap').value);
    const exposure = parseInt(document.getElementById('panel-exposure').value);

    // Call backend API
    const response = await fetch('/api/planner/mosaic', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            target_name: target,
            width_deg: width,
            height_deg: height,
            overlap_percent: overlap,
            exposure_minutes: exposure
        })
    });

    const mosaicPlan = await response.json();

    // Draw preview
    drawMosaicPreview(mosaicPlan);

    // Show summary
    displayMosaicSummary(mosaicPlan);
}

function drawMosaicPreview(plan) {
    const canvas = document.getElementById('mosaic-preview');
    const ctx = canvas.getContext('2d');

    // Clear canvas
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw each panel
    plan.panels.forEach((panel, idx) => {
        // Calculate screen position
        const x = (panel.ra - plan.center_ra) * scale + centerX;
        const y = (panel.dec - plan.center_dec) * scale + centerY;

        // Draw panel rectangle
        ctx.strokeStyle = '#4a9eff';
        ctx.strokeRect(x, y, panelWidth, panelHeight);

        // Draw panel number
        ctx.fillStyle = '#fff';
        ctx.fillText(`P${idx + 1}`, x + 5, y + 15);
    });
}
```

### 1.3 API Endpoints

**New Routes:** `backend/app/api/routes.py`

```python
@app.post("/api/planner/mosaic")
async def create_mosaic_plan(request: MosaicPlanRequest):
    """Generate a mosaic observation plan."""
    mosaic_service = MosaicService()

    # Resolve target coordinates
    target_coords = astronomy_service.resolve_target(request.target_name)

    # Calculate panel grid
    panels = mosaic_service.calculate_mosaic_grid(
        center_ra=target_coords.ra,
        center_dec=target_coords.dec,
        width_deg=request.width_deg,
        height_deg=request.height_deg,
        overlap_percent=request.overlap_percent
    )

    # Estimate timing
    timing = mosaic_service.estimate_total_time(
        panels=panels,
        exposure_per_panel=request.exposure_minutes
    )

    return {
        "target_name": request.target_name,
        "center_ra": target_coords.ra,
        "center_dec": target_coords.dec,
        "panels": panels,
        "total_panels": len(panels),
        "timing": timing
    }
```

**Data Models:** `backend/app/models/mosaic_models.py`

```python
from pydantic import BaseModel
from typing import List

class MosaicPanel(BaseModel):
    panel_id: str           # e.g., "P1", "P2"
    ra: float              # Center RA
    dec: float             # Center DEC
    row: int               # Grid row
    col: int               # Grid column
    neighbors: List[str]   # Adjacent panel IDs

class MosaicPlanRequest(BaseModel):
    target_name: str
    width_deg: float
    height_deg: float
    overlap_percent: float = 25
    exposure_minutes: int = 30

class MosaicPlan(BaseModel):
    target_name: str
    center_ra: float
    center_dec: float
    panels: List[MosaicPanel]
    total_panels: int
    timing: dict
```

---

## Phase 2: Mosaic Execution (Weeks 3-4)

### Goal
Execute mosaic plans automatically, moving telescope to each panel position.

### 2.1 Mosaic Execution Service

**Update:** `backend/app/services/telescope_service.py`

```python
async def execute_mosaic_plan(
    self,
    mosaic_plan: MosaicPlan,
    exposure_per_panel: int,
    focus_every_n_panels: int = 4,
    callback: Optional[Callable] = None
) -> MosaicExecutionResult:
    """
    Execute a mosaic observation plan.

    For each panel:
    1. Slew to panel center
    2. Auto-focus (if needed)
    3. Start imaging
    4. Wait for completion
    5. Save panel data
    6. Move to next panel
    """
    results = []

    for idx, panel in enumerate(mosaic_plan.panels):
        # Progress callback
        if callback:
            callback({
                "panel": panel.panel_id,
                "progress": (idx / len(mosaic_plan.panels)) * 100,
                "phase": "slewing"
            })

        # Slew to panel
        success = await self.seestar_client.goto_target(
            ra=panel.ra,
            dec=panel.dec,
            target_name=f"{mosaic_plan.target_name}_{panel.panel_id}"
        )

        if not success:
            results.append({"panel": panel.panel_id, "status": "failed", "reason": "slew_failed"})
            continue

        # Focus if needed
        if idx % focus_every_n_panels == 0:
            if callback:
                callback({"phase": "focusing"})
            await self.seestar_client.auto_focus()

        # Image
        if callback:
            callback({"phase": "imaging"})

        await self.seestar_client.start_imaging()
        await asyncio.sleep(exposure_per_panel * 60)  # Wait for exposure
        await self.seestar_client.stop_imaging()

        results.append({"panel": panel.panel_id, "status": "complete"})

    return MosaicExecutionResult(panels=results)
```

### 2.2 Mosaic Session Tracking

**Database Model:** `backend/app/models/mosaic_models.py`

```python
class MosaicSession(Base):
    __tablename__ = "mosaic_sessions"

    id = Column(Integer, primary_key=True)
    session_name = Column(String, unique=True)
    target_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Mosaic configuration
    center_ra = Column(Float)
    center_dec = Column(Float)
    width_deg = Column(Float)
    height_deg = Column(Float)
    overlap_percent = Column(Float)

    # Execution tracking
    status = Column(String)  # 'planned', 'executing', 'complete', 'failed'
    panels_complete = Column(Integer, default=0)
    panels_total = Column(Integer)

    # Results
    panels = relationship("MosaicPanelCapture", back_populates="session")

class MosaicPanelCapture(Base):
    __tablename__ = "mosaic_panel_captures"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("mosaic_sessions.id"))
    panel_id = Column(String)  # "P1", "P2", etc.

    # Coordinates
    ra = Column(Float)
    dec = Column(Float)
    row = Column(Integer)
    col = Column(Integer)

    # Capture details
    status = Column(String)  # 'pending', 'capturing', 'complete', 'failed'
    captured_at = Column(DateTime)
    exposure_time = Column(Integer)  # seconds

    # File reference
    fits_file_path = Column(String)

    session = relationship("MosaicSession", back_populates="panels")
```

---

## Phase 3: Mosaic Stitching (Weeks 5-6)

### Goal
Combine captured panels into a single large image.

### 3.1 Image Registration and Alignment

**New Module:** `backend/app/services/mosaic_stitcher.py`

```python
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import shift
from skimage.feature import register_translation
from skimage.transform import warp, SimilarityTransform

class MosaicStitcher:
    def __init__(self):
        self.overlap_threshold = 0.8  # 80% match required

    def load_panel(self, fits_path: str) -> Tuple[np.ndarray, WCS]:
        """Load FITS panel and extract WCS."""
        with fits.open(fits_path) as hdul:
            data = hdul[0].data
            wcs = WCS(hdul[0].header)
        return data, wcs

    def find_overlap_region(
        self,
        panel1: np.ndarray,
        panel2: np.ndarray,
        overlap_direction: str  # 'horizontal', 'vertical'
    ) -> Tuple[int, int]:
        """
        Find offset between overlapping panels using cross-correlation.
        Returns (x_offset, y_offset) in pixels.
        """
        # Use phase cross-correlation for sub-pixel accuracy
        shift_result, error, diffphase = register_translation(
            panel1,
            panel2,
            upsample_factor=10
        )
        return shift_result

    def align_panels(
        self,
        panels: List[Tuple[np.ndarray, WCS]],
        mosaic_plan: MosaicPlan
    ) -> List[Tuple[np.ndarray, Tuple[int, int]]]:
        """
        Align all panels to a common reference frame.
        Returns list of (aligned_data, (x_offset, y_offset)).
        """
        # Use first panel as reference
        reference = panels[0]
        aligned = [(reference[0], (0, 0))]

        for idx, (panel_data, panel_wcs) in enumerate(panels[1:], 1):
            # Find which panel(s) this overlaps with
            neighbors = mosaic_plan.panels[idx].neighbors

            # Calculate offset from overlapping panels
            offset = self.calculate_offset_from_neighbors(
                panel_data,
                aligned,
                neighbors
            )

            aligned.append((panel_data, offset))

        return aligned

    def blend_overlaps(
        self,
        panel1: np.ndarray,
        panel2: np.ndarray,
        overlap_width: int
    ) -> np.ndarray:
        """
        Blend overlapping regions using gradient weighting.
        This prevents visible seams between panels.
        """
        # Create alpha mask for smooth blending
        alpha = np.linspace(0, 1, overlap_width)

        # Apply gradient blend in overlap region
        blended = panel1 * (1 - alpha) + panel2 * alpha

        return blended

    def stitch_mosaic(
        self,
        session_id: int
    ) -> str:
        """
        Main stitching function.

        Process:
        1. Load all captured panels
        2. Align panels using star registration
        3. Create output canvas
        4. Place panels with gradient blending
        5. Save final mosaic FITS
        """
        # Load session and panels
        session = db.query(MosaicSession).get(session_id)
        panels = db.query(MosaicPanelCapture).filter_by(
            session_id=session_id,
            status='complete'
        ).all()

        # Load FITS data
        panel_data = []
        for panel in panels:
            data, wcs = self.load_panel(panel.fits_file_path)
            panel_data.append((data, wcs, panel))

        # Align all panels
        aligned = self.align_panels(panel_data, session.mosaic_plan)

        # Calculate output canvas size
        canvas_size = self.calculate_canvas_size(aligned)
        output = np.zeros(canvas_size, dtype=np.float32)
        weight_map = np.zeros(canvas_size, dtype=np.float32)

        # Place each panel on canvas with blending
        for (data, (x_off, y_off)) in aligned:
            self.place_panel_on_canvas(
                output,
                weight_map,
                data,
                x_off,
                y_off
            )

        # Normalize by weight map
        output = output / (weight_map + 1e-10)

        # Save result
        output_path = f"mosaics/{session.session_name}_mosaic.fits"
        self.save_mosaic_fits(output, session, output_path)

        return output_path

    def place_panel_on_canvas(
        self,
        canvas: np.ndarray,
        weight_map: np.ndarray,
        panel_data: np.ndarray,
        x_offset: int,
        y_offset: int
    ):
        """
        Place panel on canvas with distance-weighted blending.
        Panels contribute more weight at their center, less at edges.
        """
        h, w = panel_data.shape

        # Create distance-based weight for this panel
        y_dist = np.linspace(-1, 1, h)
        x_dist = np.linspace(-1, 1, w)
        y_grid, x_grid = np.meshgrid(y_dist, x_dist, indexing='ij')

        # Gaussian weight (higher in center)
        weight = np.exp(-(x_grid**2 + y_grid**2) / 0.5)

        # Add to canvas
        canvas[y_offset:y_offset+h, x_offset:x_offset+w] += panel_data * weight
        weight_map[y_offset:y_offset+h, x_offset:x_offset+w] += weight
```

### 3.2 Star Detection for Registration

**Helper Module:** `backend/app/services/star_detection.py`

```python
from scipy.ndimage import gaussian_filter, maximum_filter
from skimage.feature import peak_local_max

class StarDetector:
    def detect_stars(
        self,
        image: np.ndarray,
        threshold: float = 5.0,  # sigma above background
        min_separation: int = 5   # pixels
    ) -> np.ndarray:
        """
        Detect stars in image using local maxima detection.
        Returns array of (x, y) star coordinates.
        """
        # Smooth image to reduce noise
        smoothed = gaussian_filter(image, sigma=2)

        # Find local maxima
        local_max = maximum_filter(smoothed, size=min_separation)
        detected = (smoothed == local_max)

        # Apply threshold
        background = np.median(image)
        noise = np.std(image)
        threshold_value = background + threshold * noise

        detected &= (smoothed > threshold_value)

        # Get coordinates
        stars = np.argwhere(detected)

        return stars

    def match_star_patterns(
        self,
        stars1: np.ndarray,
        stars2: np.ndarray,
        max_distance: float = 10.0
    ) -> List[Tuple[int, int]]:
        """
        Match star patterns between two images.
        Returns list of (idx1, idx2) matched star pairs.
        """
        from scipy.spatial import KDTree

        # Build KD-tree for fast nearest-neighbor search
        tree = KDTree(stars2)

        matches = []
        for idx1, star1 in enumerate(stars1):
            # Find nearest star in image 2
            dist, idx2 = tree.query(star1)

            if dist < max_distance:
                matches.append((idx1, idx2))

        return matches
```

### 3.3 API Endpoints for Stitching

```python
@app.post("/api/mosaic/{session_id}/stitch")
async def stitch_mosaic(
    session_id: int,
    background_tasks: BackgroundTasks
):
    """Start mosaic stitching job."""
    stitcher = MosaicStitcher()

    # Start background job
    job = ProcessingJob(
        session_id=session_id,
        job_type='mosaic_stitch',
        status='pending'
    )
    db.add(job)
    db.commit()

    background_tasks.add_task(
        stitcher.stitch_mosaic,
        session_id=session_id,
        job_id=job.id
    )

    return {"job_id": job.id, "status": "started"}

@app.get("/api/mosaic/{session_id}/preview")
async def get_mosaic_preview(session_id: int):
    """Generate quick preview of mosaic layout."""
    # Return panel positions and thumbnails
    pass
```

---

## Phase 4: Advanced Stacking (Weeks 7-8)

### Goal
Stack multiple sub-frames with rejection algorithms to improve SNR and remove artifacts.

### 4.1 Frame Stacking Service

**New Module:** `backend/app/services/frame_stacker.py`

```python
from typing import List, Literal
import numpy as np
from astropy.io import fits

class FrameStacker:
    def __init__(self):
        self.rejection_methods = [
            'none',
            'sigma_clip',
            'winsorized_sigma_clip',
            'min_max',
            'percentile'
        ]

    def stack_frames(
        self,
        frame_paths: List[str],
        method: Literal['median', 'mean', 'sum'] = 'median',
        rejection: str = 'sigma_clip',
        rejection_params: dict = None
    ) -> np.ndarray:
        """
        Stack multiple frames with rejection.

        Args:
            frame_paths: List of FITS file paths
            method: Stacking method (median, mean, sum)
            rejection: Rejection algorithm
            rejection_params: Parameters for rejection (e.g., sigma=3.0)

        Returns:
            Stacked image as numpy array
        """
        # Load all frames
        frames = []
        for path in frame_paths:
            with fits.open(path) as hdul:
                frames.append(hdul[0].data.astype(np.float32))

        # Stack as 3D array (frames, height, width)
        frame_cube = np.stack(frames, axis=0)

        # Apply rejection
        if rejection != 'none':
            mask = self.calculate_rejection_mask(
                frame_cube,
                rejection,
                rejection_params or {}
            )
            frame_cube = np.ma.array(frame_cube, mask=mask)

        # Stack
        if method == 'median':
            result = np.ma.median(frame_cube, axis=0)
        elif method == 'mean':
            result = np.ma.mean(frame_cube, axis=0)
        elif method == 'sum':
            result = np.ma.sum(frame_cube, axis=0)

        return result.filled(0)

    def calculate_rejection_mask(
        self,
        frame_cube: np.ndarray,
        rejection: str,
        params: dict
    ) -> np.ndarray:
        """
        Calculate mask of pixels to reject.

        Returns boolean mask (True = reject, False = keep).
        """
        if rejection == 'sigma_clip':
            return self.sigma_clip_rejection(
                frame_cube,
                sigma_low=params.get('sigma_low', 3.0),
                sigma_high=params.get('sigma_high', 3.0)
            )

        elif rejection == 'winsorized_sigma_clip':
            return self.winsorized_sigma_clip(
                frame_cube,
                sigma=params.get('sigma', 3.0)
            )

        elif rejection == 'min_max':
            return self.min_max_rejection(
                frame_cube,
                num_low=params.get('num_low', 1),
                num_high=params.get('num_high', 1)
            )

        elif rejection == 'percentile':
            return self.percentile_rejection(
                frame_cube,
                low_percentile=params.get('low', 5),
                high_percentile=params.get('high', 95)
            )

        return np.zeros(frame_cube.shape, dtype=bool)

    def sigma_clip_rejection(
        self,
        frame_cube: np.ndarray,
        sigma_low: float = 3.0,
        sigma_high: float = 3.0,
        max_iterations: int = 3
    ) -> np.ndarray:
        """
        Iterative sigma clipping rejection.

        Removes outliers that are more than sigma_low/sigma_high
        standard deviations from the median.
        """
        mask = np.zeros(frame_cube.shape, dtype=bool)

        for _ in range(max_iterations):
            # Calculate median and std per pixel across frames
            median = np.ma.median(
                np.ma.array(frame_cube, mask=mask),
                axis=0
            )
            std = np.ma.std(
                np.ma.array(frame_cube, mask=mask),
                axis=0
            )

            # Find outliers
            diff = frame_cube - median[np.newaxis, :, :]

            low_outliers = diff < -sigma_low * std[np.newaxis, :, :]
            high_outliers = diff > sigma_high * std[np.newaxis, :, :]

            new_mask = low_outliers | high_outliers

            # Check for convergence
            if np.array_equal(mask, new_mask):
                break

            mask = new_mask

        return mask

    def winsorized_sigma_clip(
        self,
        frame_cube: np.ndarray,
        sigma: float = 3.0
    ) -> np.ndarray:
        """
        Winsorized sigma clipping - more robust to outliers.
        Uses percentiles instead of mean/std.
        """
        # Use median absolute deviation (MAD) for robust std estimate
        median = np.median(frame_cube, axis=0)
        mad = np.median(np.abs(frame_cube - median[np.newaxis, :, :]), axis=0)
        std_estimate = 1.4826 * mad  # Scale factor for normal distribution

        # Reject outliers
        diff = frame_cube - median[np.newaxis, :, :]
        mask = np.abs(diff) > sigma * std_estimate[np.newaxis, :, :]

        return mask

    def min_max_rejection(
        self,
        frame_cube: np.ndarray,
        num_low: int = 1,
        num_high: int = 1
    ) -> np.ndarray:
        """
        Simple min/max rejection.
        Removes the N darkest and N brightest pixels per pixel position.
        """
        mask = np.zeros(frame_cube.shape, dtype=bool)

        if num_low > 0:
            # Find indices of lowest values
            lowest = np.argpartition(frame_cube, num_low, axis=0)[:num_low]
            np.put_along_axis(mask, lowest, True, axis=0)

        if num_high > 0:
            # Find indices of highest values
            highest = np.argpartition(frame_cube, -num_high, axis=0)[-num_high:]
            np.put_along_axis(mask, highest, True, axis=0)

        return mask

    def percentile_rejection(
        self,
        frame_cube: np.ndarray,
        low_percentile: float = 5,
        high_percentile: float = 95
    ) -> np.ndarray:
        """
        Reject pixels outside percentile range.
        """
        low_thresh = np.percentile(frame_cube, low_percentile, axis=0)
        high_thresh = np.percentile(frame_cube, high_percentile, axis=0)

        mask = (
            (frame_cube < low_thresh[np.newaxis, :, :]) |
            (frame_cube > high_thresh[np.newaxis, :, :])
        )

        return mask

    def align_frames(
        self,
        frame_paths: List[str],
        reference_idx: int = 0
    ) -> List[np.ndarray]:
        """
        Align all frames to a reference frame using star registration.

        This is critical for good stacking quality.
        """
        star_detector = StarDetector()

        # Load reference frame
        with fits.open(frame_paths[reference_idx]) as hdul:
            reference = hdul[0].data.astype(np.float32)

        ref_stars = star_detector.detect_stars(reference)

        aligned_frames = [reference]

        # Align each frame to reference
        for idx, path in enumerate(frame_paths):
            if idx == reference_idx:
                continue

            with fits.open(path) as hdul:
                frame = hdul[0].data.astype(np.float32)

            # Detect stars
            frame_stars = star_detector.detect_stars(frame)

            # Match star patterns
            matches = star_detector.match_star_patterns(
                ref_stars,
                frame_stars
            )

            # Calculate transformation
            transform = self.calculate_transform_from_matches(
                ref_stars,
                frame_stars,
                matches
            )

            # Apply transformation
            aligned = self.apply_transform(frame, transform)
            aligned_frames.append(aligned)

        return aligned_frames
```

### 4.2 Integration with Processing Pipeline

**Update:** `backend/app/services/processing_service.py`

```python
async def process_with_stacking(
    self,
    session_id: int,
    stack_config: StackConfig
) -> ProcessingJob:
    """
    Process session with frame stacking.

    Steps:
    1. Load all light frames
    2. Align frames using star detection
    3. Stack with rejection
    4. Apply calibration (if available)
    5. Apply processing pipeline
    6. Export result
    """
    stacker = FrameStacker()

    # Load session frames
    session = db.query(ProcessingSession).get(session_id)
    frame_paths = [f.file_path for f in session.files if f.file_type == 'light']

    # Align frames
    logger.info(f"Aligning {len(frame_paths)} frames...")
    aligned_frames = stacker.align_frames(frame_paths)

    # Stack with rejection
    logger.info(f"Stacking with {stack_config.rejection} rejection...")
    stacked = stacker.stack_frames(
        aligned_frames,
        method=stack_config.method,
        rejection=stack_config.rejection,
        rejection_params=stack_config.rejection_params
    )

    # Continue with normal processing pipeline
    # ...
```

---

## Phase 5: Gradient Removal (Week 9)

### Goal
Remove light pollution and vignetting gradients from images.

### 5.1 Gradient Detection and Removal

**New Module:** `backend/app/services/gradient_removal.py`

```python
from scipy.ndimage import median_filter, gaussian_filter
from skimage.morphology import disk, white_tophat

class GradientRemover:
    def remove_gradient(
        self,
        image: np.ndarray,
        method: Literal['polynomial', 'morphological', 'dbe'] = 'dbe',
        mask_stars: bool = True
    ) -> np.ndarray:
        """
        Remove background gradient from image.

        Methods:
        - polynomial: Fit low-order polynomial surface
        - morphological: Use morphological opening
        - dbe: Dynamic Background Extraction (most sophisticated)
        """
        if mask_stars:
            star_mask = self.create_star_mask(image)
        else:
            star_mask = None

        if method == 'polynomial':
            return self.polynomial_gradient_removal(image, star_mask)
        elif method == 'morphological':
            return self.morphological_gradient_removal(image)
        elif method == 'dbe':
            return self.dynamic_background_extraction(image, star_mask)

    def create_star_mask(
        self,
        image: np.ndarray,
        threshold: float = 5.0
    ) -> np.ndarray:
        """
        Create mask of stars to exclude from gradient calculation.
        """
        from skimage.morphology import binary_dilation, disk

        # Detect bright pixels (stars)
        median = np.median(image)
        std = np.std(image)
        star_pixels = image > (median + threshold * std)

        # Dilate to capture full star profiles
        star_mask = binary_dilation(star_pixels, disk(5))

        return star_mask

    def polynomial_gradient_removal(
        self,
        image: np.ndarray,
        star_mask: Optional[np.ndarray] = None,
        degree: int = 3
    ) -> np.ndarray:
        """
        Fit polynomial surface to background and subtract.
        """
        from scipy.optimize import curve_fit

        h, w = image.shape

        # Create coordinate grid
        y, x = np.mgrid[0:h, 0:w]

        # Flatten
        x_flat = x.ravel()
        y_flat = y.ravel()
        z_flat = image.ravel()

        # Exclude stars if mask provided
        if star_mask is not None:
            mask_flat = ~star_mask.ravel()
            x_flat = x_flat[mask_flat]
            y_flat = y_flat[mask_flat]
            z_flat = z_flat[mask_flat]

        # Fit polynomial surface
        def polynomial_surface(xy, *coeffs):
            x, y = xy
            result = np.zeros_like(x)
            idx = 0
            for i in range(degree + 1):
                for j in range(degree + 1 - i):
                    result += coeffs[idx] * (x ** i) * (y ** j)
                    idx += 1
            return result

        # Initial guess
        num_coeffs = sum(range(degree + 2))
        p0 = np.zeros(num_coeffs)
        p0[0] = np.median(z_flat)

        # Fit
        popt, _ = curve_fit(
            polynomial_surface,
            (x_flat, y_flat),
            z_flat,
            p0=p0
        )

        # Generate background model
        background = polynomial_surface((x, y), *popt).reshape(h, w)

        # Subtract
        corrected = image - background

        return corrected

    def dynamic_background_extraction(
        self,
        image: np.ndarray,
        star_mask: Optional[np.ndarray] = None,
        box_size: int = 50,
        sigma: float = 3.0
    ) -> np.ndarray:
        """
        Dynamic Background Extraction - most sophisticated method.

        Similar to PixInsight's DBE:
        1. Divide image into grid
        2. Calculate background in each box (avoiding stars)
        3. Interpolate to create smooth background model
        4. Subtract from image
        """
        from scipy.interpolate import RectBivariateSpline

        h, w = image.shape

        # Create grid of sample points
        y_points = np.arange(box_size // 2, h, box_size)
        x_points = np.arange(box_size // 2, w, box_size)

        # Sample background at each grid point
        background_samples = np.zeros((len(y_points), len(x_points)))

        for i, y in enumerate(y_points):
            for j, x in enumerate(x_points):
                # Extract box
                y_start = max(0, y - box_size // 2)
                y_end = min(h, y + box_size // 2)
                x_start = max(0, x - box_size // 2)
                x_end = min(w, x + box_size // 2)

                box = image[y_start:y_end, x_start:x_end]

                if star_mask is not None:
                    box_mask = star_mask[y_start:y_end, x_start:x_end]
                    box = box[~box_mask]

                # Use robust estimator (median)
                background_samples[i, j] = np.median(box) if len(box) > 0 else 0

        # Interpolate to full image size
        interpolator = RectBivariateSpline(
            y_points,
            x_points,
            background_samples,
            kx=3,
            ky=3
        )

        y_full = np.arange(h)
        x_full = np.arange(w)
        background_model = interpolator(y_full, x_full)

        # Subtract
        corrected = image - background_model

        return corrected
```

---

## Phase 6: Star Reduction (Week 10)

### Goal
Reduce star prominence to emphasize nebulosity in DSO images.

### 5.1 Star Reduction Service

**New Module:** `backend/app/services/star_reduction.py`

```python
from scipy.ndimage import gaussian_filter, median_filter
from skimage.morphology import disk, erosion, dilation, white_tophat

class StarReducer:
    def reduce_stars(
        self,
        image: np.ndarray,
        amount: float = 0.5,  # 0.0 = no reduction, 1.0 = maximum
        protect_structures: bool = True
    ) -> np.ndarray:
        """
        Reduce star prominence while preserving nebulosity.

        Process:
        1. Detect stars
        2. Create star mask
        3. Separate stars from background
        4. Reduce star layer
        5. Recombine
        """
        # Detect stars
        star_layer = self.extract_star_layer(image)

        # Create protection mask for nebulosity
        if protect_structures:
            structure_mask = self.detect_structures(image)
        else:
            structure_mask = None

        # Reduce star layer
        reduced_stars = star_layer * (1.0 - amount)

        # Protect structures
        if structure_mask is not None:
            reduced_stars[structure_mask] = star_layer[structure_mask]

        # Recombine
        background = image - star_layer
        result = background + reduced_stars

        return result

    def extract_star_layer(
        self,
        image: np.ndarray,
        min_star_size: int = 3,
        max_star_size: int = 20
    ) -> np.ndarray:
        """
        Extract star layer using morphological operations.

        Uses multiscale morphological filtering to separate
        point sources (stars) from extended structures (nebulae).
        """
        # Morphological white top-hat with star-sized structuring element
        star_layer = np.zeros_like(image)

        for size in range(min_star_size, max_star_size, 2):
            # Top-hat transform isolates bright small structures
            structure_elem = disk(size)
            layer = white_tophat(image, structure_elem)
            star_layer = np.maximum(star_layer, layer)

        return star_layer

    def detect_structures(
        self,
        image: np.ndarray,
        min_structure_size: int = 50
    ) -> np.ndarray:
        """
        Detect extended structures (nebulae) to protect from star reduction.
        """
        # Smooth to get large-scale structures
        smoothed = gaussian_filter(image, sigma=min_structure_size / 3)

        # Threshold to get structure mask
        threshold = np.median(smoothed) + 2 * np.std(smoothed)
        structure_mask = smoothed > threshold

        # Dilate to ensure protection
        structure_mask = dilation(structure_mask, disk(5))

        return structure_mask
```

---

## Phase 7: Testing and UI Integration (Weeks 11-12)

### 7.1 Processing Presets

Add new presets with all the advanced features:

```python
PROCESSING_PRESETS = {
    "mosaic_dso": {
        "name": "Mosaic DSO",
        "description": "Full pipeline for mosaic deep-sky objects",
        "steps": [
            {"type": "align_and_stack", "params": {
                "method": "median",
                "rejection": "sigma_clip",
                "sigma_low": 3.0,
                "sigma_high": 3.0
            }},
            {"type": "gradient_removal", "params": {
                "method": "dbe",
                "mask_stars": True
            }},
            {"type": "star_reduction", "params": {
                "amount": 0.6,
                "protect_structures": True
            }},
            {"type": "histogram_stretch", "params": {
                "target_median": 0.25,
                "shadows_clip": 0.0
            }},
            {"type": "export", "params": {
                "format": "tiff",
                "bit_depth": 16
            }}
        ]
    },

    "narrowband_stack": {
        "name": "Narrowband Stack",
        "description": "Stack narrowband filters (Ha, OIII, SII)",
        "steps": [
            {"type": "align_and_stack", "params": {
                "method": "median",
                "rejection": "winsorized_sigma_clip"
            }},
            {"type": "gradient_removal", "params": {
                "method": "polynomial",
                "degree": 3
            }},
            {"type": "histogram_stretch", "params": {
                "target_median": 0.20
            }},
            {"type": "export", "params": {
                "format": "tiff",
                "bit_depth": 16
            }}
        ]
    }
}
```

### 7.2 UI Updates

Add controls to Process tab:

```html
<!-- Stacking Configuration -->
<div id="stacking-config" style="display: none;">
    <h4>🔗 Frame Stacking</h4>

    <label>Stacking Method:</label>
    <select id="stack-method">
        <option value="median">Median (best for rejection)</option>
        <option value="mean">Mean (best SNR)</option>
        <option value="sum">Sum (photometry)</option>
    </select>

    <label>Rejection Algorithm:</label>
    <select id="stack-rejection">
        <option value="none">None</option>
        <option value="sigma_clip" selected>Sigma Clip</option>
        <option value="winsorized_sigma_clip">Winsorized Sigma Clip</option>
        <option value="min_max">Min/Max Rejection</option>
        <option value="percentile">Percentile Clipping</option>
    </select>

    <div id="sigma-clip-params">
        <label>Low Sigma:</label>
        <input type="number" id="sigma-low" value="3.0" step="0.1">

        <label>High Sigma:</label>
        <input type="number" id="sigma-high" value="3.0" step="0.1">
    </div>
</div>

<!-- Gradient Removal -->
<div id="gradient-config">
    <h4>🌅 Gradient Removal</h4>

    <label>
        <input type="checkbox" id="enable-gradient-removal" checked>
        Remove gradients (light pollution, vignetting)
    </label>

    <label>Method:</label>
    <select id="gradient-method">
        <option value="dbe" selected>Dynamic Background Extraction (best)</option>
        <option value="polynomial">Polynomial Fit</option>
        <option value="morphological">Morphological</option>
    </select>
</div>

<!-- Star Reduction -->
<div id="star-reduction-config">
    <h4>⭐ Star Reduction</h4>

    <label>
        <input type="checkbox" id="enable-star-reduction">
        Reduce star prominence
    </label>

    <label>Amount:</label>
    <input type="range" id="star-reduction-amount" min="0" max="100" value="50">
    <span id="star-reduction-display">50%</span>

    <label>
        <input type="checkbox" id="protect-structures" checked>
        Protect nebulosity
    </label>
</div>
```

---

## Testing Plan

### Unit Tests

**Test Coverage:**
1. Mosaic panel calculation
2. Star detection and matching
3. Frame alignment
4. Stacking with various rejection methods
5. Gradient removal algorithms
6. Star reduction

**Example Test:** `backend/tests/test_frame_stacker.py`

```python
import pytest
import numpy as np
from app.services.frame_stacker import FrameStacker

def test_sigma_clip_rejection():
    """Test sigma clipping removes outliers."""
    stacker = FrameStacker()

    # Create synthetic frames with outliers
    frames = np.random.normal(100, 10, (10, 100, 100)).astype(np.float32)

    # Add hot pixels to some frames
    frames[0, 50, 50] = 1000  # Outlier
    frames[1, 50, 50] = 1000  # Outlier

    # Stack with rejection
    result = stacker.stack_frames(
        frames,
        method='median',
        rejection='sigma_clip',
        rejection_params={'sigma_low': 3.0, 'sigma_high': 3.0}
    )

    # Check that outlier was rejected
    assert result[50, 50] < 200  # Should be close to 100, not 1000

def test_mosaic_panel_calculation():
    """Test mosaic grid calculation."""
    from app.services.mosaic_service import MosaicService

    mosaic = MosaicService()

    panels = mosaic.calculate_mosaic_grid(
        center_ra=83.633,  # M42 Orion Nebula
        center_dec=-5.391,
        width_deg=2.0,
        height_deg=2.0,
        overlap_percent=25
    )

    # Should create approximately 4 panels (2x2)
    assert len(panels) >= 4

    # Check overlap
    # ...
```

### Integration Tests

1. Full mosaic workflow (plan → execute → stitch)
2. End-to-end stacking pipeline
3. Processing with all features enabled

### Real-World Testing

1. Test with actual Seestar S50 captures
2. Compare results with PixInsight/Siril
3. Verify star registration accuracy
4. Check gradient removal effectiveness

---

## Dependencies

Add to `backend/requirements-processing.txt`:

```txt
# Existing
astropy>=6.0
numpy>=1.24
scikit-image>=0.21
scipy>=1.11
Pillow>=10.0

# New for advanced processing
astroalign>=2.5.0        # Star-based image alignment
photutils>=1.9.0         # Star detection and photometry
reproject>=0.13.0        # WCS-based image reprojection
ccdproc>=2.4.0          # CCD data reduction
astroscrappy>=1.1.0      # Cosmic ray rejection
```

---

## Performance Considerations

### 1. Memory Management
- Process panels/frames in batches if needed
- Use memory-mapped FITS files for large mosaics
- Implement progressive loading

### 2. GPU Acceleration (Optional)
- CuPy for numpy operations on GPU
- Useful for stacking large frame counts
- Can provide 10-50x speedup

### 3. Caching
- Cache aligned frames to avoid re-alignment
- Cache intermediate processing steps
- Use Redis for distributed processing

### 4. Progress Tracking
- Detailed progress for long operations
- Estimated time remaining
- Cancellation support

---

## Documentation

### User Guide Sections to Create

1. **Mosaic Planning Guide**
   - How to choose mosaic size
   - Overlap recommendations
   - Time estimation

2. **Stacking Guide**
   - When to use each rejection method
   - How many frames needed for good SNR
   - Troubleshooting alignment issues

3. **Processing Guide**
   - Gradient removal best practices
   - Star reduction tips
   - Preset selection guide

4. **Examples Gallery**
   - Before/after comparisons
   - Parameter recommendations by target type
   - Common issues and solutions

---

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Mosaic Planning | 2 weeks | UI + API for mosaic grid calculation |
| 2. Mosaic Execution | 2 weeks | Automated multi-panel capture |
| 3. Mosaic Stitching | 2 weeks | Panel registration and blending |
| 4. Advanced Stacking | 2 weeks | Frame stacking with rejection |
| 5. Gradient Removal | 1 week | Background correction |
| 6. Star Reduction | 1 week | Star emphasis control |
| 7. Testing & Polish | 2 weeks | Integration testing + docs |

**Total: 12 weeks**

---

## Priority Order

If implementing incrementally:

1. **Start with Phase 4 (Advanced Stacking)** - Most immediate value, works with existing single-frame captures
2. **Then Phase 5 (Gradient Removal)** - Dramatically improves image quality
3. **Then Phase 6 (Star Reduction)** - Finishing touch for DSO images
4. **Then Phases 1-3 (Mosaicing)** - Larger feature, but very impressive when done

This allows you to show improvements quickly while working toward the full mosaic capability.

---

## Questions?

This is a comprehensive plan. Let me know which phase you'd like to start with, or if you want to adjust the approach!
