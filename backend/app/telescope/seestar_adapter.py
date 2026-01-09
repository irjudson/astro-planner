"""
Seestar S-50 telescope adapter.

Wraps the SeestarClient to provide the generic telescope interface.
"""

from typing import Optional, Dict, Any
import logging

from app.telescope.base_adapter import (
    TelescopeAdapter,
    TelescopeStatus,
    TelescopeState,
    ExposureSettings,
)
from app.clients.seestar_client import SeestarClient, SeestarState

logger = logging.getLogger(__name__)


class SeestarAdapter(TelescopeAdapter):
    """Adapter for Seestar S-50 smart telescope."""

    def __init__(self, device_id: int, name: str, host: str, port: int = 4700):
        """
        Initialize Seestar adapter.

        Args:
            device_id: Database ID of the device
            name: Display name
            host: Hostname or IP (e.g., "seestar.local" or "192.168.2.47")
            port: Control port (default 4700)
        """
        super().__init__(device_id, name, host, port)
        self.client = SeestarClient()
        self._last_target_name: Optional[str] = None

    async def connect(self) -> bool:
        """Connect to Seestar telescope."""
        try:
            await self.client.connect(self.host, self.port)
            self._connected = self.client.connected
            logger.info(f"Connected to Seestar at {self.host}:{self.port}")
            return self._connected
        except Exception as e:
            logger.error(f"Failed to connect to Seestar: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Seestar telescope."""
        try:
            await self.client.disconnect()
            self._connected = False
            logger.info(f"Disconnected from Seestar at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect from Seestar: {e}")
            return False

    async def get_status(self) -> TelescopeStatus:
        """Get current Seestar status."""
        seestar_status = self.client.status

        # Map Seestar states to generic telescope states
        state_mapping = {
            SeestarState.DISCONNECTED: TelescopeState.DISCONNECTED,
            SeestarState.CONNECTED: TelescopeState.CONNECTED,
            SeestarState.SLEWING: TelescopeState.SLEWING,
            SeestarState.TRACKING: TelescopeState.TRACKING,
            SeestarState.FOCUSING: TelescopeState.SLEWING,  # Map focusing to slewing
            SeestarState.IMAGING: TelescopeState.EXPOSING,  # Map imaging to exposing
            SeestarState.PARKING: TelescopeState.SLEWING,  # Map parking to slewing
            SeestarState.PARKED: TelescopeState.PARKED,
            SeestarState.ERROR: TelescopeState.ERROR,
        }

        generic_state = state_mapping.get(seestar_status.state, TelescopeState.ERROR)

        return TelescopeStatus(
            connected=self.client.connected,
            state=generic_state,
            firmware_version=seestar_status.firmware_version,
            ra=seestar_status.current_ra_hours,
            dec=seestar_status.current_dec_degrees,
            alt=None,  # Seestar doesn't provide alt/az in status
            az=None,
            is_tracking=seestar_status.is_tracking,
            is_exposing=(generic_state == TelescopeState.EXPOSING),
            exposure_progress=None,  # Not available in current status
            temperature=None,  # Not available in current status
            error_message=seestar_status.last_error,
            extra={
                "current_target": seestar_status.current_target,
            },
        )

    async def goto(self, ra: float, dec: float, target_name: Optional[str] = None) -> bool:
        """Slew Seestar to target coordinates."""
        try:
            self._last_target_name = target_name
            success = await self.client.goto(ra, dec)
            if success:
                logger.info(f"Seestar slewing to {target_name or f'RA={ra}, Dec={dec}'}")
            return success
        except Exception as e:
            logger.error(f"Failed to slew Seestar: {e}")
            return False

    async def start_exposure(self, settings: ExposureSettings) -> bool:
        """Start exposure on Seestar."""
        try:
            # Seestar uses auto-exposure with stacking, so we adapt the settings
            success = await self.client.start_exposure(
                target_name=settings.target_name,
                ra=settings.ra,
                dec=settings.dec,
                exposure_time=settings.exposure_time,
                gain=settings.gain or 80,  # Default Seestar gain
                count=settings.count,
            )

            if success:
                logger.info(
                    f"Seestar started exposure: {settings.target_name} "
                    f"(RA={settings.ra}, Dec={settings.dec}, exp={settings.exposure_time}s)"
                )

            return success
        except Exception as e:
            logger.error(f"Failed to start Seestar exposure: {e}")
            return False

    async def stop_exposure(self) -> bool:
        """Stop current Seestar exposure."""
        try:
            success = await self.client.stop_exposure()
            if success:
                logger.info("Seestar exposure stopped")
            return success
        except Exception as e:
            logger.error(f"Failed to stop Seestar exposure: {e}")
            return False

    async def park(self) -> bool:
        """
        Park Seestar telescope.

        For Seestar, parking means moving to azimuth=0, altitude=0 (horizon).
        This is the safest stowed position for the telescope.
        """
        try:
            logger.info("Parking Seestar by moving to 0,0")
            # Move to azimuth=0, altitude=0 (horizon, north)
            success = await self.client.move_to_horizon(azimuth=0.0, altitude=0.0)
            if success:
                logger.info("Seestar parked at 0,0")
            return success
        except Exception as e:
            logger.error(f"Failed to park Seestar: {e}")
            return False

    async def unpark(self) -> bool:
        """
        Unpark/activate Seestar telescope.

        For Seestar, there's no explicit unpark command. Instead, we move the
        telescope to a good starting position (North, 60° altitude) which
        activates it and prepares it for observing.

        Returns:
            True if unpark/activation successful
        """
        try:
            logger.info("Unparking Seestar by moving to observing position")
            # Move to North at 60° altitude - a good starting position
            success = await self.client.move_to_horizon(azimuth=0.0, altitude=60.0)
            if success:
                logger.info("Seestar moved to observing position (unparked)")
            return success
        except Exception as e:
            logger.error(f"Failed to unpark Seestar: {e}")
            return False

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Report Seestar S-50 capabilities."""
        return {
            "goto": True,
            "tracking": True,
            "exposure": True,
            "park": True,
            "autofocus": True,  # Seestar has built-in autofocus
            "filter_wheel": False,  # No filter wheel
            "plate_solving": True,  # Seestar has plate solving
            "guiding": False,  # No separate guiding (built-in tracking)
            "stacking": True,  # Seestar-specific: live stacking
            "dew_heater": True,  # Seestar-specific: dew heater control
        }

    async def get_telescope_specific_data(self) -> Dict[str, Any]:
        """Get Seestar-specific data."""
        status = self.client.status
        return {
            "current_target": status.current_target,
            "firmware_version": status.firmware_version,
            "last_error": status.last_error,
            "last_update": status.last_update.isoformat() if status.last_update else None,
        }

    async def set_dew_heater(self, enabled: bool) -> bool:
        """
        Seestar-specific: Control dew heater.

        Args:
            enabled: True to turn on dew heater, False to turn off

        Returns:
            True if successful
        """
        try:
            success = await self.client.set_dew_heater(enabled)
            if success:
                logger.info(f"Seestar dew heater {'enabled' if enabled else 'disabled'}")
            return success
        except Exception as e:
            logger.error(f"Failed to set Seestar dew heater: {e}")
            return False

    async def get_stacked_image(self) -> Optional[bytes]:
        """
        Seestar-specific: Get the current stacked image.

        Returns:
            Image data as bytes, or None if not available
        """
        try:
            return await self.client.get_stacked_image()
        except Exception as e:
            logger.error(f"Failed to get Seestar stacked image: {e}")
            return None
