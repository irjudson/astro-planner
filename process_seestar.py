#!/usr/bin/env python3
"""
One-button Seestar post-processing tool.

This script provides a simple command-line interface to process Seestar images
with the same stretch algorithm that Seestar uses internally.

Usage:
    # Process an already-stacked FITS file (from M81/, M31_mosaic/, etc.)
    python process_seestar.py /mnt/seestar-s50/MyWorks/M81/Stacked_34_M81_10.0s_IRCUT_20251115-190922.fit

    # Process all stacked files in a directory
    python process_seestar.py /mnt/seestar-s50/MyWorks/M81/

    # Stack sub-frames and stretch (from M81_sub/, M31_mosaic_sub/, etc.)
    python process_seestar.py /mnt/seestar-s50/MyWorks/M81_sub/ --stack

Options:
    --stack         Stack Light_*.fit sub-frames before stretching
    --sigma SIGMA   Sigma threshold for stacking (default: 2.5)
    --format FMT    Output format: jpg, png, or tiff (default: jpg)
    --output DIR    Output directory (default: current directory)
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.auto_stretch_service import AutoStretchService
from app.services.stacking_service import StackingService


def process_stacked_file(fits_path: Path, output_dir: Path, formats: list):
    """Process an already-stacked FITS file."""
    print(f"Processing: {fits_path.name}")

    service = AutoStretchService()
    result = service.auto_process(fits_path, formats=formats, output_dir=output_dir)

    for output_file in result.output_files:
        print(f"  → {output_file}")

    print(f"  Stretch factor: {result.params.stretch_factor}")
    print(f"  Black point: {result.params.black_point:.1f}")
    print(f"  White point: {result.params.white_point:.1f}")


def process_sub_frames(folder_path: Path, output_dir: Path, formats: list, sigma: float):
    """Stack sub-frames and stretch."""
    print(f"Stacking and processing: {folder_path.name}")

    # Step 1: Stack
    print("  [1/2] Stacking sub-frames...")
    stacking_service = StackingService(use_gpu=True)

    # Create temporary stacked file in output directory
    stacked_file = output_dir / f"Stacked_{folder_path.name}.fit"
    stack_result = stacking_service.stack_folder(folder_path, output_path=stacked_file, sigma=sigma)

    print(f"    Stacked {stack_result.num_frames} frames")
    print(f"    Rejected ~{stack_result.rejected_frames} outlier frames")

    # Step 2: Auto-stretch
    print("  [2/2] Auto-stretching...")
    stretch_service = AutoStretchService()
    stretch_result = stretch_service.auto_process(stack_result.stacked_file, formats=formats)

    print(f"    Stretch factor: {stretch_result.params.stretch_factor}")

    for output_file in stretch_result.output_files:
        print(f"  → {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="One-button Seestar post-processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("path", type=Path, help="FITS file or directory to process")
    parser.add_argument("--stack", action="store_true", help="Stack Light_*.fit sub-frames")
    parser.add_argument("--sigma", type=float, default=2.5, help="Sigma threshold for stacking (default: 2.5)")
    parser.add_argument("--format", dest="formats", action="append", choices=["jpg", "png", "tiff"],
                        help="Output format (can specify multiple times)")
    parser.add_argument("--output", type=Path, help="Output directory (default: same as input)")

    args = parser.parse_args()

    # Validate input path
    if not args.path.exists():
        print(f"Error: Path not found: {args.path}", file=sys.stderr)
        return 1

    # Default format
    if not args.formats:
        args.formats = ["jpg"]

    # Default output directory
    if args.output is None:
        if args.path.is_file():
            args.output = args.path.parent
        else:
            args.output = Path.cwd()

    # Create output directory if it doesn't exist
    args.output.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Seestar Post-Processing")
    print("=" * 80)

    try:
        if args.stack:
            # Stack sub-frames mode
            if not args.path.is_dir():
                print("Error: --stack requires a directory path", file=sys.stderr)
                return 1

            process_sub_frames(args.path, args.output, args.formats, args.sigma)

        elif args.path.is_file():
            # Single file mode
            process_stacked_file(args.path, args.output, args.formats)

        elif args.path.is_dir():
            # Directory mode - process all stacked files
            fits_files = list(args.path.glob("Stacked_*.fit"))

            if not fits_files:
                print(f"No Stacked_*.fit files found in {args.path}", file=sys.stderr)
                print("Tip: Use --stack to process Light_*.fit sub-frames", file=sys.stderr)
                return 1

            print(f"Found {len(fits_files)} stacked FITS files\n")

            for fits_file in fits_files:
                process_stacked_file(fits_file, args.output, args.formats)
                print()

        print("=" * 80)
        print("✓ Processing complete!")
        print("=" * 80)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
