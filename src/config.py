"""Centralized configuration management using environment variables."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Twitter settings
    TWITTER_BASE_URL: str = os.getenv("TWITTER_BASE_URL", "https://x.com")
    AUTH_STATE_PATH: str = os.getenv("AUTH_STATE_PATH", "auth.json")

    # Browser settings
    BROWSER_HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "60000"))

    # MCP settings
    MCP_SERVER_NAME: str = os.getenv("MCP_SERVER_NAME", "TwitterMCPAgent")

    # REST API settings
    HTTP_HOST: str = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT: int = int(os.getenv("HTTP_PORT", "8000"))

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration is present."""
        auth_path = Path(cls.AUTH_STATE_PATH)
        if not auth_path.exists():
            raise FileNotFoundError(
                f"Authentication file not found: {cls.AUTH_STATE_PATH}. "
                f"Please run login_and_save_auth.py first."
            )

    @classmethod
    def get_auth_state_path(cls) -> Path:
        """Get the authentication state file path."""
        return Path(cls.AUTH_STATE_PATH)


# Global config instance
config = Config()
