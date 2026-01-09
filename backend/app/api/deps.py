"""
API dependencies.
"""

from fastapi import HTTPException

from app.api import routes
from app.clients.seestar_client import SeestarClient


def get_current_telescope() -> SeestarClient:
    """
    Get the currently connected telescope client.

    Raises:
        HTTPException: If no telescope is connected
    """
    if routes.seestar_client is None:
        raise HTTPException(status_code=400, detail="No telescope connected. Connect to a telescope first.")
    return routes.seestar_client
