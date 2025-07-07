"""
Structr API

FastAPI-based REST API for external integration.
Provides endpoints for connectors, batch processing, and monitoring.
"""

from .app import create_app
from .auth import APIKeyAuth
from .middleware import setup_middleware

__version__ = "0.1.0"

__all__ = [
    "create_app",
    "APIKeyAuth", 
    "setup_middleware"
]