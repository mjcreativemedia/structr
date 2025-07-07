"""
API Endpoints Package

REST API endpoints for Structr external integration.
"""

from .connectors import router as connectors_router
from .batches import router as batches_router  
from .monitoring import router as monitoring_router
from .webhooks import router as webhooks_router

__all__ = [
    "connectors_router",
    "batches_router",
    "monitoring_router", 
    "webhooks_router"
]