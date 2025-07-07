"""
Centralized configuration for Structr PDP optimization engine

This module contains all configuration values used across the application,
including paths, model settings, server configurations, and default values.
All settings can be overridden via environment variables.
"""

import os
from pathlib import Path
from typing import Dict, List, Any


class StructrConfig:
    """Central configuration for the entire Structr application"""
    
    # =================== CORE APPLICATION SETTINGS ===================
    
    APP_NAME = "Structr"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Local-first PDP optimization engine"
    
    # =================== DIRECTORY SETTINGS ===================
    
    # Base directories
    ROOT_DIR = Path(__file__).parent
    DEFAULT_OUTPUT_DIR = "output"
    DEFAULT_INPUT_DIR = "input"
    DEFAULT_TEMP_DIR = "temp_uploads"
    DEFAULT_LOGS_DIR = "logs"
    DEFAULT_CACHE_DIR = "cache"
    
    # Sub-directories
    BUNDLES_SUBDIR = "bundles"
    JOBS_SUBDIR = "jobs"
    MONITORING_SUBDIR = "monitoring"
    EXPORTS_SUBDIR = "exports"
    
    @classmethod
    def get_output_dir(cls) -> Path:
        """Get the main output directory"""
        return Path(os.environ.get("STRUCTR_OUTPUT_DIR", cls.DEFAULT_OUTPUT_DIR))
    
    @classmethod
    def get_input_dir(cls) -> Path:
        """Get the main input directory"""
        return Path(os.environ.get("STRUCTR_INPUT_DIR", cls.DEFAULT_INPUT_DIR))
    
    @classmethod
    def get_temp_dir(cls) -> Path:
        """Get the temporary files directory"""
        return Path(os.environ.get("STRUCTR_TEMP_DIR", cls.DEFAULT_TEMP_DIR))
    
    @classmethod
    def get_logs_dir(cls) -> Path:
        """Get the logs directory"""
        return Path(os.environ.get("STRUCTR_LOGS_DIR", cls.DEFAULT_LOGS_DIR))
    
    @classmethod
    def get_cache_dir(cls) -> Path:
        """Get the cache directory"""
        return Path(os.environ.get("STRUCTR_CACHE_DIR", cls.DEFAULT_CACHE_DIR))
    
    @classmethod
    def get_bundles_dir(cls) -> Path:
        """Get the bundles directory"""
        return cls.get_output_dir() / cls.BUNDLES_SUBDIR
    
    @classmethod
    def get_jobs_dir(cls) -> Path:
        """Get the batch jobs directory"""
        return cls.get_output_dir() / cls.JOBS_SUBDIR
    
    @classmethod
    def get_monitoring_dir(cls) -> Path:
        """Get the monitoring data directory"""
        return cls.get_output_dir() / cls.MONITORING_SUBDIR
    
    @classmethod
    def get_exports_dir(cls) -> Path:
        """Get the exports directory"""
        return cls.get_output_dir() / cls.EXPORTS_SUBDIR
    
    # =================== LLM SETTINGS ===================
    
    # Default LLM configuration
    DEFAULT_LLM_MODEL = "mistral"
    AVAILABLE_LLM_MODELS = ["mistral", "llama2", "codellama", "llama3", "phi3"]
    DEFAULT_LLM_BASE_URL = "http://localhost:11434"
    LLM_TIMEOUT = 300  # seconds
    
    # Generation settings
    DEFAULT_GENERATION_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 2048
    DEFAULT_RETRY_ATTEMPTS = 3
    
    @classmethod
    def get_llm_model(cls) -> str:
        """Get the current LLM model"""
        return os.environ.get("STRUCTR_LLM_MODEL", cls.DEFAULT_LLM_MODEL)
    
    @classmethod
    def get_llm_base_url(cls) -> str:
        """Get the LLM service base URL"""
        return os.environ.get("STRUCTR_LLM_BASE_URL", cls.DEFAULT_LLM_BASE_URL)
    
    # =================== SERVER SETTINGS ===================
    
    # Streamlit dashboard
    DEFAULT_DASHBOARD_PORT = 8501
    DEFAULT_DASHBOARD_HOST = "localhost"
    DASHBOARD_HEADLESS = False
    
    # FastAPI backend
    DEFAULT_API_PORT = 8000
    DEFAULT_API_HOST = "0.0.0.0"
    API_RELOAD = False
    
    @classmethod
    def get_dashboard_port(cls) -> int:
        """Get the dashboard port"""
        return int(os.environ.get("STRUCTR_DASHBOARD_PORT", cls.DEFAULT_DASHBOARD_PORT))
    
    @classmethod
    def get_dashboard_host(cls) -> str:
        """Get the dashboard host"""
        return os.environ.get("STRUCTR_DASHBOARD_HOST", cls.DEFAULT_DASHBOARD_HOST)
    
    @classmethod
    def get_api_port(cls) -> int:
        """Get the API port"""
        return int(os.environ.get("STRUCTR_API_PORT", cls.DEFAULT_API_PORT))
    
    @classmethod
    def get_api_host(cls) -> str:
        """Get the API host"""
        return os.environ.get("STRUCTR_API_HOST", cls.DEFAULT_API_HOST)
    
    # =================== FILE SETTINGS ===================
    
    # File extensions
    JSON_EXTENSION = ".json"
    CSV_EXTENSION = ".csv"
    HTML_EXTENSION = ".html"
    LOG_EXTENSION = ".log"
    
    # Standard file names
    AUDIT_FILENAME = "audit.json"
    SYNC_FILENAME = "sync.json"
    HTML_FILENAME = "index.html"
    FIX_LOG_FILENAME = "fix_log.json"
    
    # Export file patterns
    CATALOG_EXPORT_PATTERN = "catalog_structr_{timestamp}.csv"
    AUDIT_REPORT_PATTERN = "audit_report_{timestamp}.csv"
    COMPLIANCE_REPORT_PATTERN = "compliance_report_{timestamp}.csv"
    BUNDLE_ARCHIVE_PATTERN = "structr_bundles_{timestamp}.zip"
    
    # Upload settings
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_UPLOAD_EXTENSIONS = ["json", "csv", "txt"]
    TEMP_FILE_LIFETIME = 3600  # seconds (1 hour)
    
    # =================== BATCH PROCESSING SETTINGS ===================
    
    # Job queue settings
    DEFAULT_MAX_QUEUE_SIZE = 1000
    DEFAULT_WORKER_COUNT = 2
    MAX_WORKER_COUNT = 10
    DEFAULT_BATCH_SIZE = 25
    MAX_BATCH_SIZE = 100
    
    # Progress monitoring
    PROGRESS_UPDATE_INTERVAL = 2  # seconds
    JOB_TIMEOUT = 1800  # seconds (30 minutes)
    
    # Retry settings
    DEFAULT_RETRY_COUNT = 3
    RETRY_DELAY = 5  # seconds
    
    @classmethod
    def get_max_workers(cls) -> int:
        """Get the maximum number of workers"""
        return min(
            int(os.environ.get("STRUCTR_MAX_WORKERS", cls.DEFAULT_WORKER_COUNT)),
            cls.MAX_WORKER_COUNT
        )
    
    # =================== AUDIT SETTINGS ===================
    
    # Score thresholds
    SCORE_THRESHOLDS = {
        "excellent": 90,
        "good": 80,
        "fair": 60,
        "poor": 0
    }
    
    DEFAULT_MIN_SCORE = 80
    MAX_SCORE = 100
    MIN_SCORE = 0
    
    # Issue severity levels
    ISSUE_SEVERITIES = ["critical", "high", "medium", "low"]
    
    # Audit categories
    AUDIT_CATEGORIES = [
        "missing_fields",
        "flagged_issues", 
        "schema_errors",
        "metadata_issues"
    ]
    
    # =================== UI/DASHBOARD SETTINGS ===================
    
    # Page layout
    PAGE_LAYOUT = "wide"
    SIDEBAR_STATE = "auto"
    
    # Data display
    ITEMS_PER_PAGE = 20
    PREVIEW_ROWS = 10
    MAX_PREVIEW_LENGTH = 500
    
    # Cache settings
    CACHE_TTL = 60  # seconds
    AUTO_REFRESH_INTERVAL = 30  # seconds
    
    # Color scheme
    COLORS = {
        "excellent": "#28a745",
        "good": "#17a2b8", 
        "fair": "#ffc107",
        "poor": "#dc3545",
        "primary": "#007bff",
        "secondary": "#6c757d",
        "success": "#28a745",
        "danger": "#dc3545",
        "warning": "#ffc107",
        "info": "#17a2b8"
    }
    
    # Status text mapping
    STATUS_TEXT = {
        "excellent": "Excellent",
        "good": "Good",
        "fair": "Fair", 
        "poor": "Poor"
    }
    
    # =================== INTEGRATION SETTINGS ===================
    
    # Webhook settings
    DEFAULT_WEBHOOK_SECRET = "structr-webhook-secret"
    WEBHOOK_TIMEOUT = 30  # seconds
    
    # API settings
    API_KEY_HEADER = "X-API-Key"
    DEFAULT_RATE_LIMIT = 60  # requests per minute
    
    # External service URLs
    SHOPIFY_API_VERSION = "2024-01"
    
    # =================== CSV/EXPORT SETTINGS ===================
    
    # Export formats
    EXPORT_FORMATS = [
        "Shopify CSV",
        "Generic CSV", 
        "Audit Report CSV",
        "Custom CSV"
    ]
    
    DEFAULT_EXPORT_FORMAT = "Shopify CSV"
    MAX_EXPORT_ROWS = 10000
    INCLUDE_AUDIT_DATA_DEFAULT = True
    
    # CSV field mappings for common platforms
    SHOPIFY_FIELD_MAPPING = {
        "handle": "Handle",
        "title": "Title",
        "description": "Body (HTML)",
        "price": "Variant Price",
        "brand": "Vendor",
        "category": "Product Category",
        "sku": "Variant SKU"
    }
    
    GENERIC_FIELD_MAPPING = {
        "handle": "Product ID",
        "title": "Product Name",
        "description": "Description",
        "price": "Price",
        "brand": "Brand",
        "category": "Category"
    }
    
    # =================== VALIDATION SETTINGS ===================
    
    # Required fields for products
    REQUIRED_PRODUCT_FIELDS = ["handle", "title", "description", "price", "brand"]
    OPTIONAL_PRODUCT_FIELDS = ["category", "images", "features", "sku", "weight"]
    
    # Validation modes
    VALIDATION_MODES = ["strict", "lenient", "skip"]
    DEFAULT_VALIDATION_MODE = "lenient"
    
    # =================== LOGGING SETTINGS ===================
    
    LOG_LEVEL = os.environ.get("STRUCTR_LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # =================== SECURITY SETTINGS ===================
    
    # API security
    ENABLE_API_AUTH = True
    DEFAULT_API_KEY = "structr-default-key-change-in-production"
    
    # File security
    ALLOWED_FILE_TYPES = ["json", "csv", "html", "txt"]
    MAX_FILE_PATH_LENGTH = 255
    
    @classmethod
    def get_api_key(cls) -> str:
        """Get the API key"""
        return os.environ.get("STRUCTR_API_KEY", cls.DEFAULT_API_KEY)
    
    # =================== ENVIRONMENT-SPECIFIC OVERRIDES ===================
    
    @classmethod
    def configure_for_environment(cls):
        """Configure settings based on environment"""
        env = os.environ.get("STRUCTR_ENV", "development").lower()
        
        if env == "development":
            cls.CACHE_TTL = 10
            cls.AUTO_REFRESH_INTERVAL = 10
            cls.API_RELOAD = True
            cls.LOG_LEVEL = "DEBUG"
        
        elif env == "production":
            cls.CACHE_TTL = 300
            cls.AUTO_REFRESH_INTERVAL = 60
            cls.API_RELOAD = False
            cls.LOG_LEVEL = "INFO"
            cls.DASHBOARD_HEADLESS = True
        
        elif env == "testing":
            cls.CACHE_TTL = 1
            cls.AUTO_REFRESH_INTERVAL = 5
            cls.LOG_LEVEL = "DEBUG"
    
    # =================== UTILITY METHODS ===================
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        directories = [
            cls.get_output_dir(),
            cls.get_input_dir(),
            cls.get_temp_dir(),
            cls.get_logs_dir(),
            cls.get_cache_dir(),
            cls.get_bundles_dir(),
            cls.get_jobs_dir(),
            cls.get_monitoring_dir(),
            cls.get_exports_dir()
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_file_path(cls, directory: str, filename: str) -> Path:
        """Get a standardized file path"""
        if directory == "output":
            return cls.get_output_dir() / filename
        elif directory == "input":
            return cls.get_input_dir() / filename
        elif directory == "temp":
            return cls.get_temp_dir() / filename
        elif directory == "logs":
            return cls.get_logs_dir() / filename
        elif directory == "bundles":
            return cls.get_bundles_dir() / filename
        else:
            return Path(directory) / filename
    
    @classmethod
    def get_bundle_path(cls, bundle_id: str) -> Path:
        """Get the path for a specific bundle"""
        return cls.get_bundles_dir() / bundle_id
    
    @classmethod
    def get_audit_file_path(cls, bundle_id: str) -> Path:
        """Get the audit file path for a bundle"""
        return cls.get_bundle_path(bundle_id) / cls.AUDIT_FILENAME
    
    @classmethod
    def get_sync_file_path(cls, bundle_id: str) -> Path:
        """Get the sync file path for a bundle"""
        return cls.get_bundle_path(bundle_id) / cls.SYNC_FILENAME
    
    @classmethod
    def get_html_file_path(cls, bundle_id: str) -> Path:
        """Get the HTML file path for a bundle"""
        return cls.get_bundle_path(bundle_id) / cls.HTML_FILENAME
    
    @classmethod
    def get_fix_log_path(cls, bundle_id: str) -> Path:
        """Get the fix log path for a bundle"""
        return cls.get_bundle_path(bundle_id) / cls.FIX_LOG_FILENAME
    
    @classmethod
    def get_timestamp_filename(cls, pattern: str) -> str:
        """Get a filename with timestamp"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return pattern.format(timestamp=timestamp)
    
    @classmethod
    def get_dashboard_url(cls) -> str:
        """Get the dashboard URL"""
        host = cls.get_dashboard_host()
        port = cls.get_dashboard_port()
        return f"http://{host}:{port}"
    
    @classmethod
    def get_api_url(cls) -> str:
        """Get the API base URL"""
        host = cls.get_api_host()
        port = cls.get_api_port()
        return f"http://{host}:{port}"
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        config = {}
        
        for attr_name in dir(cls):
            if not attr_name.startswith('_') and not callable(getattr(cls, attr_name)):
                attr_value = getattr(cls, attr_name)
                if not callable(attr_value):
                    config[attr_name] = attr_value
        
        return config


# Initialize configuration for current environment
StructrConfig.configure_for_environment()
StructrConfig.ensure_directories()


# Convenience aliases for commonly used settings
CONFIG = StructrConfig
PATHS = StructrConfig
LLM = StructrConfig
UI = StructrConfig