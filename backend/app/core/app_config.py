"""
Application Configuration Settings

Manages application-specific configurations including:
- Data file paths
- ChromaDB settings
- General application parameters
- Logging configuration
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import validator, Field


class AppSettings(BaseSettings):
    """Configuration for application-specific settings."""

    # Project Information
    app_project_name: str = "RecruiterRadar MVP"
    app_api_prefix: str = ""  # No prefix for MVP, but configurable
    app_version: str = "1.0.0"

    # Environment & Debug
    app_environment: str = "development"
    app_debug: bool = True
    app_log_level: str = "INFO"
    # Verbose resume extraction diagnostics (toggle via env: APP_VERBOSE_EXTRACTION=true)
    app_verbose_extraction: bool = Field(default=False, env="APP_VERBOSE_EXTRACTION")

    # Data Configuration
    app_candidate_data_path: str = "app/data/candidate_profiles.json"

    # ADDED: New field to capture the CANDIDATE_DATA_FULL_PATH environment variable
    candidate_data_override_path: Optional[str] = Field(
        None, env="OVERRIDE_CANDIDATE_DATA_FULL_PATH"
    )

    # ChromaDB Configuration
    app_chroma_db_path: str = "app/data/chroma_db"
    app_chroma_collection_name: str = "recruiter_radar_candidates"
    app_chroma_persist_directory: Optional[str] = (
        None  # Will use chroma_db_path if None
    )

    # Application Limits
    app_max_file_size_mb: int = 10  # Maximum file size for uploads
    app_request_timeout_seconds: int = 30  # API request timeout

    @validator("app_candidate_data_path")
    def validate_candidate_data_path(cls, v: str) -> str:
        """Validate candidate data file exists."""
        # For now, just validate the path format
        # File existence check happens at runtime
        if not v.endswith((".json", ".csv")):
            raise ValueError("Candidate data file must be .json or .csv")
        return v

    @validator("app_log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f'Log level must be one of: {", ".join(valid_levels)}')
        return v_upper

    @validator("app_environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        valid_environments = ["development", "testing", "production"]
        v_lower = v.lower()
        if v_lower not in valid_environments:
            raise ValueError(
                f'Environment must be one of: {", ".join(valid_environments)}'
            )
        return v_lower

    # Convenience properties for cleaner access
    @property
    def project_name(self) -> str:
        return self.app_project_name

    @property
    def api_prefix(self) -> str:
        return self.app_api_prefix

    @property
    def version(self) -> str:
        return self.app_version

    @property
    def environment(self) -> str:
        return self.app_environment

    @property
    def debug(self) -> bool:
        return self.app_debug

    @property
    def log_level(self) -> str:
        return self.app_log_level

    @property
    def candidate_data_path(self) -> str:
        return self.app_candidate_data_path

    @property
    def chroma_db_path(self) -> str:
        return self.app_chroma_db_path

    @property
    def chroma_collection_name(self) -> str:
        return self.app_chroma_collection_name

    @property
    def max_file_size_mb(self) -> int:
        return self.app_max_file_size_mb

    @property
    def request_timeout_seconds(self) -> int:
        return self.app_request_timeout_seconds

    @property
    def candidate_data_full_path(self) -> Path:
        """Get full path to candidate data file.
        Prioritizes an absolute path from the CANDIDATE_DATA_FULL_PATH environment variable if set.
        Otherwise, constructs a path relative to the 'backend' directory.
        """
        if self.candidate_data_override_path:
            # Using path provided via CANDIDATE_DATA_FULL_PATH environment variable
            override_path = Path(self.candidate_data_override_path)
            # It's good practice to ensure it's absolute if an override is intended to be absolute.
            # For this fix, we'll assume the user provides a correct, usable path.
            return override_path
        else:
            # Fallback: Construct path relative to the 'backend' directory,
            # assuming app_config.py is in backend/app/core/
            # Path(__file__) is .../backend/app/core/app_config.py
            # .parent.parent.parent gives the .../backend/ directory
            backend_directory = Path(__file__).resolve().parent.parent.parent
            return backend_directory / self.app_candidate_data_path

    @property
    def chroma_db_full_path(self) -> str:
        """
        Get the absolute path to the ChromaDB directory.
        This ensures that both the ingestion script and the FastAPI application
        reference the exact same database location, regardless of the
        current working directory.
        """
        # Path(__file__) is .../backend/app/core/app_config.py
        # .parent.parent.parent gives the .../backend/ directory
        backend_dir = Path(__file__).resolve().parent.parent.parent
        absolute_path = backend_dir / self.app_chroma_db_path
        return str(absolute_path)

    @property
    def effective_chroma_persist_directory(self) -> str:
        """Get the ChromaDB persist directory to use, ensuring it's an absolute path."""
        # This now returns the guaranteed absolute path.
        return self.chroma_db_full_path
