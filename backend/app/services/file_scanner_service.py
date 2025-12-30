"""File scanner service for discovering and processing image files."""

from sqlalchemy.orm import Session


class FileScannerService:
    """Service for scanning directories and processing image files."""

    def __init__(self, db: Session):
        """Initialize file scanner service with database session."""
        self.db = db
