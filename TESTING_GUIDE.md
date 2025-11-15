# Testing Guide for Astro Planner

## Overview
This document describes how to test the Astro Planner system to ensure it's functioning correctly.

---

## Quick Health Check

### 1. Check Services are Running

```bash
docker-compose ps
```

You should see:
- ✅ `astro-planner` - Main API (port 9247)
- ✅ `astro-planner-celery` - Background worker
- ✅ `astro-planner-redis` - Task queue

All should show status `Up` and be healthy.

### 2. API Health Check

```bash
curl http://localhost:9247/api/health | python3 -m json.tool
```

Expected output:
```json
{
  "status": "healthy",
  "service": "astro-planner-api",
  "version": "1.0.0",
  "telescope_connected": false
}
```

### 3. Check Docker-in-Docker

Verify both containers have Docker CLI:

```bash
# Main API container
docker exec astro-planner docker --version

# Celery worker container
docker exec astro-planner-celery docker --version
```

Both should return: `Docker version 28.5.2, build ecc6942` (or similar)

---

## Processing Pipeline Test

### Automated Test Script

The easiest way to test the complete processing pipeline:

```bash
# Install requirements
pip install astropy requests numpy

# Run the test
python test_processing.py
```

This script will:
1. ✅ Check API health
2. 📸 Create synthetic star field FITS file
3. 📁 Create processing session
4. 📤 Upload FITS file
5. ⚙️  Start processing job
6. ⏳ Monitor progress
7. 📥 Download result
8. ✅ Verify success

**Expected output:**
```
============================================================
🧪 Astro Planner Processing Pipeline Test
============================================================

🏥 Checking API health...
✓ API is healthy: {'status': 'healthy', ...}

📸 Creating synthetic star field...
✓ Created test FITS: /tmp/tmpXXXX.fits
  Size: 1024x1024 pixels
  Stars: 100
  File size: 4.19 MB

📁 Creating processing session...
✓ Created session: test_session_1699401234 (ID: 1)

📤 Uploading FITS file...
✓ Uploaded: tmpXXXX.fits (4.19 MB)

✅ Finalizing session...
✓ Session finalized and ready for processing

⚙️  Starting processing with preset 'quick_dso'...
✓ Processing job started (ID: 1)

⏳ Monitoring job progress (timeout: 120s)...
  ⏸️ PENDING: 0.0% -
  🔄 RUNNING: 25.0% - Loading FITS file
  🔄 RUNNING: 50.0% - Applying histogram stretch
  🔄 RUNNING: 75.0% - Exporting to JPEG
  🔄 RUNNING: 100.0% - Complete

✅ Processing completed successfully!
   Output: /fits/sessions/1/result.jpg

📥 Downloading result...
✓ Downloaded: result.jpg (245.3 KB)

============================================================
✅ ALL TESTS PASSED!
============================================================

📄 Result saved to: result.jpg
```

---

## Manual Testing via UI

### 1. Open Web Interface

```bash
open http://localhost:9247
# or visit in browser
```

### 2. Test Processing Tab

1. Click **"Process"** tab
2. Create a new session:
   - Enter session name: `manual_test_001`
   - Click **"Create Session"**
3. Upload a FITS file:
   - Drag and drop or click to browse
   - Watch upload progress bar
   - Should see ✓ with file name when complete
4. Click a processing preset button:
   - **"Quick DSO"** for fast auto-stretch
   - **"PixInsight Export"** for 16-bit TIFF
5. Monitor job progress:
   - Progress bar updates every 2 seconds
   - Shows current step
   - GPU badge if GPU used
6. Download result when complete:
   - Click **"📥 Download Result"** button
   - Image opens or downloads

---

## Unit Tests

### Run Backend Tests

```bash
cd backend
pytest tests/ -v
```

### Run Specific Test Suites

```bash
# Processing tests only
pytest tests/test_processing_integration.py -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Verbose output with print statements
pytest tests/ -v -s
```

### Test Coverage

Expected coverage:
- Processing pipeline: >80%
- Direct processor: >90%
- API endpoints: >70%
- Astronomy services: >85%

---

## Integration Tests

### 1. Test Planner

```bash
curl -X POST http://localhost:9247/api/planner/plan \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-11-15",
    "location": {
      "latitude": 45.9183,
      "longitude": -111.5433,
      "elevation": 1234
    },
    "target_preferences": {
      "target_type": "dso",
      "min_altitude": 30
    }
  }' | python3 -m json.tool
```

Should return scheduled targets with rise/set times.

### 2. Test Weather API

```bash
curl http://localhost:9247/api/weather/current | python3 -m json.tool
```

Should return current weather conditions (if API key configured).

### 3. Test Target Search

```bash
curl "http://localhost:9247/api/targets/search?query=M31&limit=5" | python3 -m json.tool
```

Should return Andromeda Galaxy and similar targets.

---

## Performance Tests

### Processing Performance

Test with various file sizes:

```bash
# Small file (512x512)
python test_processing.py  # ~5-10 seconds

# Medium file (1024x1024)
# Modify script to create larger image

# Large file (2048x2048)
# Should complete in <60 seconds
```

### Concurrent Jobs

Test multiple jobs running simultaneously:

```python
# Create multiple sessions and start jobs
for i in range(5):
    # Create session
    # Upload file
    # Start processing

# All should complete successfully
```

---

## Troubleshooting Tests

### Processing Job Fails

**Check celery worker logs:**
```bash
docker-compose logs -f celery-worker
```

**Common issues:**

1. **"Docker is not available"**
   - Solution: Rebuild celery-worker
   ```bash
   docker-compose build celery-worker
   docker-compose up -d celery-worker
   ```

2. **"File not found"**
   - Check FITS_DIR volume mount
   - Verify file was uploaded successfully

3. **"Memory error"**
   - Increase Docker memory limit
   - Process smaller files first

### API Not Responding

**Check main API logs:**
```bash
docker-compose logs -f astro-planner
```

**Restart services:**
```bash
docker-compose restart
```

### Database Issues

**Reset database:**
```bash
docker-compose down
rm -rf data/*.db
docker-compose up -d
```

### Port Already in Use

**Find what's using port 9247:**
```bash
lsof -i :9247
```

**Kill native processes:**
```bash
./scripts/docker-clean.sh
```

---

## Continuous Testing

### Set Up Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Run tests before commit

echo "Running tests..."
cd backend
pytest tests/ -v

if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi

echo "All tests passed!"
exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

### GitHub Actions (Future)

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11

    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
        pip install -r backend/requirements-test.txt

    - name: Run tests
      run: |
        cd backend
        pytest tests/ -v --cov=app

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## Test Data

### Synthetic FITS Files

The `test_processing.py` script creates synthetic star fields. You can also create custom test data:

```python
from astropy.io import fits
import numpy as np

# Create test image
data = np.random.poisson(lam=100, size=(1024, 1024)).astype(np.float32)

# Add gradient (to test gradient removal)
y, x = np.ogrid[0:1024, 0:1024]
gradient = (y / 1024) * 500
data += gradient

# Add stars
# ... (see test_processing.py for star generation code)

# Save
hdu = fits.PrimaryHDU(data=data)
hdu.header['OBJECT'] = 'Test with Gradient'
hdu.writeto('test_gradient.fits', overwrite=True)
```

### Real Data

For testing with real Seestar S50 data:

1. Capture images with Seestar S50 app
2. Export FITS files
3. Copy to `fits/` directory
4. Upload via web UI or test script

---

## Regression Testing

### Baseline Images

Keep a set of baseline processed images to detect regressions:

```bash
# Process baseline image
python test_processing.py

# Save result as baseline
cp result.jpg baselines/test_001_baseline.jpg

# On future changes, compare
python test_processing.py
compare result.jpg baselines/test_001_baseline.jpg -metric RMSE diff.png
```

### Expected Metrics

Track key metrics:
- Processing time: <30s for 1024x1024 image
- Output file size: 200-300 KB for JPEG
- Memory usage: <2GB per job
- Success rate: >95%

---

## Periodic Health Checks

### Daily Checks

```bash
# Check API health
curl http://localhost:9247/api/health

# Check disk space
df -h data/
df -h fits/

# Check logs for errors
docker-compose logs --tail=100 | grep ERROR
```

### Weekly Checks

```bash
# Run full test suite
pytest backend/tests/ -v

# Check database size
ls -lh data/*.db

# Clean old processed files
find fits/sessions/ -type f -mtime +30 -delete
```

### Monthly Checks

```bash
# Update dependencies
pip list --outdated

# Check Docker image sizes
docker images | grep astro-planner

# Review and archive old sessions
```

---

## Test Checklist

Before releasing changes:

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Manual UI testing complete
- [ ] Processing pipeline tested with real data
- [ ] Memory usage acceptable
- [ ] No error logs during testing
- [ ] Documentation updated
- [ ] Changelog updated

---

## Getting Help

If tests fail:

1. Check logs: `docker-compose logs`
2. Verify Docker setup: `docker-compose ps`
3. Review error messages carefully
4. Check TESTING_GUIDE.md troubleshooting section
5. Open issue on GitHub with:
   - Test output
   - Logs
   - System info (`docker version`, `python --version`)
   - Steps to reproduce

---

## Summary

**Quick daily test:**
```bash
python test_processing.py
```

**Full test suite:**
```bash
pytest backend/tests/ -v
```

**System health:**
```bash
docker-compose ps
curl http://localhost:9247/api/health
```

Keep testing regularly to catch issues early!

**Last Updated:** 2025-11-07
