"""Direct FITS processing without Docker containers."""

import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from astropy.io import fits
from PIL import Image

logger = logging.getLogger(__name__)


class DirectProcessor:
    """Process FITS files directly without Docker."""

    def __init__(self):
        self.supported_formats = ["jpeg", "jpg", "tiff", "tif", "png"]

    def process_fits(self, input_file: Path, output_dir: Path, pipeline_steps: List[Dict[str, Any]]) -> List[Path]:
        """
        Process a FITS file through a pipeline.

        Args:
            input_file: Path to input FITS file
            output_dir: Directory for output files
            pipeline_steps: List of processing steps

        Returns:
            List of output file paths
        """
        logger.info(f"Processing {input_file} with {len(pipeline_steps)} steps")

        # Load FITS file
        data = self._load_fits(input_file)

        # Apply pipeline steps
        for step in pipeline_steps:
            step_name = step.get("step")
            params = step.get("params", {})

            if step_name == "histogram_stretch":
                data = self.histogram_stretch(data, **params)
            elif step_name == "export":
                return self.export_image(data, output_dir, input_file.stem, **params)
            else:
                logger.warning(f"Unknown processing step: {step_name}")

        # Default: export as JPEG
        return self.export_image(data, output_dir, input_file.stem, format="jpeg", quality=95)

    def _load_fits(self, fits_path: Path) -> np.ndarray:
        """Load FITS file and return image data."""
        logger.info(f"Loading FITS file: {fits_path}")

        with fits.open(fits_path) as hdul:
            # Get the primary HDU or first image HDU
            for hdu in hdul:
                if isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU)) and hdu.data is not None:
                    data = hdu.data
                    logger.info(f"Loaded FITS data: shape={data.shape}, dtype={data.dtype}")
                    return data.astype(np.float32)

        raise ValueError(f"No image data found in FITS file: {fits_path}")

    def histogram_stretch(
        self, data: np.ndarray, algorithm: str = "auto", midtones: float = 0.5, **kwargs
    ) -> np.ndarray:
        """Apply histogram stretch to image data."""
        logger.info(f"Applying histogram stretch: algorithm={algorithm}, midtones={midtones}")

        # Handle multi-channel images (RGB/color)
        if data.ndim == 3:
            # Process each channel separately
            stretched = np.zeros_like(data)
            for i in range(data.shape[0]):
                stretched[i] = self._stretch_channel(data[i], algorithm, midtones)
            return stretched
        else:
            return self._stretch_channel(data, algorithm, midtones)

    def _stretch_channel(self, channel: np.ndarray, algorithm: str, midtones: float) -> np.ndarray:
        """Stretch a single channel."""
        # Clip outliers (robust min/max)
        vmin, vmax = np.percentile(channel, [0.5, 99.5])

        # Normalize to 0-1
        stretched = np.clip((channel - vmin) / (vmax - vmin), 0, 1)

        if algorithm == "auto" or algorithm == "midtone":
            # Apply midtone transfer function
            # MTF formula: ((median - 1) * x) / ((2 * median - 1) * x - median)
            median = midtones
            if median != 0.5:
                stretched = ((median - 1) * stretched) / ((2 * median - 1) * stretched - median + 1e-10)
                stretched = np.clip(stretched, 0, 1)

        return stretched

    def export_image(
        self,
        data: np.ndarray,
        output_dir: Path,
        base_name: str,
        format: str = "jpeg",
        quality: int = 95,
        bit_depth: int = 8,
        compression: str = None,
        **kwargs,
    ) -> List[Path]:
        """Export processed data to image file."""
        format = format.lower()
        if format not in self.supported_formats:
            raise ValueError(f"Unsupported format: {format}. Supported: {self.supported_formats}")

        logger.info(f"Exporting to {format}: quality={quality}, bit_depth={bit_depth}")

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert to appropriate bit depth
        if bit_depth == 8:
            img_data = (data * 255).astype(np.uint8)
        elif bit_depth == 16:
            img_data = (data * 65535).astype(np.uint16)
        else:
            raise ValueError(f"Unsupported bit depth: {bit_depth}")

        # Handle different image dimensions
        if img_data.ndim == 3:
            # Multi-channel: convert to HxWxC for PIL
            if img_data.shape[0] == 3:  # CxHxW to HxWxC
                img_data = np.transpose(img_data, (1, 2, 0))
            mode = "RGB"
        elif img_data.ndim == 2:
            # Single channel grayscale
            mode = "L"
        else:
            raise ValueError(f"Unexpected image dimensions: {img_data.shape}")

        # Create PIL Image
        if bit_depth == 16:
            # PIL doesn't support 16-bit grayscale well, use 'I;16' for single channel
            if mode == "L":
                image = Image.fromarray(img_data, mode="I;16")
            else:
                # For RGB 16-bit, we need to use mode 'I' per channel or convert to 8-bit
                logger.warning("16-bit RGB export not fully supported, converting to 8-bit")
                img_data = (img_data / 256).astype(np.uint8)
                image = Image.fromarray(img_data, mode="RGB")
        else:
            image = Image.fromarray(img_data, mode=mode)

        # Determine file extension
        ext_map = {"jpeg": "jpg", "jpg": "jpg", "tiff": "tif", "tif": "tif", "png": "png"}
        ext = ext_map.get(format, format)
        output_file = output_dir / f"{base_name}.{ext}"

        # Save with appropriate parameters
        save_kwargs = {}
        if format in ["jpeg", "jpg"]:
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        elif format in ["tiff", "tif"]:
            if compression and compression != "none":
                save_kwargs["compression"] = compression
        elif format == "png":
            save_kwargs["optimize"] = True

        image.save(output_file, **save_kwargs)
        logger.info(f"Saved output to: {output_file}")

        return [output_file]
