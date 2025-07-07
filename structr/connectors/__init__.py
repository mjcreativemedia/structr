"""
Connectors Package

Data source integrations for Structr PDP engine.
Supports Shopify, PIM systems, and generic CSV/API sources.
"""

from .base import BaseConnector, ConnectorConfig, ImportResult
from .shopify.importer import ShopifyCSVImporter
from .pim.connector import PIMConnector
from .generic.csv_mapper import GenericCSVMapper

__version__ = "0.1.0"

__all__ = [
    "BaseConnector",
    "ConnectorConfig", 
    "ImportResult",
    "ShopifyCSVImporter",
    "PIMConnector",
    "GenericCSVMapper"
]