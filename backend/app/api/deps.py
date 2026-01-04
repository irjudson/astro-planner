"""
API dependencies.
"""

from fastapi import HTTPException
from app.telescope.base_adapter import TelescopeAdapter
from app.api import routes


def get_current_telescope() -> TelescopeAdapter:
    """
    Get the currently connected telescope adapter.

    Raises:
        HTTPException: If no telescope is connected
    """
    if routes.telescope_adapter is None:
        raise HTTPException(
            status_code=400,
            detail="No telescope connected. Connect to a telescope first."
        )
    return routes.telescope_adapter
