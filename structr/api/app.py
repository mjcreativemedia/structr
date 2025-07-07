"""
Main FastAPI Application

Central FastAPI app with all endpoints and middleware.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import time
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from .endpoints.connectors import router as connectors_router
from .endpoints.batches import router as batches_router
from .endpoints.monitoring import router as monitoring_router
from .endpoints.webhooks import router as webhooks_router
from .middleware import setup_middleware
from .auth import APIKeyAuth

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(config: Optional[Dict[str, Any]] = None) -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Structr API",
        description="PDP Optimization Engine API for external integration",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configuration
    config = config or {}
    app.state.config = {
        'api_keys': config.get('api_keys', ['dev-key-123']),
        'cors_origins': config.get('cors_origins', ['*']),
        'rate_limit': config.get('rate_limit', 100),  # requests per minute
        'require_auth': config.get('require_auth', False),
        'webhook_secret': config.get('webhook_secret', 'default-secret'),
        'storage_dir': Path(config.get('storage_dir', 'output'))
    }
    
    # Setup middleware
    setup_middleware(app)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app.state.config['cors_origins'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Authentication
    auth = APIKeyAuth(app.state.config['api_keys'])
    
    # Include routers
    app.include_router(
        connectors_router,
        prefix="/api/v1/connectors",
        tags=["connectors"]
    )
    
    app.include_router(
        batches_router,
        prefix="/api/v1/batches", 
        tags=["batches"]
    )
    
    app.include_router(
        monitoring_router,
        prefix="/api/v1/monitoring",
        tags=["monitoring"]
    )
    
    app.include_router(
        webhooks_router,
        prefix="/api/v1/webhooks",
        tags=["webhooks"]
    )
    
    # Health check endpoint
    @app.get("/health", tags=["system"])
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "0.1.0"
        }
    
    # API info endpoint
    @app.get("/api/v1/info", tags=["system"])
    async def api_info():
        """Get API information and capabilities"""
        return {
            "name": "Structr API",
            "version": "0.1.0",
            "description": "PDP Optimization Engine API",
            "capabilities": [
                "data_import",
                "batch_processing", 
                "progress_monitoring",
                "webhook_integration",
                "csv_export",
                "shopify_integration"
            ],
            "supported_connectors": [
                "shopify_csv",
                "generic_csv",
                "pim_api",
                "webhook"
            ],
            "limits": {
                "max_batch_size": 10000,
                "max_file_size_mb": 100,
                "rate_limit_per_minute": app.state.config['rate_limit']
            }
        }
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "timestamp": time.time()
            }
        )
    
    return app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )