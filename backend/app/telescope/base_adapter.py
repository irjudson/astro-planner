"""
Base telescope adapter interface.

This defines the generic API that all telescope adapters must implement,
regardless of the underlying telescope hardware or control protocol.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class TelescopeState(Enum):
    """Generic telescope states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SLEWING = "slewing"
    TRACKING = "tracking"
    EXPOSING = "exposing"
    ERROR = "error"
    PARKED = "parked"


@dataclass
class TelescopeStatus:
    """Generic telescope status information."""
    connected: bool
    state: TelescopeState
    firmware_version: Optional[str] = None
    ra: Optional[float] = None  # Right ascension in degrees
    dec: Optional[float] = None  # Declination in degrees
    alt: Optional[float] = None  # Altitude in degrees
    az: Optional[float] = None  # Azimuth in degrees
    is_tracking: bool = False
    is_exposing: bool = False
    exposure_progress: Optional[float] = None  # 0.0 to 1.0
    temperature: Optional[float] = None  # Sensor temperature in Celsius
    error_message: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None  # Telescope-specific data


@dataclass
class ExposureSettings:
    """Settings for an exposure."""
    target_name: str
    ra: float  # degrees
    dec: float  # degrees
    exposure_time: int  # seconds
    gain: Optional[int] = None
    binning: Optional[int] = None
    filter_name: Optional[str] = None
    count: int = 1  # Number of exposures to take
    dither: bool = False


class TelescopeAdapter(ABC):
    """
    Abstract base class for telescope adapters.

    All telescope-specific clients must implement this interface to provide
    a consistent API for the application.
    """

    def __init__(self, device_id: int, name: str, host: str, port: int):
        """
        Initialize the adapter.

        Args:
            device_id: Database ID of the device
            name: Display name of the telescope
            host: Hostname or IP address
            port: Control port
        """
        self.device_id = device_id
        self.name = name
        self.host = host
        self.port = port
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the telescope.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the telescope.

        Returns:
            True if disconnection successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_status(self) -> TelescopeStatus:
        """
        Get current telescope status.

        Returns:
            Current telescope status
        """
        pass

    @abstractmethod
    async def goto(self, ra: float, dec: float, target_name: Optional[str] = None) -> bool:
        """
        Slew telescope to target coordinates.

        Args:
            ra: Right ascension in degrees
            dec: Declination in degrees
            target_name: Optional name of the target

        Returns:
            True if slew successful, False otherwise
        """
        pass

    @abstractmethod
    async def start_exposure(self, settings: ExposureSettings) -> bool:
        """
        Start an exposure.

        Args:
            settings: Exposure settings

        Returns:
            True if exposure started successfully, False otherwise
        """
        pass

    @abstractmethod
    async def stop_exposure(self) -> bool:
        """
        Stop current exposure.

        Returns:
            True if exposure stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    async def park(self) -> bool:
        """
        Park the telescope in a safe position.

        Returns:
            True if parked successfully, False otherwise
        """
        pass

    @property
    def connected(self) -> bool:
        """Check if telescope is connected."""
        return self._connected

    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Report telescope capabilities.

        Override this to specify which features are supported.

        Returns:
            Dictionary of capability flags
        """
        return {
            "goto": True,
            "tracking": True,
            "exposure": True,
            "park": True,
            "autofocus": False,
            "filter_wheel": False,
            "plate_solving": False,
            "guiding": False,
        }

    async def get_telescope_specific_data(self) -> Dict[str, Any]:
        """
        Get telescope-specific data that doesn't fit the generic interface.

        Override this to provide additional telescope-specific information.

        Returns:
            Dictionary of telescope-specific data
        """
        return {}
