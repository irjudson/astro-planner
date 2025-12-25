"""Webhook notification service for plan events."""

import logging
import os
from datetime import datetime
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for sending webhook notifications about plan events."""

    def __init__(self, webhook_url: Optional[str] = None):
        """Initialize webhook service with configuration.

        Args:
            webhook_url: Webhook URL (optional, defaults to WEBHOOK_URL env var)
        """
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_URL")
        self.timeout = 5  # seconds
        self.max_retries = 2

    def send_plan_created_notification(
        self,
        plan_id: int,
        plan_name: str,
        observing_date: str,
        target_names: List[str],
        session_start: Optional[str] = None,
        session_end: Optional[str] = None,
    ) -> bool:
        """
        Send webhook notification when a plan is created.

        Args:
            plan_id: Database ID of the created plan
            plan_name: Name of the plan (e.g., "2024-12-25-plan")
            observing_date: Date of observation (YYYY-MM-DD)
            target_names: List of target names in the plan
            session_start: Session start time (ISO format with timezone)
            session_end: Session end time (ISO format with timezone)

        Returns:
            True if webhook sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.debug("No webhook URL configured, skipping notification")
            return False

        # Build webhook payload
        payload = {
            "event": "plan_created",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "plan": {
                "id": plan_id,
                "name": plan_name,
                "observing_date": observing_date,
                "target_count": len(target_names),
                "targets": target_names,
            },
        }

        # Add optional session times if provided
        if session_start:
            payload["plan"]["session_start"] = session_start
        if session_end:
            payload["plan"]["session_end"] = session_end

        # Send webhook with retries
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Sending webhook to {self.webhook_url} (attempt {attempt + 1}/{self.max_retries + 1})")

                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json", "User-Agent": "AstroPlanner/1.0"},
                )

                # Check response status
                response.raise_for_status()

                logger.info(f"Webhook sent successfully to {self.webhook_url}")
                return True

            except requests.exceptions.Timeout:
                logger.warning(f"Webhook request timed out (attempt {attempt + 1}/{self.max_retries + 1})")
                if attempt == self.max_retries:
                    logger.error(f"Webhook failed after {self.max_retries + 1} attempts (timeout)")
                    return False

            except requests.exceptions.RequestException as e:
                logger.warning(f"Webhook request failed: {e} (attempt {attempt + 1}/{self.max_retries + 1})")
                if attempt == self.max_retries:
                    logger.error(f"Webhook failed after {self.max_retries + 1} attempts: {e}")
                    return False

            except Exception as e:
                logger.error(f"Unexpected error sending webhook: {e}")
                return False

        return False

    def is_configured(self) -> bool:
        """Check if webhook URL is configured."""
        return bool(self.webhook_url)
