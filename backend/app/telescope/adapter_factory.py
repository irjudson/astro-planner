"""
Telescope adapter factory.

Creates appropriate telescope adapter instances based on device configuration.
"""

from typing import Optional

from app.models.settings_models import SeestarDevice
from app.telescope.base_adapter import TelescopeAdapter
from app.telescope.seestar_adapter import SeestarAdapter


class AdapterFactory:
    """Factory for creating telescope adapter instances."""

    # Registry mapping device types to adapter classes
    _adapters = {
        "seestar": SeestarAdapter,
        # Future telescope types can be registered here:
        # "ascom": AscomAdapter,
        # "indi": IndiAdapter,
    }

    @classmethod
    def create_adapter(cls, device: SeestarDevice) -> TelescopeAdapter:
        """
        Create a telescope adapter for the given device.

        Args:
            device: Device configuration from database (SeestarDevice)

        Returns:
            Appropriate telescope adapter instance

        Raises:
            ValueError: If device type is not supported
        """
        # For now, we only support Seestar devices
        # When we add more telescope types, we'll need a device_type field
        device_type = "seestar"

        if device_type not in cls._adapters:
            supported = ", ".join(cls._adapters.keys())
            raise ValueError(f"Unsupported device type: {device_type}. Supported types: {supported}")

        adapter_class = cls._adapters[device_type]

        # Create adapter with device configuration
        return adapter_class(
            device_id=device.id,
            name=device.name,
            host=device.control_host,
            port=device.control_port or 4700,  # Default to 4700
        )

    @classmethod
    def register_adapter(cls, device_type: str, adapter_class: type):
        """
        Register a new adapter type.

        Args:
            device_type: Device type identifier (e.g., "seestar_s50")
            adapter_class: Adapter class implementing TelescopeAdapter
        """
        cls._adapters[device_type.lower()] = adapter_class

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """
        Get list of supported telescope types.

        Returns:
            List of supported device type identifiers
        """
        return list(cls._adapters.keys())
