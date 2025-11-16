# Astro Planner - Current Capabilities and Roadmap

## Overview
This document summarizes what's currently working, what's partially implemented, and what needs to be built.

---

## 1. Automated Plan Execution

### ✅ What Works Now

**Telescope Control:**
- Connect to Seestar S50 via TCP (port 4700)
- Automated plan execution with retry logic
- For each target in the plan:
  1. Slew to coordinates (goto command)
  2. Perform auto-focus
  3. Image for specified duration
  4. Move to next target
- Park telescope when complete (optional)
- Progress monitoring during execution
- Abort capability

**Files:**
- `backend/app/clients/seestar_client.py` - Seestar S50 protocol implementation
- `backend/app/services/telescope_service.py` - High-level plan execution
- `backend/app/api/routes.py` - REST API endpoints

**How to Use:**
1. Manually power on and align your Seestar S50
2. Connect to telescope via web UI (Observe tab)
3. Generate a plan in the Planner tab
4. Click "Execute Plan" in Observe tab
5. Monitor progress in real-time

### ⚠️ Limitations

**Not Implemented:**
- No automatic startup sequence
- No automatic alignment verification
- No plate solving / blind solving
- No meridian flip handling
- No guiding integration
- Limited error recovery (basic retry only)

**Manual Steps Required:**
- You must manually power on the telescope
- You must manually perform initial alignment
- System assumes telescope is already aligned when execution starts

### 🔮 Future Enhancements
- Add startup sequence automation
- Add plate solving for alignment verification
- Add meridian flip detection and handling
- Improve error recovery with smarter retry logic
- Add weather monitoring integration
- Add drift alignment assistance

---

## 2. Calibration Frame Capture

### ❌ Status: Not Implemented

**What's Missing:**
- No dark frame capture functionality
- No flat frame capture functionality
- No bias frame capture functionality
- No calibration library management
- No automated calibration routines

### 📋 Requirements for Implementation

To add calibration capture, we would need to:

1. **Dark Frames:**
   - Cover optics (or wait for daylight with cap on)
   - Take series of exposures at various exposure times
   - Match temperatures to light frames
   - Store with metadata (temp, exposure, date)

2. **Flat Frames:**
   - Point at uniform light source (twilight sky, light panel)
   - Take series with optimal exposure (50-60% histogram)
   - Match filter/settings to light frames

3. **Bias Frames:**
   - Take series of zero-second exposures
   - Used for readout noise calibration

4. **Library Management:**
   - Organize by temperature, exposure, date
   - Age tracking (darks expire after ~30 days)
   - Auto-select appropriate calibration frames for processing

### 🔮 Future Implementation Plan

**Phase 1: Capture Interface**
- Add "Calibration" tab to web UI
- Buttons for dark/flat/bias capture
- Set quantity, exposure times, temperatures
- Live preview during capture

**Phase 2: Seestar Commands**
- Extend `seestar_client.py` with calibration commands
- Expose settings control (exposure, gain)
- Add optics cover detection/warning

**Phase 3: Library Management**
- Database schema for calibration frames
- Auto-organization by metadata
- Age tracking and expiration warnings
- Frame quality validation

**Phase 4: Processing Integration**
- Auto-select matching calibration frames
- Apply during processing pipeline
- Quality metrics (effectiveness ratings)

---

## 3. Mosaicing and Stacking

### Mosaicing: ❌ Not Implemented

**What's Missing:**
- No multi-panel planning
- No FOV overlap calculation
- No frame stitching/registration
- No distortion correction
- No mosaic preview

### 📋 Requirements for Mosaicing

To implement mosaicing:

1. **Planning Phase:**
   - Select target and desired FOV
   - Calculate grid of panels with overlap (typically 20-30%)
   - Account for Seestar S50 FOV: 1.27° × 0.71°
   - Generate coordinate list for each panel

2. **Capture Phase:**
   - Execute plan with position for each panel
   - Maintain consistent exposure settings
   - Track which panels succeeded/failed
   - Option to re-image failed panels

3. **Processing Phase:**
   - Register/align all panels
   - Detect overlapping stars for alignment
   - Stitch with gradient blending
   - Handle distortion correction
   - Crop to final FOV

### Stacking: ⚠️ Partially Implemented

**What Works:**
- Basic histogram stretching on pre-stacked FITS files
- Auto black/white point detection
- Export to JPEG, TIFF, PNG
- Processing queue with background jobs

**What Doesn't Work:**
- No frame-by-frame stacking (expects Seestar to do it)
- No rejection algorithms (sigma clipping, min/max reject, etc.)
- No drizzle or other advanced stacking
- No sub-frame registration
- No automatic gradient removal
- No star reduction/morphology

**Files:**
- `backend/app/services/direct_processor.py` - Basic FITS processing
- `backend/app/services/processing_service.py` - Pipeline orchestration
- `backend/app/api/processing.py` - REST API for processing

### 🔮 Awesome Images: What's Needed

To create publication-quality images:

1. **Advanced Stacking:**
   - Sigma clipping rejection (remove satellites, hot pixels)
   - Drizzle for resolution enhancement
   - Integration time tracking
   - SNR optimization

2. **Gradient Removal:**
   - Light pollution gradient detection
   - Background extraction and subtraction
   - DBE (Dynamic Background Extraction)

3. **Star Processing:**
   - Star reduction to emphasize nebulosity
   - Morphological transformation
   - Deconvolution for sharpness

4. **Color Processing:**
   - Channel combination for narrowband
   - Color calibration
   - Saturation enhancement
   - SCNR (Selective Color Noise Reduction)

5. **Noise Reduction:**
   - Multi-scale noise reduction
   - Preserve detail while reducing noise
   - Per-channel noise reduction

6. **Final Touches:**
   - Unsharp masking for detail enhancement
   - HDR combination for dynamic range
   - Curves and levels adjustment
   - Final color grading

**Integration Options:**
- Siril (open source, CLI available) - Designed in PROCESSING_DESIGN.md
- PixInsight (commercial, can script)
- Custom Python pipeline with astropy/scikit-image
- Docker containers for isolation and security

---

## 4. Image Processing Pipeline

### ✅ Currently Implemented

**Basic Processing:**
- Upload FITS files to processing sessions
- Apply histogram stretch with midtone transfer
- Auto black/white point using percentiles
- Export to JPEG, TIFF, PNG with quality settings
- Background job processing with Celery
- Session management (create, upload, process, download)

**Available Presets:**
1. `quick_dso` - Auto-stretch + JPEG export
2. `export_pixinsight` - 16-bit TIFF export

**Features:**
- Upload progress tracking (NEW!)
- Job progress monitoring
- Multi-file sessions
- Result download

### ⚠️ Designed But Not Implemented

From `PROCESSING_DESIGN.md` (comprehensive 1,765 line design doc):

1. **Advanced Processing Steps:**
   - Calibration application (darks/flats/bias)
   - Gradient removal
   - Star reduction
   - Noise reduction
   - Sharpening
   - Custom pipeline builder

2. **Docker Isolation:**
   - Sandboxed processing in containers
   - Security isolation from host
   - GPU passthrough for acceleration
   - Resource limits (CPU, memory, time)

3. **Quality Analysis:**
   - FWHM (seeing quality)
   - Star count and distribution
   - SNR measurement
   - Frame rejection suggestions

4. **Session Features:**
   - Frame quality sorting
   - Best frame selection
   - Integration time tracking
   - Automatic calibration frame matching

---

## 5. Quick Start Guide

### Current Workflow

**Planning an Observation:**
1. Go to "Planner" tab
2. Set date, location, and target list preferences
3. Click "Generate Plan"
4. Review scheduled targets with rise/set times
5. Save or export plan

**Executing the Plan:**
1. Manually power on and align your Seestar S50
2. Go to "Observe" tab
3. Enter telescope IP address
4. Click "Connect"
5. Review the plan (generated from Planner tab)
6. Click "Execute Plan"
7. Monitor progress in real-time
8. Wait for completion or abort if needed

**Processing Captured Images:**
1. Go to "Process" tab
2. Create a new processing session (give it a name)
3. Upload FITS files (with progress tracking!)
4. Choose a processing preset:
   - Quick DSO (fast auto-stretch)
   - PixInsight Export (16-bit TIFF)
5. Monitor processing job progress
6. Download results when complete

---

## 6. Priority Recommendations

Based on your questions, here's what I'd recommend prioritizing:

### High Priority (Most Impact)

1. **Add Upload Progress Indicator** ✅ DONE
   - Just implemented! Shows real-time upload progress with percentage and bar

2. **Improve Execution UX**
   - Add clear instructions about manual alignment requirement
   - Add pre-flight checklist (telescope aligned? covers off? etc.)
   - Add confirmation that telescope is ready before execution

3. **Document Current Workflow**
   - Create user guide with screenshots
   - Add troubleshooting section
   - Include best practices

### Medium Priority (Nice to Have)

4. **Add Calibration Frame Capture**
   - Start with dark frame capture
   - Add library management
   - Integrate with processing pipeline

5. **Enhanced Processing**
   - Add gradient removal
   - Add basic star reduction
   - Add more presets (Ha, OIII, broadband, etc.)

6. **Session Management**
   - Better session organization
   - Frame quality indicators
   - Automatic best-frame selection

### Low Priority (Future Features)

7. **Mosaicing Support**
   - Multi-panel planning
   - Automated stitching
   - Distortion correction

8. **Advanced Stacking**
   - Frame-by-frame stacking with rejection
   - Drizzle integration
   - SNR optimization

9. **Full Automation**
   - Automatic startup sequence
   - Plate solving
   - Meridian flip handling
   - Weather monitoring

---

## 7. Technical Details

### Architecture

**Backend:**
- FastAPI (Python) - REST API
- SQLAlchemy - Database ORM
- Celery - Background job processing
- Redis - Job queue and caching
- Docker - Containerization

**Frontend:**
- Vanilla JavaScript (no framework)
- HTML5 + CSS3
- Fetch API for REST calls
- WebSockets potential for real-time updates

**Telescope Integration:**
- Custom TCP protocol client for Seestar S50
- Firmware v5.x support
- UDP discovery for guest mode
- JSON-based command/response

### Key Files

**Planning & Scheduling:**
- `backend/app/services/planner_service.py`
- `backend/app/services/targets_service.py`
- `backend/app/services/astronomy_service.py`

**Telescope Control:**
- `backend/app/clients/seestar_client.py`
- `backend/app/services/telescope_service.py`

**Processing:**
- `backend/app/api/processing.py`
- `backend/app/services/processing_service.py`
- `backend/app/services/direct_processor.py`

**Frontend:**
- `frontend/index.html` (monolithic, could be split)

**Documentation:**
- `PROCESSING_DESIGN.md` - Comprehensive processing design
- `SEESTAR_INTEGRATION.md` - Telescope integration guide
- `ROADMAP.md` - Future development plans

---

## 8. Answers to Your Questions

### Q1: Can I send the plan and it will handle startup/alignment?

**Answer:** No, not fully automatic.

**What you CAN do:**
- Generate a plan with the Planner
- Send the plan to the telescope for execution
- System will automatically slew, focus, and image each target
- System will park when done (if enabled)

**What you MUST do manually:**
- Power on the telescope
- Perform initial alignment (star alignment or plate solving)
- Make sure covers are off and conditions are good
- Then connect and execute

**Why:** The startup/alignment automation isn't implemented yet. This would be a good Phase 2 feature.

### Q2: Is there a way to capture calibration frames?

**Answer:** No, not currently.

**Status:** Calibration frame capture is not implemented. The processing pipeline has a placeholder for applying calibration frames, but there's no way to capture them through the Astro Planner interface.

**Workaround:** You would need to capture calibration frames manually using the Seestar app, then apply them using external tools like PixInsight or Siril.

**Future:** This would be a valuable addition. See the detailed requirements in Section 2 above.

### Q3: Do we know how to specify mosaicing and stacking?

**Answer:** Partially.

**Mosaicing:** Not implemented. No multi-panel support at all.

**Stacking:** Partial implementation
- Can process pre-stacked FITS from Seestar
- Basic histogram stretching
- Can't stack individual sub-frames
- Can't do rejection or advanced stacking

**For Awesome Images:**
You'll need to implement or integrate external tools for:
- Gradient removal
- Star reduction
- Advanced color processing
- Noise reduction
- Detail enhancement

See Section 3 for the full requirements.

---

## 9. Next Steps

### Immediate (This Week)
- ✅ Add upload progress indicator (DONE!)
- Test processing pipeline with real FITS files
- Document any bugs or issues
- Create user guide with current workflow

### Short Term (This Month)
- Add pre-flight checklist to execution UI
- Improve error messages and user feedback
- Add more processing presets
- Implement basic gradient removal

### Medium Term (Next Quarter)
- Add calibration frame capture
- Implement calibration library management
- Add star reduction to processing
- Improve session management UI

### Long Term (Next 6 Months)
- Add mosaicing support
- Implement advanced stacking
- Add startup/alignment automation
- Integrate weather monitoring

---

## Questions or Feedback?

This is a living document. As you use the system and discover issues or have ideas, update this document with your findings.

**Last Updated:** 2025-11-07
