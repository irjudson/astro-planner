# Processing UX Redesign

## Current Problems

1. **Sessions are unnecessary** - Files are already on disk, why create a session?
2. **Upload is redundant** - We're importing from local filesystem, not uploading
3. **Preset names are unclear**:
   - "Quick DSO" - What does this do?
   - "Export for PixInsight" - Why would I use this?
4. **Missing the real workflow** - Neither preset does proper calibration/stacking

## Proposed New UX

### Simple File Browser + Process

```
┌─────────────────────────────────────────────┐
│  Process FITS Files                         │
├─────────────────────────────────────────────┤
│                                             │
│  📁 Browse Files: /fits/M31/                │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ ☐ Light_001.fits        4.2 MB       │ │
│  │ ☐ Light_002.fits        4.2 MB       │ │
│  │ ☐ Light_003.fits        4.1 MB       │ │
│  │ ✓ Light_004_stacked.fits   8.5 MB   │ │ <- Selected
│  └───────────────────────────────────────┘ │
│                                             │
│  What do you want to do?                    │
│                                             │
│  ○ Quick Preview (Auto-stretch to JPEG)    │
│     Fast preview for sharing/social media   │
│                                             │
│  ○ Export for Editing (16-bit TIFF)        │
│     Open in PixInsight, Photoshop, GIMP    │
│                                             │
│  ○ Stack Multiple Lights (Coming Soon)     │
│     Combine multiple exposures              │
│                                             │
│  ○ Full Calibration (Coming Soon)          │
│     Dark/Flat/Bias + Stack + Stretch        │
│                                             │
│  [ Process Selected Files ]                 │
│                                             │
└─────────────────────────────────────────────┘
```

### Processing Options - Clear & Descriptive

| Option | What it does | When to use | Output |
|--------|--------------|-------------|--------|
| **Quick Preview** | Auto-stretch + JPEG | Sharing on social media, quick look | JPEG (8-bit, compressed) |
| **Export for Editing** | Minimal processing, preserves data | Opening in PixInsight/Photoshop | TIFF (16-bit, uncompressed) |
| **Stack Multiple Lights** | Combine exposures, sigma clipping | Multiple subs of same target | FITS (32-bit float) |
| **Full Calibration** | Dark/Flat/Bias + Stack + Stretch | Proper workflow from raw subs | FITS + JPEG |

### File Selection

**Option 1: Direct file picker**
- Browse local filesystem
- Multi-select
- No "session" concept

**Option 2: Scan directory**
- Point to object directory (e.g., `/fits/M31/`)
- Auto-detect file types (Light_*.fits, Dark_*.fits, etc.)
- One-click workflow

## Simplified API

### Old (Session-based):
```
POST /api/process/sessions          # Create session
POST /api/process/sessions/1/upload # Upload file
POST /api/process/sessions/1/finalize
POST /api/process/sessions/1/process {"pipeline_name": "quick_dso"}
GET  /api/process/jobs/1
GET  /api/process/jobs/1/download
```

### New (Direct):
```
POST /api/process/quick-preview
{
  "files": ["/fits/M31/Light_004_stacked.fits"]
}
→ Returns job_id, polls for completion

POST /api/process/export-for-editing
{
  "files": ["/fits/M31/Light_004_stacked.fits"],
  "bit_depth": 16,
  "format": "tiff"
}

POST /api/process/stack
{
  "light_frames": ["/fits/M31/Light_001.fits", ...],
  "dark_frames": [...],  # optional
  "flat_frames": [...],  # optional
  "method": "sigma_clip"
}

GET /api/process/jobs/{job_id}/status
GET /api/process/jobs/{job_id}/result
```

## Implementation Plan

### Phase 1: Simplify Current (Quick Win)

1. **Remove session requirement**
   - Add `/api/process/file` endpoint
   - Takes file path + processing type
   - Returns job_id immediately

2. **Rename presets to be clear**
   - "Quick DSO" → "Quick Preview"
   - "Export PixInsight" → "Export for Editing"

3. **Update UI**
   - Remove "Create Session" step
   - Direct file browser
   - Clear descriptions of each option

### Phase 2: Add Real Workflows (Future)

4. **Stack Multiple Lights**
   - Alignment
   - Sigma clipping rejection
   - Output calibrated stack

5. **Full Calibration Pipeline**
   - Master dark/flat/bias
   - Calibrate lights
   - Stack
   - Auto-stretch
   - Output both FITS + JPEG

## UI Mockup - Simplified

```html
<div class="process-tab">
  <h2>Process FITS Files</h2>

  <!-- File Browser -->
  <div class="file-browser">
    <label>Select FITS file:</label>
    <button onclick="browseFiles()">Browse...</button>
    <div id="selected-file"></div>
  </div>

  <!-- Processing Options -->
  <div class="processing-options">
    <h3>What do you want to do?</h3>

    <label class="option-card">
      <input type="radio" name="process-type" value="quick-preview" checked>
      <div class="option-content">
        <h4>📸 Quick Preview</h4>
        <p>Auto-stretch and export to JPEG</p>
        <small>Best for: Sharing, social media, quick look</small>
        <small>Output: JPEG (8-bit, 95% quality)</small>
      </div>
    </label>

    <label class="option-card">
      <input type="radio" name="process-type" value="export-editing">
      <div class="option-content">
        <h4>🎨 Export for Editing</h4>
        <p>Preserve all data for post-processing</p>
        <small>Best for: PixInsight, Photoshop, GIMP</small>
        <small>Output: TIFF (16-bit, uncompressed)</small>
      </div>
    </label>

    <label class="option-card disabled">
      <div class="option-content">
        <h4>📚 Stack Multiple Lights</h4>
        <p>Combine multiple exposures with rejection</p>
        <small>Coming soon in v2.0</small>
      </div>
    </label>

    <label class="option-card disabled">
      <div class="option-content">
        <h4>⚙️ Full Calibration Pipeline</h4>
        <p>Dark/Flat/Bias + Stack + Stretch</p>
        <small>Coming soon in v2.0</small>
      </div>
    </label>
  </div>

  <button onclick="startProcessing()" class="primary">
    Process File
  </button>

  <!-- Progress -->
  <div id="processing-status" style="display:none">
    <div class="progress-bar">
      <div id="progress" style="width:0%"></div>
    </div>
    <p id="status-text">Processing...</p>
  </div>

  <!-- Result -->
  <div id="result" style="display:none">
    <h3>✓ Processing Complete!</h3>
    <img id="result-preview" />
    <button onclick="downloadResult()">Download Result</button>
  </div>
</div>
```

## Key Improvements

1. ✅ **No sessions** - Direct file → process → result
2. ✅ **Clear option names** - Users know what each does
3. ✅ **Descriptions** - Explain use case and output format
4. ✅ **Visual preview** - Show result inline
5. ✅ **Future-ready** - Disabled options show what's coming

## Migration Strategy

### Keep Backward Compatibility
- Keep old session API for now (deprecated)
- Add new direct processing API
- Update UI to use new API
- Remove old API in v2.0

### Database Changes
- Sessions become optional
- Jobs can exist without sessions
- Add `source_file_path` to ProcessingJob
