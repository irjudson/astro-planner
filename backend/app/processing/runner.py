"""Processing pipeline runner (runs inside Docker container)."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from app.processing import gpu_ops

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineRunner:
    """Executes a processing pipeline."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.job_id = config["job_id"]
        self.input_file = config["input_file"]
        self.output_dir = Path(config["output_dir"])
        self.working_dir = Path(config["working_dir"])
        self.pipeline_steps = config["pipeline_steps"]

        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)

        # Check GPU availability
        gpu_info = gpu_ops.check_gpu_available()
        self.use_gpu = gpu_info.get("available", False)

        logger.info(f"Pipeline runner initialized for job {self.job_id}")
        logger.info(f"GPU available: {self.use_gpu}")
        if self.use_gpu:
            logger.info(f"GPU info: {gpu_info}")

    def run(self) -> Dict[str, Any]:
        """Execute the pipeline."""
        logger.info(f"Starting pipeline execution for job {self.job_id}")
        logger.info(f"Input file: {self.input_file}")
        logger.info(f"Pipeline steps: {len(self.pipeline_steps)}")

        current_file = self.input_file
        output_files = []

        try:
            for i, step in enumerate(self.pipeline_steps):
                step_name = step["step"]
                step_params = step.get("params", {})

                logger.info(f"Executing step {i+1}/{len(self.pipeline_steps)}: {step_name}")

                # Execute step
                if step_name == "histogram_stretch":
                    current_file = self._step_histogram_stretch(current_file, step_params)

                elif step_name == "export":
                    output_file = self._step_export(current_file, step_params)
                    output_files.append(output_file)

                else:
                    logger.warning(f"Unknown step: {step_name}")

            logger.info(f"Pipeline execution complete for job {self.job_id}")
            logger.info(f"Output files: {output_files}")

            return {
                "status": "success",
                "output_files": [str(f) for f in output_files]
            }

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }

    def _step_histogram_stretch(self, input_file: str, params: Dict[str, Any]) -> str:
        """Execute histogram stretch step."""
        output_file = self.working_dir / "stretched.fit"

        gpu_ops.histogram_stretch(
            input_path=input_file,
            output_path=str(output_file),
            params=params,
            use_gpu=self.use_gpu
        )

        return str(output_file)

    def _step_export(self, input_file: str, params: Dict[str, Any]) -> str:
        """Execute export step."""
        format_type = params.get("format", "jpeg").lower()

        if format_type == "jpeg":
            output_file = self.output_dir / "final.jpg"
        elif format_type == "tiff":
            output_file = self.output_dir / "final.tif"
        elif format_type == "png":
            output_file = self.output_dir / "final.png"
        else:
            output_file = self.output_dir / f"final.{format_type}"

        gpu_ops.export_image(
            input_path=input_file,
            output_path=str(output_file),
            params=params
        )

        return str(output_file)


def main():
    """Main entry point for pipeline runner."""
    parser = argparse.ArgumentParser(description="Process FITS files")
    parser.add_argument("--config", required=True, help="Path to job config JSON")
    args = parser.parse_args()

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = json.load(f)

    # Create runner and execute
    runner = PipelineRunner(config)
    result = runner.run()

    # Write result
    result_path = Path(config["output_dir"]) / "result.json"
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2)

    # Exit with appropriate code
    if result["status"] == "success":
        logger.info("Pipeline completed successfully")
        sys.exit(0)
    else:
        logger.error("Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
