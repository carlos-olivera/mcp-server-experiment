#!/usr/bin/env python3
"""Entry point for running the REST API server."""

import uvicorn
from src.config import config

if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app",
        host=config.HTTP_HOST,
        port=config.HTTP_PORT,
        reload=False,  # Set to True for development
        log_level=config.LOG_LEVEL.lower()
    )
