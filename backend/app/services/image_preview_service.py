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
        Fetch color image from multiple sources (SDSS, Pan-STARRS, then SkyView).

        Tries sources in order:
        1. SDSS - best color images for northern sky
        2. Pan-STARRS - good color images for most of sky
        3. SkyView DSS - grayscale fallback

        Args:
            target: DSO target

        Returns:
            Image bytes or None
        """
        # Convert RA/Dec to degrees
        ra_deg = target.ra_hours * 15.0
        dec_deg = target.dec_degrees

        # Calculate field of view in arcminutes (with padding)
        fov_arcmin = max(target.size_arcmin * 2.0, 12.0)  # At least 12 arcmin

        # Try SDSS first (best color images, but limited coverage)
        image_data = self._fetch_from_sdss(ra_deg, dec_deg, fov_arcmin)
        if image_data:
            print(f"Fetched {target.catalog_id} from SDSS")
            return image_data

        # Try Pan-STARRS second (wider coverage, good quality)
        image_data = self._fetch_from_panstarrs(ra_deg, dec_deg, fov_arcmin)
        if image_data:
            print(f"Fetched {target.catalog_id} from Pan-STARRS")
            return image_data

        # Fallback to SkyView DSS2 (grayscale but always available)
        print(f"Using SkyView DSS fallback for {target.catalog_id}")
        return self._fetch_from_skyview_dss(ra_deg, dec_deg, fov_arcmin)

    def _fetch_from_sdss(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> Optional[bytes]:
        """Fetch color image from SDSS DR17."""
        # SDSS Image Cutout Service
        # Scale: 0.396 arcsec/pixel (Native SDSS resolution)
        # Convert FOV to pixels
        pixels = int(fov_arcmin * 60 / 0.396)
        pixels = min(pixels, 2048)  # Max size

        url = "https://skyserver.sdss.org/dr17/SkyServerWS/ImgCutout/getjpeg"
        params = {
            "ra": ra_deg,
            "dec": dec_deg,
            "width": pixels,
            "height": pixels,
            "scale": 0.4,  # arcsec/pixel
        }

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url, params=params)
                if response.status_code == 200 and len(response.content) > 1000:
                    # SDSS returns a small image even for out-of-bounds, check size
                    return response.content
        except Exception as e:
            print(f"SDSS fetch error: {e}")
        return None

    def _fetch_from_panstarrs(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> Optional[bytes]:
        """Fetch color image from Pan-STARRS via PS1 image service."""
        # PS1 Image Cutout Service
        # Size in pixels (0.25 arcsec/pixel)
        pixels = int(fov_arcmin * 60 / 0.25)
        pixels = min(pixels, 2400)  # Max size

        # Use PS1 color image service (gri composite)
        url = "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi"
        params = {
            "ra": ra_deg,
            "dec": dec_deg,
            "size": pixels,
            "format": "jpg",
            "color": True,  # RGB composite
        }

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url, params=params)
                if response.status_code == 200 and "image" in response.headers.get("content-type", ""):
                    return response.content
        except Exception as e:
            print(f"Pan-STARRS fetch error: {e}")
        return None

    def _fetch_from_skyview_dss(self, ra_deg: float, dec_deg: float, fov_arcmin: float) -> Optional[bytes]:
        """Fetch grayscale image from SkyView DSS2 (fallback)."""
        fov_deg = fov_arcmin / 60.0

        params = {
            "Position": f"{ra_deg},{dec_deg}",
            "Survey": "DSS2 Red",
            "Pixels": "300,300",
            "Size": str(fov_deg),
            "Return": "JPEG",
            "Scaling": "Log",
        }

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(self.skyview_url, params=params)
                response.raise_for_status()
                if "image" in response.headers.get("content-type", ""):
                    return response.content
        except Exception as e:
            print(f"SkyView DSS fetch error: {e}")
        return None

    def _sanitize_catalog_id(self, catalog_id: str) -> str:
        """Sanitize catalog ID for use as filename."""
        # Replace special characters with underscores
        return catalog_id.replace(" ", "_").replace("/", "_").replace(":", "_")
