"""Stacking service for combining multiple FITS sub-frames.

This service handles:
1. Loading multiple grayscale FITS sub-frames (Light_*.fit)
2. Debayering (converting Bayer pattern to RGB)
3. Stacking using sigma-clipped mean
4. Saving stacked FITS file in Seestar-compatible format
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from astropy.io import fits

logger = logging.getLogger(__name__)

# Try to import GPU-accelerated libraries
try:
    import cupy as cp

    HAS_CUPY = True
    logger.info("CuPy available - GPU acceleration enabled")
except ImportError:
    HAS_CUPY = False
    logger.info("CuPy not available - using CPU only")


@dataclass
class StackingResult:
    """Result of stacking operation."""

    stacked_file: Path
    num_frames: int
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]
    rejected_frames: int


class StackingService:
    """Service for stacking multiple FITS sub-frames."""

    def __init__(self, use_gpu: bool = True):
        """
        Initialize stacking service.

        Args:
            use_gpu: Whether to use GPU acceleration if available
        """
        self.use_gpu = use_gpu and HAS_CUPY
        if self.use_gpu:
            logger.info("GPU acceleration enabled")
        else:
            logger.info("Using CPU for stacking")

    def load_subframes(self, folder_path: Path, pattern: str = "Light_*.fit") -> List[np.ndarray]:
        """
        Load all matching sub-frames from a folder.

        Args:
            folder_path: Path to folder containing sub-frames
            pattern: Glob pattern to match files

        Returns:
            List of numpy arrays (grayscale images)
        """
        fits_files = sorted(folder_path.glob(pattern))

        if not fits_files:
            raise ValueError(f"No files matching '{pattern}' found in {folder_path}")

        logger.info(f"Loading {len(fits_files)} sub-frames from {folder_path}")

        frames = []
        for fits_file in fits_files:
            try:
                with fits.open(fits_file) as hdul:
                    data = hdul[0].data.astype(np.float32)
                    frames.append(data)
            except Exception as e:
                logger.warning(f"Failed to load {fits_file}: {e}")

        if not frames:
            raise ValueError("No frames could be loaded")

        logger.info(f"Loaded {len(frames)} frames, shape: {frames[0].shape}")
        return frames

    def debayer_rggb(self, bayer: np.ndarray) -> np.ndarray:
        """
        Debayer a Bayer pattern image (RGGB) to RGB using simple bilinear interpolation.

        The Seestar S50 uses an IMX462 sensor with RGGB Bayer pattern:
        R G R G ...
        G B G B ...
        R G R G ...
        ...

        Args:
            bayer: Grayscale Bayer pattern image (H, W)

        Returns:
            RGB image (3, H, W) in CHW format
        """
        from scipy.ndimage import convolve

        h, w = bayer.shape

        # Create full-resolution channel images
        r_full = np.zeros((h, w), dtype=np.float32)
        g_full = np.zeros((h, w), dtype=np.float32)
        b_full = np.zeros((h, w), dtype=np.float32)

        # Extract channels (RGGB pattern)
        r_full[0::2, 0::2] = bayer[0::2, 0::2]  # R at even rows, even cols
        g_full[0::2, 1::2] = bayer[0::2, 1::2]  # G at even rows, odd cols
        g_full[1::2, 0::2] = bayer[1::2, 0::2]  # G at odd rows, even cols
        b_full[1::2, 1::2] = bayer[1::2, 1::2]  # B at odd rows, odd cols

        # Simple bilinear interpolation kernels
        # For R and B (checkerboard pattern), use 3x3 kernel
        kernel_rb = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=np.float32) / 4

        # For G (two separate positions), use cross kernel
        kernel_g = np.array([[0, 1, 0], [1, 4, 1], [0, 1, 0]], dtype=np.float32) / 4

        # Interpolate each channel
        r_interp = convolve(r_full, kernel_rb, mode="nearest")
        g_interp = convolve(g_full, kernel_g, mode="nearest")
        b_interp = convolve(b_full, kernel_rb, mode="nearest")

        # Stack into RGB (CHW format to match Seestar)
        rgb = np.stack([r_interp, g_interp, b_interp], axis=0)

        return rgb

    def sigma_clip_stack(
        self, frames: List[np.ndarray], sigma: float = 2.5, max_iterations: int = 3
    ) -> Tuple[np.ndarray, int]:
        """
        Stack frames using sigma-clipped mean.

        This rejects outliers (cosmic rays, hot pixels, satellites) before stacking.

        Args:
            frames: List of frames to stack
            sigma: Sigma threshold for clipping
            max_iterations: Maximum iterations for sigma clipping

        Returns:
            Tuple of (stacked image, number of rejected pixels)
        """
        # Stack into 3D array (N, H, W)
        stack = np.stack(frames, axis=0)
        n_frames = stack.shape[0]

        logger.info(f"Sigma-clipping {n_frames} frames with sigma={sigma}")

        # Convert to GPU if available
        if self.use_gpu:
            stack_gpu = cp.asarray(stack)
        else:
            stack_gpu = stack

        # Iterative sigma clipping
        mask = np.ones_like(stack, dtype=bool)

        for iteration in range(max_iterations):
            # Calculate mean and std using unmasked values
            if self.use_gpu:
                mean = cp.ma.array(stack_gpu, mask=~cp.asarray(mask)).mean(axis=0).filled(0)
                std = cp.ma.array(stack_gpu, mask=~cp.asarray(mask)).std(axis=0).filled(1)

                # Find outliers
                diff = cp.abs(stack_gpu - mean[None, :, :])
                outliers = diff > (sigma * std[None, :, :])

                # Update mask
                mask_gpu = cp.asarray(mask)
                mask_gpu &= ~outliers
                mask = cp.asnumpy(mask_gpu)
            else:
                mean = np.ma.array(stack, mask=~mask).mean(axis=0).filled(0)
                std = np.ma.array(stack, mask=~mask).std(axis=0).filled(1)

                # Find outliers
                diff = np.abs(stack - mean[None, :, :])
                outliers = diff > (sigma * std[None, :, :])

                # Update mask
                mask &= ~outliers

            rejected = (~mask).sum()
            logger.info(f"Iteration {iteration + 1}: {rejected} pixels rejected")

        # Calculate final mean using mask
        if self.use_gpu:
            result = cp.ma.array(stack_gpu, mask=~cp.asarray(mask)).mean(axis=0).filled(0)
            result = cp.asnumpy(result)
        else:
            result = np.ma.array(stack, mask=~mask).mean(axis=0).filled(0)

        total_rejected = (~mask).sum()
        logger.info(f"Total rejected pixels: {total_rejected} / {mask.size} ({100 * total_rejected / mask.size:.2f}%)")

        return result.astype(np.float32), int(total_rejected)

    def save_stacked_fits(
        self, data: np.ndarray, output_path: Path, num_frames: int, original_header: Optional[fits.Header] = None
    ) -> None:
        """
        Save stacked image as FITS file.

        Args:
            data: RGB image data in CHW format (3, H, W)
            output_path: Output file path
            num_frames: Number of frames that were stacked
            original_header: Optional FITS header from one of the input files
        """
        # Create FITS header
        if original_header:
            header = original_header.copy()
        else:
            header = fits.Header()

        # Update/add relevant keywords
        header["CREATOR"] = "AstroPlanner"
        header["STACKED"] = num_frames
        header["COMMENT"] = f"Stacked from {num_frames} sub-frames"

        # Save as uint16 with BZERO offset (matching Seestar format)
        # Convert float32 [0, 65535] to uint16 with BZERO=32768
        data_uint16 = np.clip(data, 0, 65535).astype(np.uint16)

        # Create HDU and write
        hdu = fits.PrimaryHDU(data_uint16, header=header)
        hdu.writeto(output_path, overwrite=True)

        logger.info(f"Saved stacked FITS: {output_path}")

    def stack_folder(
        self,
        folder_path: Path,
        pattern: str = "Light_*.fit",
        output_path: Optional[Path] = None,
        sigma: float = 2.5,
    ) -> StackingResult:
        """
        Main entry point: stack all sub-frames in a folder.

        Args:
            folder_path: Path to folder containing Light_*.fit files
            pattern: Glob pattern for sub-frames
            output_path: Optional output path (auto-generated if None)
            sigma: Sigma threshold for clipping

        Returns:
            StackingResult with stacking information
        """
        logger.info(f"Stacking folder: {folder_path}")

        # Load sub-frames
        frames = self.load_subframes(folder_path, pattern)
        num_frames = len(frames)
        input_shape = frames[0].shape

        # Stack with sigma clipping
        stacked_gray, rejected = self.sigma_clip_stack(frames, sigma=sigma)

        # Debayer to RGB
        logger.info("Debayering to RGB")
        stacked_rgb = self.debayer_rggb(stacked_gray)
        output_shape = stacked_rgb.shape

        # Generate output path if not provided
        if output_path is None:
            # Extract object name from folder
            folder_name = folder_path.name
            if folder_name.endswith("_sub"):
                object_name = folder_name[:-4]  # Remove _sub suffix
            else:
                object_name = folder_name

            output_filename = f"Stacked_{num_frames}_{object_name}.fit"
            output_path = folder_path.parent / object_name / output_filename

            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load header from first frame
        first_file = sorted(folder_path.glob(pattern))[0]
        with fits.open(first_file) as hdul:
            original_header = hdul[0].header

        # Save stacked FITS
        self.save_stacked_fits(stacked_rgb, output_path, num_frames, original_header)

        return StackingResult(
            stacked_file=output_path,
            num_frames=num_frames,
            input_shape=input_shape,
            output_shape=output_shape,
            rejected_frames=rejected // (input_shape[0] * input_shape[1]),  # Approximate
        )
