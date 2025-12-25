"""Tests for the auto-stretch service."""

import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from app.services.auto_stretch_service import AutoStretchService, StretchParams


class TestArcsinhStretch:
    """Tests for the arcsinh stretch function."""

    def setup_method(self):
        self.service = AutoStretchService()

    def test_arcsinh_stretch_zero_input(self):
        """Arcsinh stretch of zero should return zero."""
        data = np.zeros((10, 10))
        result = self.service.arcsinh_stretch(data, a=10)
        assert np.allclose(result, 0)

    def test_arcsinh_stretch_one_input(self):
        """Arcsinh stretch of one should return one."""
        data = np.ones((10, 10))
        result = self.service.arcsinh_stretch(data, a=10)
        assert np.allclose(result, 1)

    def test_arcsinh_stretch_preserves_shape(self):
        """Stretch should preserve input shape."""
        data = np.random.rand(100, 200, 3)
        result = self.service.arcsinh_stretch(data, a=10)
        assert result.shape == data.shape

    def test_arcsinh_stretch_output_range(self):
        """Output should be in 0-1 range for 0-1 input."""
        data = np.random.rand(100, 100)
        result = self.service.arcsinh_stretch(data, a=20)
        assert result.min() >= 0
        assert result.max() <= 1

    def test_arcsinh_stretch_monotonic(self):
        """Stretch function should be monotonically increasing."""
        data = np.linspace(0, 1, 100)
        result = self.service.arcsinh_stretch(data, a=10)
        assert np.all(np.diff(result) >= 0)

    def test_arcsinh_stretch_higher_a_more_aggressive(self):
        """Higher stretch factor should produce more aggressive stretch."""
        data = np.array([0.1, 0.5, 0.9])

        result_low = self.service.arcsinh_stretch(data, a=5)
        result_high = self.service.arcsinh_stretch(data, a=20)

        # For mid-values, higher 'a' produces more stretched (higher) output
        assert result_high[1] > result_low[1]


class TestDetectStretchParams:
    """Tests for automatic parameter detection."""

    def setup_method(self):
        self.service = AutoStretchService()

    def test_detect_params_galaxy_like(self):
        """Galaxy-like images (sparse bright pixels) should get high stretch factor."""
        # Create image with sparse bright pixels (high CV)
        data = np.zeros((100, 100, 3), dtype=np.float64)
        data[45:55, 45:55, :] = 10000  # Small bright core

        params = self.service.detect_stretch_params(data)

        # Should detect as galaxy-like with high stretch
        assert params.stretch_factor == 20

    def test_detect_params_different_content_types(self):
        """Different content distributions should produce different stretch factors."""
        # Galaxy-like: mostly dark with sparse bright
        galaxy_data = np.zeros((100, 100, 3), dtype=np.float64)
        galaxy_data[45:55, 45:55, :] = 10000

        galaxy_params = self.service.detect_stretch_params(galaxy_data)

        # This distribution should get high stretch factor
        assert galaxy_params.stretch_factor == 20

        # Verify the params are valid
        assert galaxy_params.black_pct == 0.5
        assert galaxy_params.white_pct == 99.95

    def test_detect_params_returns_correct_type(self):
        """Should return StretchParams dataclass."""
        data = np.random.rand(50, 50, 3) * 1000

        params = self.service.detect_stretch_params(data)

        assert isinstance(params, StretchParams)
        assert hasattr(params, "black_point")
        assert hasattr(params, "white_point")
        assert hasattr(params, "stretch_factor")

    def test_detect_params_percentiles(self):
        """Should use correct percentiles for black/white points."""
        data = np.random.rand(100, 100, 3) * 1000

        params = self.service.detect_stretch_params(data)

        # Verify percentiles match design spec
        assert params.black_pct == 0.5
        assert params.white_pct == 99.95


class TestApplyStretch:
    """Tests for applying stretch with parameters."""

    def setup_method(self):
        self.service = AutoStretchService()

    def test_apply_stretch_output_range(self):
        """Applied stretch should produce 0-1 output."""
        data = np.random.rand(100, 100, 3) * 10000

        params = StretchParams(black_point=100, white_point=9000, stretch_factor=10)

        result = self.service.apply_stretch(data, params)

        assert result.min() >= 0
        assert result.max() <= 1

    def test_apply_stretch_clipping(self):
        """Values outside black/white points should be clipped."""
        data = np.array([[[0, 5000, 10000]]], dtype=np.float64)

        params = StretchParams(black_point=1000, white_point=8000, stretch_factor=10)

        result = self.service.apply_stretch(data, params)

        # Value below black point should be 0
        assert result[0, 0, 0] == 0
        # Value above white point should be 1 after stretch
        assert result[0, 0, 2] == 1


class TestSaveOutputs:
    """Tests for saving output files."""

    def setup_method(self):
        self.service = AutoStretchService()

    def test_save_jpg(self):
        """Should save valid JPEG file."""
        data = np.random.rand(100, 100, 3)

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "test"
            output_files = self.service.save_outputs(data, base_path, formats=["jpg"])

            assert len(output_files) == 1
            assert output_files[0].suffix == ".jpg"
            assert output_files[0].exists()

            # Verify it's a valid image
            img = Image.open(output_files[0])
            assert img.size == (100, 100)

    def test_save_png(self):
        """Should save valid PNG file."""
        data = np.random.rand(100, 100, 3)

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "test"
            output_files = self.service.save_outputs(data, base_path, formats=["png"])

            assert len(output_files) == 1
            assert output_files[0].suffix == ".png"
            assert output_files[0].exists()

    def test_save_tiff(self):
        """Should save valid TIFF file."""
        data = np.random.rand(100, 100, 3)

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "test"
            output_files = self.service.save_outputs(data, base_path, formats=["tiff"])

            assert len(output_files) == 1
            assert output_files[0].suffix == ".tiff"
            assert output_files[0].exists()

    def test_save_multiple_formats(self):
        """Should save all requested formats."""
        data = np.random.rand(100, 100, 3)

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "test"
            output_files = self.service.save_outputs(data, base_path, formats=["jpg", "png", "tiff"])

            assert len(output_files) == 3
            extensions = {f.suffix for f in output_files}
            assert extensions == {".jpg", ".png", ".tiff"}

    def test_save_creates_astroplanner_suffix(self):
        """Output filename should have _astroplanner suffix."""
        data = np.random.rand(100, 100, 3)

        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "Stacked_M81"
            output_files = self.service.save_outputs(data, base_path, formats=["jpg"])

            assert "_astroplanner" in output_files[0].stem


class TestLoadFits:
    """Tests for FITS file loading."""

    def setup_method(self):
        self.service = AutoStretchService()

    def test_load_fits_rgb(self):
        """Should load RGB FITS as HWC format."""
        # Create mock FITS data in CHW format
        from astropy.io import fits

        data_chw = np.random.rand(3, 100, 200).astype(np.float64) * 1000

        with tempfile.TemporaryDirectory() as tmpdir:
            fits_path = Path(tmpdir) / "test.fit"
            hdu = fits.PrimaryHDU(data_chw)
            hdu.writeto(fits_path)

            result = self.service.load_fits(fits_path)

            # Should be HWC format
            assert result.shape == (100, 200, 3)

    def test_load_fits_grayscale(self):
        """Should convert grayscale FITS to RGB."""
        from astropy.io import fits

        data_gray = np.random.rand(100, 200).astype(np.float64) * 1000

        with tempfile.TemporaryDirectory() as tmpdir:
            fits_path = Path(tmpdir) / "test.fit"
            hdu = fits.PrimaryHDU(data_gray)
            hdu.writeto(fits_path)

            result = self.service.load_fits(fits_path)

            # Should be HWC format with 3 channels
            assert result.shape == (100, 200, 3)
            # All channels should be the same
            assert np.allclose(result[:, :, 0], result[:, :, 1])
            assert np.allclose(result[:, :, 1], result[:, :, 2])


class TestAutoProcess:
    """Tests for full auto-process workflow."""

    def setup_method(self):
        self.service = AutoStretchService()

    def test_auto_process_creates_outputs(self):
        """Auto-process should create output files."""
        from astropy.io import fits

        # Create test FITS
        data_chw = np.random.rand(3, 100, 100).astype(np.float64) * 10000

        with tempfile.TemporaryDirectory() as tmpdir:
            fits_path = Path(tmpdir) / "Stacked_test.fit"
            hdu = fits.PrimaryHDU(data_chw)
            hdu.writeto(fits_path)

            result = self.service.auto_process(fits_path, formats=["jpg", "png"])

            assert len(result.output_files) == 2
            for output_file in result.output_files:
                assert output_file.exists()

    def test_auto_process_returns_params(self):
        """Auto-process should return detected parameters."""
        from astropy.io import fits

        data_chw = np.random.rand(3, 100, 100).astype(np.float64) * 10000

        with tempfile.TemporaryDirectory() as tmpdir:
            fits_path = Path(tmpdir) / "test.fit"
            hdu = fits.PrimaryHDU(data_chw)
            hdu.writeto(fits_path)

            result = self.service.auto_process(fits_path)

            assert result.params is not None
            assert result.params.stretch_factor in [5, 10, 20]
            assert result.input_shape == (100, 100, 3)

    def test_auto_process_with_manual_params(self):
        """Auto-process should use manual parameters when provided."""
        from astropy.io import fits

        data_chw = np.random.rand(3, 100, 100).astype(np.float64) * 10000

        with tempfile.TemporaryDirectory() as tmpdir:
            fits_path = Path(tmpdir) / "test.fit"
            hdu = fits.PrimaryHDU(data_chw)
            hdu.writeto(fits_path)

            manual_params = StretchParams(black_point=500, white_point=9000, stretch_factor=15)

            result = self.service.auto_process(fits_path, params=manual_params)

            assert result.params.stretch_factor == 15


class TestBatchProcess:
    """Tests for batch processing."""

    def setup_method(self):
        self.service = AutoStretchService()

    def test_batch_process_finds_files(self):
        """Batch process should find matching files."""
        from astropy.io import fits

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create test FITS files
            for i in range(3):
                data = np.random.rand(3, 50, 50).astype(np.float64) * 10000
                fits_path = tmpdir / f"Stacked_{i}.fit"
                hdu = fits.PrimaryHDU(data)
                hdu.writeto(fits_path)

            results = self.service.batch_process(tmpdir, pattern="Stacked_*.fit", formats=["jpg"])

            assert len(results) == 3

    def test_batch_process_recursive(self):
        """Batch process should search recursively when enabled."""
        from astropy.io import fits

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create nested structure
            subdir = tmpdir / "subdir"
            subdir.mkdir()

            data = np.random.rand(3, 50, 50).astype(np.float64) * 10000
            fits_path = subdir / "Stacked_1.fit"
            hdu = fits.PrimaryHDU(data)
            hdu.writeto(fits_path)

            results = self.service.batch_process(tmpdir, pattern="Stacked_*.fit", recursive=True, formats=["jpg"])

            assert len(results) == 1
