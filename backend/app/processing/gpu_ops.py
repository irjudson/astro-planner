"""GPU-accelerated image processing operations."""

import logging
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Try to import GPU libraries
try:
    import cupy as cp

    GPU_AVAILABLE = True
    logger.info("CuPy (GPU) available")
except ImportError:
    GPU_AVAILABLE = False
    logger.info("CuPy not available, falling back to CPU")

try:
    from astropy.io import fits
except ImportError:
    fits = None
    logger.warning("Astropy not available")


def check_gpu_available() -> Dict[str, Any]:
    """Check if GPU is available and return info."""
    if not GPU_AVAILABLE:
        return {"available": False, "error": "CuPy not installed"}

    try:
        gpu_count = cp.cuda.runtime.getDeviceCount()

        gpu_info = []
        for i in range(gpu_count):
            cp.cuda.Device(i)
            props = cp.cuda.runtime.getDeviceProperties(i)

            gpu_info.append(
                {
                    "id": i,
                    "name": props["name"].decode(),
                    "memory_gb": props["totalGlobalMem"] / 1e9,
                    "compute_capability": f"{props['major']}.{props['minor']}",
                }
            )

        return {"available": True, "count": gpu_count, "devices": gpu_info}
    except Exception as e:
        return {"available": False, "error": str(e)}


def load_fits(fits_path: str) -> Tuple[np.ndarray, Any]:
    """Load FITS file and return data and header."""
    if fits is None:
        raise ImportError("Astropy is required to load FITS files")

    with fits.open(fits_path) as hdul:
        data = hdul[0].data.astype(np.float32)
        header = hdul[0].header

    return data, header


def save_fits(fits_path: str, data: np.ndarray, header: Any):
    """Save data to FITS file."""
    if fits is None:
        raise ImportError("Astropy is required to save FITS files")

    fits.writeto(fits_path, data, header, overwrite=True)


def gpu_histogram_stretch(input_path: str, output_path: str, params: Dict[str, Any]) -> str:
    """
    GPU-accelerated histogram stretch using CuPy.
    10-50x faster than CPU for large FITS files.
    """
    logger.info(f"GPU histogram stretch: {input_path} -> {output_path}")

    # Load FITS to CPU
    data, header = load_fits(input_path)

    # Transfer to GPU
    gpu_data = cp.asarray(data)

    # Calculate percentiles on GPU (much faster)
    if params.get("algorithm") == "auto":
        black_point = float(cp.percentile(gpu_data, 0.1))
        white_point = float(cp.percentile(gpu_data, 99.9))
    else:
        black_point = params.get("black_point", 0)
        white_point = params.get("white_point", 65535)

    logger.info(f"Stretch points: black={black_point}, white={white_point}")

    # Apply stretch on GPU
    gpu_stretched = cp.clip((gpu_data - black_point) / (white_point - black_point), 0, 1)

    # Apply midtones transfer function
    midtones = params.get("midtones", 0.5)
    if midtones != 0.5:
        gpu_stretched = mtf_gpu(gpu_stretched, midtones)

    # Transfer back to CPU
    stretched = cp.asnumpy(gpu_stretched)

    # Save result
    save_fits(output_path, stretched, header)

    return output_path


def cpu_histogram_stretch(input_path: str, output_path: str, params: Dict[str, Any]) -> str:
    """CPU fallback for histogram stretch."""
    logger.info(f"CPU histogram stretch: {input_path} -> {output_path}")

    # Load FITS
    data, header = load_fits(input_path)

    # Calculate percentiles on CPU
    if params.get("algorithm") == "auto":
        black_point = float(np.percentile(data, 0.1))
        white_point = float(np.percentile(data, 99.9))
    else:
        black_point = params.get("black_point", 0)
        white_point = params.get("white_point", 65535)

    logger.info(f"Stretch points: black={black_point}, white={white_point}")

    # Apply stretch
    stretched = np.clip((data - black_point) / (white_point - black_point), 0, 1)

    # Apply midtones transfer function
    midtones = params.get("midtones", 0.5)
    if midtones != 0.5:
        stretched = mtf_cpu(stretched, midtones)

    # Save result
    save_fits(output_path, stretched, header)

    return output_path


def mtf_gpu(data_gpu, midtones: float):
    """Midtones Transfer Function on GPU."""
    return (midtones - 1) * data_gpu / ((2 * midtones - 1) * data_gpu - midtones)


def mtf_cpu(data: np.ndarray, midtones: float) -> np.ndarray:
    """Midtones Transfer Function on CPU."""
    return (midtones - 1) * data / ((2 * midtones - 1) * data - midtones)


def histogram_stretch(input_path: str, output_path: str, params: Dict[str, Any], use_gpu: bool = True) -> str:
    """
    Histogram stretch with automatic GPU/CPU selection.
    """
    if use_gpu and GPU_AVAILABLE:
        try:
            return gpu_histogram_stretch(input_path, output_path, params)
        except Exception as e:
            logger.warning(f"GPU processing failed: {e}. Falling back to CPU.")
            return cpu_histogram_stretch(input_path, output_path, params)
    else:
        return cpu_histogram_stretch(input_path, output_path, params)


def export_image(input_path: str, output_path: str, params: Dict[str, Any]) -> str:
    """
    Export FITS to JPEG/TIFF/PNG.
    """
    logger.info(f"Exporting image: {input_path} -> {output_path}")

    # Load FITS
    data, header = load_fits(input_path)

    # Normalize to 0-255 for 8-bit output or 0-65535 for 16-bit
    bit_depth = params.get("bit_depth", 8)

    if bit_depth == 8:
        # 8-bit output
        data_scaled = (data * 255).astype(np.uint8)
    else:
        # 16-bit output
        data_scaled = (data * 65535).astype(np.uint16)

    # Save using PIL/imageio
    from PIL import Image

    # Handle multi-dimensional data (assume last two dims are image)
    if data_scaled.ndim > 2:
        data_scaled = data_scaled[-1]

    img = Image.fromarray(data_scaled)

    # Get format from output path
    output_format = Path(output_path).suffix[1:].upper()
    if output_format == "JPG":
        output_format = "JPEG"

    quality = params.get("quality", 95)

    if output_format == "JPEG":
        img.save(output_path, format=output_format, quality=quality)
    else:
        img.save(output_path, format=output_format)

    logger.info(f"Exported to {output_path}")
    return output_path
