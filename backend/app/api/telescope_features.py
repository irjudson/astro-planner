"""
Telescope-specific features API.

Provides dynamic endpoints for telescope-specific functionality
that goes beyond the generic telescope interface.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_telescope
from app.clients.seestar_client import SeestarClient

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
async def get_telescope_capabilities(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """
    Get telescope capabilities and features.

    Returns a dict describing what features this telescope supports.
    """
    # Seestar S50 capabilities
    return {
        "telescope_type": "seestar",
        "model": "S50",
        "features": _get_seestar_features(),
    }


def _get_seestar_features() -> Dict[str, Any]:
    """Get available Seestar-specific features organized by category."""
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


# ==========================================
# Imaging Features
# ==========================================


@router.post("/imaging/exposure")
async def set_exposure_settings(
    request: ExposureSettingsRequest, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Set exposure settings (Seestar-specific)."""

    try:
        if request.exposure_ms is not None and request.gain is not None:
            success = await telescope.set_manual_exposure(request.exposure_ms, request.gain)
        elif request.stack_exposure_ms is not None:
            success = await telescope.set_exposure(request.stack_exposure_ms, request.continuous_exposure_ms or 500)
        else:
            raise HTTPException(status_code=400, detail="Must provide exposure_ms+gain or stack_exposure_ms")

        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/imaging/dither")
async def configure_dithering(
    request: DitherConfigRequest, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Configure dithering (Seestar-specific)."""

    try:
        success = await telescope.configure_dither(request.enabled, request.pixels, request.interval)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/imaging/autofocus")
async def start_autofocus(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Start autofocus (Seestar-specific)."""

    try:
        success = await telescope.auto_focus()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Focuser Features
# ==========================================


@router.post("/focuser/move")
async def move_focuser(
    request: FocuserMoveRequest, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Move focuser (Seestar-specific)."""

    try:
        if request.position is not None:
            success = await telescope.move_focuser_to_position(request.position)
        elif request.offset is not None:
            success = await telescope.move_focuser_relative(request.offset)
        else:
            raise HTTPException(status_code=400, detail="Must provide position or offset")

        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/focuser/factory-reset")
async def reset_focuser_factory(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Reset focuser to factory position (Seestar-specific)."""

    try:
        success = await telescope.reset_focuser_to_factory()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Hardware Features
# ==========================================


@router.post("/hardware/dew-heater")
async def control_dew_heater(
    request: DewHeaterRequest, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Control dew heater (Seestar-specific)."""

    try:
        success = await telescope.set_dew_heater(request.enabled, request.power_level)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hardware/dew-heater/status")
async def get_dew_heater_status(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Get dew heater status (Seestar-specific)."""

    try:
        # Get from device state
        state = await telescope.get_device_state(["dew_heater"])
        return state.get("dew_heater", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hardware/dc-output")
async def control_dc_output(
    request: DCOutputRequest, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Control DC output (Seestar-specific)."""

    try:
        # Use set_dc_output with appropriate config
        output_config = {"enabled": request.enabled}
        success = await telescope.set_dc_output(output_config)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# WiFi Features
# ==========================================


@router.get("/wifi/scan")
async def scan_wifi_networks(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Scan for WiFi networks (Seestar-specific)."""

    try:
        return await telescope.scan_wifi_networks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wifi/connect")
async def connect_to_wifi(
    request: WiFiConnectRequest, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Connect to WiFi network (Seestar-specific)."""

    try:
        success = await telescope.connect_to_wifi(request.ssid)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wifi/saved")
async def list_saved_wifi_networks(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """List saved WiFi networks (Seestar-specific)."""

    try:
        return await telescope.list_saved_wifi_networks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# System Features
# ==========================================


@router.get("/system/info")
async def get_system_info(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Get system information (Seestar-specific)."""

    try:
        pi_info = await telescope.get_pi_info()
        station_state = await telescope.get_station_state()
        return {
            "pi_info": pi_info,
            "station_state": station_state,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/location")
async def set_telescope_location(
    request: LocationRequest, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Set telescope location (Seestar-specific)."""

    try:
        success = await telescope.set_location(request.longitude, request.latitude)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/shutdown")
async def shutdown_telescope_endpoint(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Shutdown telescope device (Seestar-specific)."""

    try:
        success = await telescope.shutdown_telescope()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/reboot")
async def reboot_telescope_endpoint(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Reboot telescope device (Seestar-specific)."""

    try:
        success = await telescope.reboot_telescope()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/time")
async def get_pi_time(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Get system time from telescope."""
    try:
        time_info = await telescope.get_pi_time()
        return time_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/time")
async def set_pi_time(unix_timestamp: int, telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Set system time on telescope."""
    try:
        success = await telescope.set_pi_time(unix_timestamp)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/pi-info")
async def get_pi_info(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Get Raspberry Pi system information."""
    try:
        info = await telescope.get_pi_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# ADVANCED IMAGING SETTINGS
# ==========================================


@router.post("/imaging/advanced-stacking")
async def configure_advanced_stacking_endpoint(
    config: Dict[str, Any], telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Configure advanced stacking settings (DBE, star correction, etc.)."""
    try:
        success = await telescope.configure_advanced_stacking(**config)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/imaging/manual-exposure")
async def set_manual_exposure_endpoint(
    exposure_ms: float, gain: float, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Set manual exposure settings."""
    try:
        success = await telescope.set_manual_exposure(exposure_ms, gain)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/imaging/auto-exposure")
async def set_auto_exposure_endpoint(
    brightness_target: float = 50.0, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Set auto exposure with brightness target."""
    try:
        success = await telescope.set_auto_exposure(brightness_target)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/focuser/stop")
async def stop_autofocus_endpoint(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Stop autofocus operation."""
    try:
        success = await telescope.stop_autofocus()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# CALIBRATION
# ==========================================


@router.get("/calibration/polar-alignment")
async def check_polar_alignment(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Check polar alignment quality."""
    try:
        result = await telescope.check_polar_alignment()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calibration/polar-alignment/clear")
async def clear_polar_alignment(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Clear polar alignment data."""
    try:
        success = await telescope.clear_polar_alignment()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calibration/compass/start")
async def start_compass_calibration(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Start compass calibration routine."""
    try:
        success = await telescope.start_compass_calibration()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calibration/compass/stop")
async def stop_compass_calibration(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Stop compass calibration routine."""
    try:
        success = await telescope.stop_compass_calibration()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calibration/compass/state")
async def get_compass_state(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Get compass state and heading."""
    try:
        state = await telescope.get_compass_state()
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# MOVEMENT CONTROL
# ==========================================


@router.post("/movement/slew")
async def slew_to_coordinates(
    ra_hours: float, dec_degrees: float, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Slew to specific RA/Dec coordinates."""
    try:
        success = await telescope.slew_to_coordinates(ra_hours, dec_degrees)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/movement/stop")
async def stop_telescope_movement(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Stop all telescope movement."""
    try:
        success = await telescope.stop_telescope_movement()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/movement/horizon")
async def move_to_horizon(
    azimuth: float, altitude: float, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Move to horizon position (azimuth/altitude)."""
    try:
        success = await telescope.move_to_horizon(azimuth, altitude)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# IMAGE MANAGEMENT
# ==========================================


@router.get("/images/list")
async def list_images(
    image_type: str = "stacked", telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """List available images on telescope."""
    try:
        images = await telescope.list_images(image_type)
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/info")
async def get_image_info(
    file_path: str = "", telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Get image file information."""
    try:
        info = await telescope.get_image_file_info(file_path)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/download/{filename}")
async def download_image(filename: str, telescope: SeestarClient = Depends(get_current_telescope)):
    """Download stacked image from telescope."""
    try:
        from fastapi.responses import Response

        image_data = await telescope.get_stacked_image(filename)
        return Response(content=image_data, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/raw/{filename}")
async def download_raw_frame(filename: str, telescope: SeestarClient = Depends(get_current_telescope)):
    """Download raw frame from telescope."""
    try:
        from fastapi.responses import Response

        image_data = await telescope.get_raw_frame(filename)
        return Response(content=image_data, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/images/{filename}")
async def delete_image(filename: str, telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Delete image from telescope storage."""
    try:
        success = await telescope.delete_image(filename)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images/preview/live")
async def get_live_preview(telescope: SeestarClient = Depends(get_current_telescope)):
    """Get live preview frame from RTMP stream."""
    try:
        from fastapi.responses import Response

        image_data = await telescope.get_live_preview()
        return Response(content=image_data, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# WIFI & NETWORK MANAGEMENT
# ==========================================


@router.post("/wifi/enable-client")
async def enable_wifi_client_mode(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Enable WiFi client mode."""
    try:
        success = await telescope.enable_wifi_client_mode()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wifi/disable-client")
async def disable_wifi_client_mode(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Disable WiFi client mode."""
    try:
        success = await telescope.disable_wifi_client_mode()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wifi/save-network")
async def save_wifi_network(
    ssid: str, password: str, security: str = "WPA2-PSK", telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Save WiFi network credentials."""
    try:
        success = await telescope.save_wifi_network(ssid, password, security)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/wifi/network/{ssid}")
async def remove_wifi_network(ssid: str, telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Remove saved WiFi network."""
    try:
        success = await telescope.remove_wifi_network(ssid)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wifi/station-state")
async def get_station_state(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Get WiFi station connection state."""
    try:
        state = await telescope.get_station_state()
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wifi/access-point")
async def configure_access_point(
    ssid: str, password: str, is_5g: bool = True, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Configure WiFi access point."""
    try:
        success = await telescope.configure_access_point(ssid, password, is_5g)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wifi/country")
async def set_wifi_country(
    country_code: str, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Set WiFi regulatory domain."""
    try:
        success = await telescope.set_wifi_country(country_code)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# REMOTE SESSIONS
# ==========================================


@router.post("/remote/join")
async def join_remote_session(
    session_id: str = "", telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Join remote observation session."""
    try:
        success = await telescope.join_remote_session(session_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remote/leave")
async def leave_remote_session(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Leave remote observation session."""
    try:
        success = await telescope.leave_remote_session()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/remote/disconnect/{client_id}")
async def disconnect_remote_client(
    client_id: str, telescope: SeestarClient = Depends(get_current_telescope)
) -> Dict[str, Any]:
    """Disconnect a remote client."""
    try:
        success = await telescope.disconnect_remote_client(client_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# DEMO MODE
# ==========================================


@router.post("/demo/start")
async def start_demo_mode(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Start demonstration mode."""
    try:
        success = await telescope.start_demo_mode()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/stop")
async def stop_demo_mode(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Stop demonstration mode."""
    try:
        success = await telescope.stop_demo_mode()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# VERIFICATION
# ==========================================


@router.get("/verification/status")
async def check_client_verified(telescope: SeestarClient = Depends(get_current_telescope)) -> Dict[str, Any]:
    """Check if client is verified with telescope."""
    try:
        is_verified = await telescope.check_client_verified()
        return {"is_verified": is_verified}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
