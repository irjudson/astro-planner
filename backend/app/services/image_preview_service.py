"""Service for fetching and caching DSO preview images from SkyView."""

import os
from pathlib import Path
from typing import Optional

import httpx

from app.models.models import DSOTarget


class ImagePreviewService:
    """Service for managing DSO preview images."""

    def __init__(self):
        """Initialize with cache directory."""
        # Cache directory is mounted from host via Docker volume
        self.cache_dir = Path(os.getenv("IMAGE_CACHE_DIR", "/app/data/previews"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # SkyView base URL (Virtual Astronomer service)
        self.skyview_url = "https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl"

    def get_preview_url(self, target: DSOTarget) -> Optional[str]:
        """
        Get preview image URL for target (fetch if not cached).

        Args:
            target: DSO target

        Returns:
            Relative URL path to image, or None if unavailable
        """
        # Generate cache filename from catalog_id
        cache_filename = f"{self._sanitize_catalog_id(target.catalog_id)}.jpg"
        cache_path = self.cache_dir / cache_filename

        # Return cached image if exists
        if cache_path.exists():
            return f"/api/images/previews/{cache_filename}"

        # Attempt to fetch from SkyView
        try:
            image_data = self._fetch_from_skyview(target)
            if image_data:
                # Save to cache
                cache_path.write_bytes(image_data)
                return f"/api/images/previews/{cache_filename}"
        except Exception as e:
            print(f"Failed to fetch image for {target.catalog_id}: {e}")

        return None

    def _fetch_from_skyview(self, target: DSOTarget) -> Optional[bytes]:
        """
        Fetch image from SkyView Virtual Astronomer API.

        Args:
            target: DSO target

        Returns:
            Image bytes or None
        """
        # Convert RA/Dec to degrees
        ra_deg = target.ra_hours * 15.0
        dec_deg = target.dec_degrees

        # Calculate field of view (FOV) based on object size
        # Add padding around object (2x size, minimum 0.2 degrees)
        fov_deg = max(target.size_arcmin / 30.0, 0.2)  # arcmin to degrees with padding

        # SkyView query parameters
        params = {
            "Position": f"{ra_deg},{dec_deg}",
            "Survey": "DSS2 Red",  # Digital Sky Survey 2
            "Pixels": "300,300",  # Image size
            "Size": str(fov_deg),  # Field of view in degrees
            "Return": "JPEG",
            "Scaling": "Log",  # Better for faint objects
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.skyview_url, params=params)
                response.raise_for_status()

                # Check if response is actually an image
                content_type = response.headers.get("content-type", "")
                if "image" in content_type:
                    return response.content

        except Exception as e:
            print(f"SkyView fetch error for {target.catalog_id}: {e}")

        return None

    def _sanitize_catalog_id(self, catalog_id: str) -> str:
        """Sanitize catalog ID for use as filename."""
        # Replace special characters with underscores
        return catalog_id.replace(" ", "_").replace("/", "_").replace(":", "_")
