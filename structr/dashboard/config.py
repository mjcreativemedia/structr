"""
Dashboard configuration settings for Structr

This module provides dashboard-specific configuration that extends
the central Structr configuration.
"""

import os
from pathlib import Path
from config import StructrConfig


class DashboardConfig(StructrConfig):
    """Dashboard-specific configuration extending StructrConfig"""
    
    # Application settings
    APP_TITLE = "Structr Dashboard"
    APP_ICON = "🧱"
    
    # Inherit all settings from StructrConfig and add dashboard-specific ones
    # Most settings are now centralized in the main config.py
    
    # Dashboard-specific UI settings
    SIDEBAR_EXPANDED = True
    SHOW_TOOLBAR = True
    SHOW_RUNNING_INDICATOR = True
    
    # Dashboard navigation
    DEFAULT_PAGE = "Overview"
    PAGES = {
        "Overview": "📊",
        "Bundle Explorer": "📂",
        "Audit Manager": "🔍",
        "Batch Processor": "⚡",
        "Export Center": "📤"
    }
    
    # Dashboard-specific cache settings
    BUNDLE_CACHE_SIZE = 50  # Number of bundles to cache in memory
    CHART_CACHE_TTL = 300   # Chart data cache time
    
    # Dashboard help text
    HELP_TEXT = {
        "overview": "View your PDP optimization summary and recent activity",
        "bundle_explorer": "Browse and inspect individual PDP bundles",
        "audit_manager": "Analyze audit results and run compliance reports",
        "batch_processor": "Upload and process multiple products at scale",
        "export_center": "Export catalogs and reports to various formats"
    }


# Use the centralized configuration system
config = DashboardConfig