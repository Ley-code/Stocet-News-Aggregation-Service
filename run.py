#!/usr/bin/env python3
"""Entry point for running the FastAPI application."""
import uvicorn
from src.infrastructure.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )

