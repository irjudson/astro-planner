"""User preferences API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.settings_models import AppSetting

router = APIRouter()


class UserPreferences(BaseModel):
    """User preferences model."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    units: str = "metric"
    default_device_id: Optional[int] = None


@router.get("/preferences", response_model=UserPreferences)
def get_user_preferences(db: Session = Depends(get_db)):
    """Get user preferences from database."""
    prefs = UserPreferences()

    # Load each preference from database
    lat_setting = db.query(AppSetting).filter(AppSetting.key == "user.latitude").first()
    if lat_setting:
        prefs.latitude = float(lat_setting.value)

    lon_setting = db.query(AppSetting).filter(AppSetting.key == "user.longitude").first()
    if lon_setting:
        prefs.longitude = float(lon_setting.value)

    elev_setting = db.query(AppSetting).filter(AppSetting.key == "user.elevation").first()
    if elev_setting:
        prefs.elevation = float(elev_setting.value)

    units_setting = db.query(AppSetting).filter(AppSetting.key == "user.units").first()
    if units_setting:
        prefs.units = units_setting.value

    device_setting = db.query(AppSetting).filter(AppSetting.key == "user.default_device_id").first()
    if device_setting:
        prefs.default_device_id = int(device_setting.value)

    return prefs


@router.put("/preferences")
def update_user_preferences(preferences: UserPreferences, db: Session = Depends(get_db)):
    """Update user preferences in database."""

    # Update latitude
    if preferences.latitude is not None:
        lat_setting = db.query(AppSetting).filter(AppSetting.key == "user.latitude").first()
        if lat_setting:
            lat_setting.value = str(preferences.latitude)
        else:
            lat_setting = AppSetting(
                key="user.latitude",
                value=str(preferences.latitude),
                value_type="float",
                category="user",
                description="User's latitude"
            )
            db.add(lat_setting)

    # Update longitude
    if preferences.longitude is not None:
        lon_setting = db.query(AppSetting).filter(AppSetting.key == "user.longitude").first()
        if lon_setting:
            lon_setting.value = str(preferences.longitude)
        else:
            lon_setting = AppSetting(
                key="user.longitude",
                value=str(preferences.longitude),
                value_type="float",
                category="user",
                description="User's longitude"
            )
            db.add(lon_setting)

    # Update elevation
    if preferences.elevation is not None:
        elev_setting = db.query(AppSetting).filter(AppSetting.key == "user.elevation").first()
        if elev_setting:
            elev_setting.value = str(preferences.elevation)
        else:
            elev_setting = AppSetting(
                key="user.elevation",
                value=str(preferences.elevation),
                value_type="float",
                category="user",
                description="User's elevation (meters)"
            )
            db.add(elev_setting)

    # Update units
    units_setting = db.query(AppSetting).filter(AppSetting.key == "user.units").first()
    if units_setting:
        units_setting.value = preferences.units
    else:
        units_setting = AppSetting(
            key="user.units",
            value=preferences.units,
            value_type="string",
            category="user",
            description="User's preferred units (metric/imperial)"
        )
        db.add(units_setting)

    # Update default device
    if preferences.default_device_id is not None:
        device_setting = db.query(AppSetting).filter(AppSetting.key == "user.default_device_id").first()
        if device_setting:
            device_setting.value = str(preferences.default_device_id)
        else:
            device_setting = AppSetting(
                key="user.default_device_id",
                value=str(preferences.default_device_id),
                value_type="int",
                category="user",
                description="User's default device ID"
            )
            db.add(device_setting)

    db.commit()

    return {"status": "success", "message": "Preferences updated"}
