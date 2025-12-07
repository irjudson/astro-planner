"""Auto-stretch service for processing stacked FITS files.

This service implements the arcsinh stretch algorithm reverse-engineered from Seestar,
with automatic parameter detection based on image content.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from astropy.io import fits
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class StretchParams:
    """Parameters for the stretch algorithm."""

    black_point: float
    white_point: float
    stretch_factor: float
    black_pct: float = 0.5
    white_pct: float = 99.95


@dataclass
class AutoProcessResult:
    """Result of auto-processing a FITS file."""

    output_files: List[Path]
    params: StretchParams
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]


class AutoStretchService:
    """Service for auto-stretching stacked FITS files to match Seestar output quality."""

    def __init__(self):
        self.supported_output_formats = ["jpg", "png", "tiff"]

    def load_fits(self, fits_path: Path) -> np.ndarray:
        """
        Load a FITS file and return image data in HWC format.

        Args:
            fits_path: Path to the FITS file

        Returns:
            numpy array with shape (H, W, C) as float64
        """
        logger.info(f"Loading FITS file: {fits_path}")

        with fits.open(fits_path) as hdul:
            for hdu in hdul:
                if isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU)) and hdu.data is not None:
                    data = hdu.data.astype(np.float64)
                    logger.info(f"Loaded FITS data: shape={data.shape}, dtype={data.dtype}")

                    # Convert to HWC format
                    if data.ndim == 3:
                        if data.shape[0] == 3:  # CHW -> HWC
                            data = np.transpose(data, (1, 2, 0))
                    elif data.ndim == 2:
                        # Grayscale -> RGB
                        data = np.stack([data, data, data], axis=-1)

                    return data

        raise ValueError(f"No image data found in FITS file: {fits_path}")

    def arcsinh_stretch(self, data: np.ndarray, a: float) -> np.ndarray:
        """
        Apply arcsinh stretch.

        This is the core stretch function used by Seestar:
        output = arcsinh(a * x) / arcsinh(a)

        Args:
            data: Normalized input data (0-1 range)
            a: Stretch factor (higher = more aggressive stretch)

        Returns:
            Stretched data in 0-1 range
        """
        return np.arcsinh(a * data) / np.arcsinh(a)

    def detect_stretch_params(self, data: np.ndarray) -> StretchParams:
        """
        Auto-detect optimal stretch parameters based on image statistics.

        The algorithm uses coefficient of variation (CV = std/mean) to determine
        the stretch factor:
        - High CV (>0.5): Sparse bright pixels (galaxies) -> higher stretch (a=20)
        - Medium CV (0.3-0.5): Mixed content -> medium stretch (a=10)
        - Low CV (<0.3): Diffuse structure (nebulae) -> lower stretch (a=5)

        Args:
            data: Input image data in HWC format

        Returns:
            StretchParams with detected values
        """
        # Fixed clip points that match Seestar
        black_pct = 0.5
        white_pct = 99.95

        # Calculate percentiles
        bp = np.percentile(data, black_pct)
        wp = np.percentile(data, white_pct)

        # Normalize for CV calculation
        normalized = np.clip((data - bp) / (wp - bp + 1e-10), 0, 1)

        # Calculate coefficient of variation
        cv = normalized.std() / (normalized.mean() + 1e-10)

        # Select stretch factor based on CV
        if cv > 0.5:
            a = 20  # Galaxy-like: sparse bright detail
        elif cv > 0.3:
            a = 10  # Mixed content
        else:
            a = 5  # Nebula-like: diffuse structure

        logger.info(f"Detected stretch params: CV={cv:.3f}, a={a}, black={bp:.1f}, white={wp:.1f}")

        return StretchParams(black_point=bp, white_point=wp, stretch_factor=a, black_pct=black_pct, white_pct=white_pct)

    def apply_stretch(self, data: np.ndarray, params: StretchParams) -> np.ndarray:
        """
        Apply stretch with given parameters.

        Args:
            data: Input image data in HWC format
            params: Stretch parameters

        Returns:
            Stretched data in 0-1 range
        """
        # Normalize using black/white points
        normalized = np.clip((data - params.black_point) / (params.white_point - params.black_point + 1e-10), 0, 1)

        # Apply arcsinh stretch
        stretched = self.arcsinh_stretch(normalized, params.stretch_factor)

        return stretched

    def save_outputs(self, data: np.ndarray, base_path: Path, formats: Optional[List[str]] = None) -> List[Path]:
        """
        Save stretched data to output files.

        Args:
            data: Stretched image data in 0-1 range, HWC format
            base_path: Base path for output files (without extension)
            formats: List of output formats (default: all supported)

        Returns:
            List of paths to saved files
        """
        if formats is None:
            formats = self.supported_output_formats

        output_files = []

        for fmt in formats:
            fmt = fmt.lower()
            if fmt not in self.supported_output_formats:
                logger.warning(f"Unsupported format: {fmt}")
                continue

            output_path = base_path.parent / f"{base_path.stem}_astroplanner.{fmt}"

            if fmt == "jpg":
                self._save_jpg(data, output_path)
            elif fmt == "png":
                self._save_png(data, output_path)
            elif fmt == "tiff":
                self._save_tiff(data, output_path)

            output_files.append(output_path)
            logger.info(f"Saved: {output_path}")

        return output_files

    def _save_jpg(self, data: np.ndarray, output_path: Path) -> None:
        """Save as JPEG (8-bit, 95% quality)."""
        img_data = (data * 255).astype(np.uint8)
        image = Image.fromarray(img_data, mode="RGB")
        image.save(output_path, quality=95, optimize=True)

    def _save_png(self, data: np.ndarray, output_path: Path) -> None:
        """Save as PNG (8-bit, lossless)."""
        img_data = (data * 255).astype(np.uint8)
        image = Image.fromarray(img_data, mode="RGB")
        image.save(output_path, optimize=True)

    def _save_tiff(self, data: np.ndarray, output_path: Path) -> None:
        """Save as TIFF (8-bit RGB, uncompressed).

        Note: True 16-bit RGB TIFF would require additional libraries like tifffile.
        For maximum compatibility, we save as high-quality 8-bit RGB.
        """
        # PIL has inconsistent support for 16-bit RGB across versions,
        # so we save as 8-bit RGB for cross-platform compatibility
        img_data = (data * 255).astype(np.uint8)
        image = Image.fromarray(img_data)
        image.save(output_path, compression=None)

    def auto_process(
        self, fits_path: Path, formats: Optional[List[str]] = None, params: Optional[StretchParams] = None
    ) -> AutoProcessResult:
        """
        Main entry point for auto-processing a FITS file.

        Args:
            fits_path: Path to input FITS file
            formats: Output formats (default: jpg, png, tiff)
            params: Optional manual stretch parameters (auto-detected if None)

        Returns:
            AutoProcessResult with output files and parameters used
        """
        logger.info(f"Auto-processing: {fits_path}")

        # Load FITS
        data = self.load_fits(fits_path)
        input_shape = data.shape

        # Detect or use provided parameters
        if params is None:
            params = self.detect_stretch_params(data)

        # Apply stretch
        stretched = self.apply_stretch(data, params)
        output_shape = stretched.shape

        # Save outputs
        if formats is None:
            formats = ["jpg", "png", "tiff"]

        output_files = self.save_outputs(stretched, fits_path, formats)

        return AutoProcessResult(
            output_files=output_files, params=params, input_shape=input_shape, output_shape=output_shape
        )

    def batch_process(
        self,
        folder_path: Path,
        pattern: str = "Stacked_*.fit",
        recursive: bool = True,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, AutoProcessResult]:
        """
        Process all matching FITS files in a folder.

        Args:
            folder_path: Path to folder containing FITS files
            pattern: Glob pattern to match files
            recursive: Whether to search recursively
            formats: Output formats for each file

        Returns:
            Dictionary mapping file paths to their processing results
        """
        results = {}

        if recursive:
            fits_files = list(folder_path.rglob(pattern))
        else:
            fits_files = list(folder_path.glob(pattern))

        logger.info(f"Found {len(fits_files)} files matching '{pattern}' in {folder_path}")

        for fits_file in fits_files:
            try:
                result = self.auto_process(fits_file, formats=formats)
                results[str(fits_file)] = result
            except Exception as e:
                logger.error(f"Error processing {fits_file}: {e}")
                results[str(fits_file)] = None

        return results
