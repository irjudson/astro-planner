"""Celery tasks for automatic plan generation."""

import logging
import os
from datetime import date, datetime
from typing import Any, Dict

from app.database import SessionLocal
from app.models import Location, ObservingConstraints, PlanRequest
from app.models.plan_models import SavedPlan
from app.models.settings_models import AppSetting, ObservingLocation
from app.services.planner_service import PlannerService
from app.services.webhook_service import WebhookService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_setting_value(db, key: str, default: str) -> str:
    """Get a setting value from database, with fallback to default."""
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    return setting.value if setting else default


@celery_app.task(bind=True, name="generate_daily_plan")
def generate_daily_plan_task(self) -> Dict[str, Any]:
    """
    Generate automatic daily observing plan for the evening.

    Runs daily at noon (configured timezone), creates a plan named YYYY-MM-DD-plan
    with the top N targets for that evening's observation session (configurable).

    Uses Quality planning mode (45-180 min/target, min_score 0.7) and selects
    the highest-scoring targets based on settings.

    Returns:
        Dict with plan summary (name, target_count, plan_id, status)
    """
    db = SessionLocal()
    try:
        # Check if daily planning is enabled
        enabled = get_setting_value(db, "planning.daily_enabled", "true")
        if enabled.lower() not in ("true", "1", "yes"):
            logger.info("Daily plan generation is disabled in settings")
            return {"status": "skipped", "reason": "disabled_in_settings"}

        # Get target count from settings
        target_count = int(get_setting_value(db, "planning.daily_target_count", "5"))

        # Try to get default location from database first
        db_location = db.query(ObservingLocation).filter(ObservingLocation.is_default == True).first()

        if db_location:
            # Use database location
            lat = db_location.latitude
            lon = db_location.longitude
            elevation = db_location.elevation
            timezone = db_location.timezone
            location_name = db_location.name
            logger.info(f"Using database location: {location_name}")
        else:
            # Fallback to environment variables
            lat = float(os.getenv("DEFAULT_LAT", "45.9183"))
            lon = float(os.getenv("DEFAULT_LON", "-111.5433"))
            elevation = int(os.getenv("DEFAULT_ELEVATION", "1234"))
            timezone = os.getenv("CELERY_TIMEZONE", os.getenv("DEFAULT_TIMEZONE", "America/Denver"))
            location_name = os.getenv("DEFAULT_LOCATION_NAME", f"Lat {lat:.2f}, Lon {lon:.2f}")
            logger.info("Using environment variables for location (no default location in database)")

        logger.info(f"Daily plan generation started for location: {location_name} ({lat}, {lon})")

        # Create Location object
        location = Location(
            latitude=lat,
            longitude=lon,
            elevation=elevation,
            timezone=timezone,
            name=location_name,
        )

        # Determine observing date (today's evening)
        today = date.today()
        observing_date = today.isoformat()

        logger.info(f"Generating plan for observing date: {observing_date}")

        # Check if plan with this name exists and generate unique name
        base_name = f"{observing_date}-plan"
        plan_name = base_name
        suffix = 1

        while db.query(SavedPlan).filter(SavedPlan.name == plan_name).first():
            suffix += 1
            plan_name = f"{base_name}-{suffix}"
            logger.info(f"Plan '{base_name}' exists, trying '{plan_name}'")

        logger.info(f"Plan name: {plan_name}")

        # Get user observing preferences from database
        min_altitude = float(get_setting_value(db, "user.min_altitude", "30.0"))
        max_moon_phase = int(get_setting_value(db, "user.max_moon_phase", "50"))
        avoid_moon = get_setting_value(db, "user.avoid_moon", "true").lower() in ("true", "1", "yes")

        logger.info(f"Using preferences: min_alt={min_altitude}°, max_moon={max_moon_phase}%, avoid_moon={avoid_moon}")

        # Create Quality mode constraints (optimized for quality) with user preferences
        constraints = ObservingConstraints(
            object_types=[
                "galaxy",
                "nebula",
                "cluster",
                "planetary_nebula",
                "supernova_remnant",
                "comet",
            ],
            min_altitude=min_altitude,
            max_altitude=90,
            max_moon_illumination=max_moon_phase / 100.0,  # Convert percentage to 0-1
            min_duration=45,  # Quality mode: 45-180 minutes
            max_duration=180,
            max_targets=8,  # Will limit later by target_count setting
            min_score=0.7,  # Quality mode threshold
            planning_mode="quality",
            daytime_planning=False,
            setup_time_minutes=30,
        )

        # Create plan request
        plan_request = PlanRequest(
            location=location,
            observing_date=observing_date,
            constraints=constraints,
        )

        # Generate plan using PlannerService
        logger.info("Calling PlannerService to generate plan...")
        planner_service = PlannerService(db)
        observing_plan = planner_service.generate_plan(plan_request)

        logger.info(f"Plan generated with {len(observing_plan.scheduled_targets)} targets")

        # Limit to top N targets by composite_score (from settings)
        if len(observing_plan.scheduled_targets) > target_count:
            # Sort by composite_score (descending) and take top N
            sorted_targets = sorted(
                observing_plan.scheduled_targets,
                key=lambda t: t.composite_score,
                reverse=True,
            )
            observing_plan.scheduled_targets = sorted_targets[:target_count]
            logger.info(f"Limited to top {target_count} targets by score")

        # Extract target names for logging/webhook
        target_names = [target.target.name for target in observing_plan.scheduled_targets]
        logger.info(f"Selected targets: {', '.join(target_names)}")

        # Save plan to database
        saved_plan = SavedPlan(
            name=plan_name,
            description=f"Automatic daily plan generated at noon on {datetime.now().isoformat()}",
            observing_date=observing_date,
            location_name=location_name,
            plan_data=observing_plan.model_dump(mode="json"),  # Convert Pydantic model with JSON-safe serialization
        )

        db.add(saved_plan)
        db.commit()
        db.refresh(saved_plan)

        logger.info(f"Saved plan ID {saved_plan.id} to database")

        # Send webhook notification (use database setting or environment variable)
        webhook_url = get_setting_value(db, "planning.webhook_url", os.getenv("WEBHOOK_URL", ""))
        webhook_service = WebhookService(webhook_url=webhook_url)
        if webhook_service.is_configured():
            # Get session times in ISO format
            session_start = observing_plan.session.imaging_start.isoformat()
            session_end = observing_plan.session.imaging_end.isoformat()

            webhook_sent = webhook_service.send_plan_created_notification(
                plan_id=saved_plan.id,
                plan_name=plan_name,
                observing_date=observing_date,
                target_names=target_names,
                session_start=session_start,
                session_end=session_end,
            )

            if webhook_sent:
                logger.info("Webhook notification sent successfully")
            else:
                logger.warning("Webhook notification failed")
        else:
            logger.debug("Webhook not configured, skipping notification")

        # Return summary
        result = {
            "status": "success",
            "plan_id": saved_plan.id,
            "plan_name": plan_name,
            "observing_date": observing_date,
            "target_count": len(observing_plan.scheduled_targets),
            "targets": target_names,
            "session_start": observing_plan.session.imaging_start.isoformat(),
            "session_end": observing_plan.session.imaging_end.isoformat(),
        }

        logger.info(
            f"Daily plan generation complete: '{plan_name}' with {len(target_names)} targets: {', '.join(target_names)}"
        )

        return result

    except Exception as e:
        logger.error(f"Daily plan generation failed: {e}", exc_info=True)
        raise

    finally:
        db.close()
