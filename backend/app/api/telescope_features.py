"""
Telescope-specific features API.

Provides dynamic endpoints for telescope-specific functionality
that goes beyond the generic telescope adapter interface.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.api.deps import get_current_telescope
from app.telescope.base_adapter import TelescopeAdapter
from app.telescope.seestar_adapter import SeestarAdapter

router = APIRouter()


# ==========================================
# Request Models
# ==========================================

class DewHeaterRequest(BaseModel):
    """Request to control dew heater."""
    enabled: bool
    power_level: int = 90


class DCOutputRequest(BaseModel):
    """Request to control DC output."""
    enabled: bool


class FocuserMoveRequest(BaseModel):
    """Request to move focuser."""
    position: Optional[int] = None
    offset: Optional[int] = None


class ExposureSettingsRequest(BaseModel):
    """Request to set exposure settings."""
    exposure_ms: Optional[float] = None
    gain: Optional[float] = None
    stack_exposure_ms: Optional[int] = None
    continuous_exposure_ms: Optional[int] = None


class DitherConfigRequest(BaseModel):
    """Request to configure dithering."""
    enabled: bool = True
    pixels: int = 50
    interval: int = 10


class WiFiConnectRequest(BaseModel):
    """Request to connect to WiFi."""
    ssid: str
    password: Optional[str] = None


class WiFiSaveRequest(BaseModel):
    """Request to save WiFi network."""
    ssid: str
    password: str
    security: str = "WPA2-PSK"


class LocationRequest(BaseModel):
    """Request to set telescope location."""
    latitude: float
    longitude: float


class HorizonMoveRequest(BaseModel):
    """Request to move to horizon coordinates."""
    azimuth: float
    altitude: float


# ==========================================
# Seestar-Specific Endpoints
# ==========================================

@router.get("/capabilities")
async def get_telescope_capabilities(
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """
    Get telescope capabilities and features.

    Returns a dict describing what features this telescope supports.
    """
    base_capabilities = telescope.capabilities

    # Add telescope type
    telescope_type = type(telescope).__name__.replace("Adapter", "").lower()

    return {
        "telescope_type": telescope_type,
        "capabilities": base_capabilities,
        "features": await _get_telescope_features(telescope),
    }


async def _get_telescope_features(telescope: TelescopeAdapter) -> Dict[str, Any]:
    """Get available telescope-specific features organized by category."""

    if isinstance(telescope, SeestarAdapter):
        return {
            "imaging": {
                "manual_exposure": True,
                "auto_exposure": True,
                "dithering": True,
                "advanced_stacking": True,
            },
            "focuser": {
                "absolute_move": True,
                "relative_move": True,
                "autofocus": True,
                "stop_autofocus": True,
                "factory_reset": True,
            },
            "hardware": {
                "dew_heater": True,
                "dc_output": True,
                "temperature_sensor": False,  # Not in current status
            },
            "alignment": {
                "polar_alignment_check": True,
                "polar_alignment_clear": True,
                "compass_calibration": True,
            },
            "wifi": {
                "scan_networks": True,
                "connect": True,
                "save_network": True,
                "list_saved": True,
                "remove_network": True,
                "ap_mode_config": True,
                "client_mode_toggle": True,
            },
            "system": {
                "shutdown": True,
                "reboot": True,
                "set_time": True,
                "get_info": True,
                "notification_sound": True,
            },
            "advanced": {
                "remote_sessions": True,
                "demo_mode": True,
                "view_plan": True,
                "planet_scan": True,
            },
        }

    # Default: no extra features
    return {}


# ==========================================
# Imaging Features
# ==========================================

@router.post("/imaging/exposure")
async def set_exposure_settings(
    request: ExposureSettingsRequest,
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Set exposure settings (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        if request.exposure_ms is not None and request.gain is not None:
            success = await telescope.client.set_manual_exposure(
                request.exposure_ms,
                request.gain
            )
        elif request.stack_exposure_ms is not None:
            success = await telescope.client.set_exposure(
                request.stack_exposure_ms,
                request.continuous_exposure_ms or 500
            )
        else:
            raise HTTPException(status_code=400, detail="Must provide exposure_ms+gain or stack_exposure_ms")

        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/imaging/dither")
async def configure_dithering(
    request: DitherConfigRequest,
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Configure dithering (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        success = await telescope.client.configure_dither(
            request.enabled,
            request.pixels,
            request.interval
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/imaging/autofocus")
async def start_autofocus(
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Start autofocus (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        success = await telescope.client.auto_focus()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Focuser Features
# ==========================================

@router.post("/focuser/move")
async def move_focuser(
    request: FocuserMoveRequest,
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Move focuser (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        if request.position is not None:
            success = await telescope.client.move_focuser_to_position(request.position)
        elif request.offset is not None:
            success = await telescope.client.move_focuser_relative(request.offset)
        else:
            raise HTTPException(status_code=400, detail="Must provide position or offset")

        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/focuser/factory-reset")
async def reset_focuser_factory(
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Reset focuser to factory position (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        success = await telescope.client.reset_focuser_to_factory()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Hardware Features
# ==========================================

@router.post("/hardware/dew-heater")
async def control_dew_heater(
    request: DewHeaterRequest,
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Control dew heater (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        success = await telescope.client.set_dew_heater(
            request.enabled,
            request.power_level
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hardware/dew-heater/status")
async def get_dew_heater_status(
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Get dew heater status (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        # Get from device state
        state = await telescope.client.get_device_state(['dew_heater'])
        return state.get('dew_heater', {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hardware/dc-output")
async def control_dc_output(
    request: DCOutputRequest,
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Control DC output (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        # Use set_dc_output with appropriate config
        output_config = {"enabled": request.enabled}
        success = await telescope.client.set_dc_output(output_config)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# WiFi Features
# ==========================================

@router.get("/wifi/scan")
async def scan_wifi_networks(
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Scan for WiFi networks (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        return await telescope.client.scan_wifi_networks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wifi/connect")
async def connect_to_wifi(
    request: WiFiConnectRequest,
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Connect to WiFi network (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        success = await telescope.client.connect_to_wifi(request.ssid)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wifi/saved")
async def list_saved_wifi_networks(
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """List saved WiFi networks (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        return await telescope.client.list_saved_wifi_networks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# System Features
# ==========================================

@router.get("/system/info")
async def get_system_info(
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Get system information (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        pi_info = await telescope.client.get_pi_info()
        station_state = await telescope.client.get_station_state()
        return {
            "pi_info": pi_info,
            "station_state": station_state,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/location")
async def set_telescope_location(
    request: LocationRequest,
    telescope: TelescopeAdapter = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Set telescope location (Seestar-specific)."""
    if not isinstance(telescope, SeestarAdapter):
        raise HTTPException(status_code=400, detail="Not supported by this telescope")

    try:
        success = await telescope.client.set_location(
            request.longitude,
            request.latitude
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
