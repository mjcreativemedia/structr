"""
API Middleware

Custom middleware for the Structr API.
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import time
import logging
import json
from typing import Callable
import uuid

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests with timing and response status"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Start timing
        start_time = time.time()
        
        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Add request ID to state
        request.state.request_id = request_id
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"[{request_id}] {response.status_code} "
                f"in {duration:.3f}s"
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] ERROR {str(e)} "
                f"in {duration:.3f}s"
            )
            raise


class ResponseHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard response headers"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Add API version
        response.headers["X-API-Version"] = "0.1.0"
        
        # Add timestamp
        response.headers["X-Timestamp"] = str(int(time.time()))
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Handle and format errors consistently"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            # Log error with request context
            request_id = getattr(request.state, 'request_id', 'unknown')
            logger.error(f"[{request_id}] Unhandled error: {str(e)}", exc_info=True)
            
            # Return formatted error response
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect API metrics"""
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics = {
            'total_requests': 0,
            'total_errors': 0,
            'response_times': [],
            'endpoints': {},  # endpoint -> {count, total_time, errors}
            'status_codes': {},  # code -> count
            'start_time': time.time()
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Update total requests
        self.metrics['total_requests'] += 1
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Update metrics
            self._update_endpoint_metrics(request.url.path, duration, False)
            self._update_status_code_metrics(response.status_code)
            self.metrics['response_times'].append(duration)
            
            # Limit response times history
            if len(self.metrics['response_times']) > 1000:
                self.metrics['response_times'] = self.metrics['response_times'][-1000:]
            
            # Add metrics headers
            response.headers["X-Total-Requests"] = str(self.metrics['total_requests'])
            response.headers["X-Uptime"] = str(int(time.time() - self.metrics['start_time']))
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Update error metrics
            self.metrics['total_errors'] += 1
            self._update_endpoint_metrics(request.url.path, duration, True)
            self._update_status_code_metrics(500)
            
            raise
    
    def _update_endpoint_metrics(self, endpoint: str, duration: float, is_error: bool):
        """Update metrics for specific endpoint"""
        if endpoint not in self.metrics['endpoints']:
            self.metrics['endpoints'][endpoint] = {
                'count': 0,
                'total_time': 0.0,
                'errors': 0,
                'avg_time': 0.0
            }
        
        endpoint_metrics = self.metrics['endpoints'][endpoint]
        endpoint_metrics['count'] += 1
        endpoint_metrics['total_time'] += duration
        endpoint_metrics['avg_time'] = endpoint_metrics['total_time'] / endpoint_metrics['count']
        
        if is_error:
            endpoint_metrics['errors'] += 1
    
    def _update_status_code_metrics(self, status_code: int):
        """Update status code metrics"""
        if status_code not in self.metrics['status_codes']:
            self.metrics['status_codes'][status_code] = 0
        self.metrics['status_codes'][status_code] += 1
    
    def get_metrics(self) -> dict:
        """Get current metrics"""
        uptime = time.time() - self.metrics['start_time']
        response_times = self.metrics['response_times']
        
        return {
            'uptime_seconds': uptime,
            'total_requests': self.metrics['total_requests'],
            'total_errors': self.metrics['total_errors'],
            'error_rate': (self.metrics['total_errors'] / max(1, self.metrics['total_requests'])) * 100,
            'requests_per_second': self.metrics['total_requests'] / max(1, uptime),
            'response_times': {
                'count': len(response_times),
                'avg': sum(response_times) / len(response_times) if response_times else 0,
                'min': min(response_times) if response_times else 0,
                'max': max(response_times) if response_times else 0,
                'p95': self._percentile(response_times, 95) if response_times else 0,
                'p99': self._percentile(response_times, 99) if response_times else 0
            },
            'endpoints': self.metrics['endpoints'].copy(),
            'status_codes': self.metrics['status_codes'].copy()
        }
    
    def _percentile(self, values: list, percentile: int) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the FastAPI app"""
    
    # Metrics middleware (first, to capture all requests)
    metrics_middleware = MetricsMiddleware(app)
    app.add_middleware(BaseHTTPMiddleware, dispatch=metrics_middleware.dispatch)
    
    # Store metrics middleware in app state for access
    app.state.metrics = metrics_middleware
    
    # Error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Response headers middleware  
    app.add_middleware(ResponseHeadersMiddleware)
    
    # Request logging middleware (last, for complete request info)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add metrics endpoint
    @app.get("/api/v1/metrics", tags=["system"])
    async def get_metrics():
        """Get API performance metrics"""
        return app.state.metrics.get_metrics()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware (optional advanced feature)"""
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests = {}  # client_ip -> {count, window_start}
        self.window_size = 60  # 1 minute
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Check rate limit
        if not self._check_rate_limit(client_ip, current_time):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit of {self.requests_per_minute} requests per minute exceeded",
                    "timestamp": current_time
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        limit_info = self._get_rate_limit_info(client_ip, current_time)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(limit_info['remaining'])
        response.headers["X-RateLimit-Reset"] = str(int(limit_info['reset_time']))
        
        return response
    
    def _check_rate_limit(self, client_ip: str, current_time: float) -> bool:
        """Check if client is within rate limits"""
        if client_ip not in self.client_requests:
            self.client_requests[client_ip] = {
                'count': 1,
                'window_start': current_time
            }
            return True
        
        client_data = self.client_requests[client_ip]
        
        # Reset window if expired
        if current_time - client_data['window_start'] > self.window_size:
            client_data['count'] = 1
            client_data['window_start'] = current_time
            return True
        
        # Check if over limit
        if client_data['count'] >= self.requests_per_minute:
            return False
        
        # Increment counter
        client_data['count'] += 1
        return True
    
    def _get_rate_limit_info(self, client_ip: str, current_time: float) -> dict:
        """Get rate limit info for client"""
        if client_ip not in self.client_requests:
            return {
                'remaining': self.requests_per_minute,
                'reset_time': current_time + self.window_size
            }
        
        client_data = self.client_requests[client_ip]
        
        return {
            'remaining': max(0, self.requests_per_minute - client_data['count']),
            'reset_time': client_data['window_start'] + self.window_size
        }