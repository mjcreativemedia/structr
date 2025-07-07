"""
Base Connector Classes

Foundation for all data source connectors in Structr.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

from models.pdp import ProductData


@dataclass
class ConnectorConfig:
    """Configuration for data connectors"""
    name: str
    source_type: str  # 'csv', 'api', 'webhook', 'ftp'
    credentials: Dict[str, Any] = field(default_factory=dict)
    field_mapping: Dict[str, str] = field(default_factory=dict)
    batch_size: int = 100
    timeout: int = 30
    retry_attempts: int = 3
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    

@dataclass 
class ImportResult:
    """Result of data import operation"""
    success: bool
    total_records: int
    processed_records: int
    failed_records: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    imported_products: List[ProductData] = field(default_factory=list)
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100


@dataclass
class ExportResult:
    """Result of data export operation"""
    success: bool
    exported_count: int
    output_path: Optional[Path] = None
    format: str = "csv"
    errors: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class BaseConnector(ABC):
    """
    Abstract base class for all data connectors.
    
    Provides common functionality for importing/exporting product data
    from various sources (Shopify, PIM systems, CSV files, APIs).
    """
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.field_mapping = config.field_mapping or self._default_field_mapping()
        self._validate_config()
    
    @abstractmethod
    def _default_field_mapping(self) -> Dict[str, str]:
        """Return default field mapping for this connector"""
        pass
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate connector configuration"""
        pass
    
    @abstractmethod
    def import_data(self, source: Union[str, Path, Dict]) -> ImportResult:
        """Import data from source and return standardized products"""
        pass
    
    @abstractmethod
    def export_data(self, products: List[ProductData], destination: Union[str, Path]) -> ExportResult:
        """Export products to destination in source format"""
        pass
    
    def test_connection(self) -> bool:
        """Test connectivity to data source"""
        return True
    
    def get_available_fields(self) -> List[str]:
        """Get list of available fields from data source"""
        return []
    
    def normalize_product(self, raw_data: Dict[str, Any]) -> ProductData:
        """
        Convert raw product data to standardized ProductData format.
        
        Uses field mapping to transform source fields to Structr fields.
        """
        mapped_data = {}
        
        # Apply field mapping
        for source_field, target_field in self.field_mapping.items():
            if source_field in raw_data:
                mapped_data[target_field] = raw_data[source_field]
        
        # Handle required fields with defaults
        normalized = {
            'id': mapped_data.get('id', f"product-{datetime.now().timestamp()}"),
            'title': mapped_data.get('title', 'Untitled Product'),
            'body_html': mapped_data.get('body_html', ''),
            'vendor': mapped_data.get('vendor', ''),
            'product_type': mapped_data.get('product_type', ''),
            'price': self._parse_price(mapped_data.get('price', '0')),
            'compare_at_price': self._parse_price(mapped_data.get('compare_at_price')),
            'sku': mapped_data.get('sku', ''),
            'barcode': mapped_data.get('barcode', ''),
            'weight': self._parse_weight(mapped_data.get('weight')),
            'weight_unit': mapped_data.get('weight_unit', 'kg'),
            'inventory_quantity': int(mapped_data.get('inventory_quantity', 0)),
            'tags': self._parse_tags(mapped_data.get('tags', '')),
            'images': self._parse_images(mapped_data.get('images', [])),
            'variants': mapped_data.get('variants', []),
            'seo_title': mapped_data.get('seo_title', ''),
            'seo_description': mapped_data.get('seo_description', ''),
            'metafields': mapped_data.get('metafields', {}),
            'status': mapped_data.get('status', 'active'),
            'published': bool(mapped_data.get('published', True))
        }
        
        return ProductData(**normalized)
    
    def _parse_price(self, price_str: Any) -> float:
        """Parse price string to float"""
        if not price_str:
            return 0.0
        
        try:
            # Remove currency symbols and commas
            clean_price = str(price_str).replace('$', '').replace(',', '').strip()
            return float(clean_price) if clean_price else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_weight(self, weight_str: Any) -> float:
        """Parse weight string to float"""
        if not weight_str:
            return 0.0
            
        try:
            clean_weight = str(weight_str).replace('kg', '').replace('lb', '').strip()
            return float(clean_weight) if clean_weight else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_tags(self, tags_str: Any) -> List[str]:
        """Parse tags string to list"""
        if not tags_str:
            return []
            
        if isinstance(tags_str, list):
            return tags_str
            
        # Split by comma and clean
        return [tag.strip() for tag in str(tags_str).split(',') if tag.strip()]
    
    def _parse_images(self, images_data: Any) -> List[str]:
        """Parse images data to list of URLs"""
        if not images_data:
            return []
            
        if isinstance(images_data, str):
            # Single URL or comma-separated URLs
            return [url.strip() for url in images_data.split(',') if url.strip()]
            
        if isinstance(images_data, list):
            return [str(img) for img in images_data if img]
            
        return []
    
    def save_import_log(self, result: ImportResult, output_dir: Path) -> Path:
        """Save import result to log file"""
        log_file = output_dir / f"import_log_{self.config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        log_data = {
            'connector': self.config.name,
            'source_type': self.config.source_type,
            'timestamp': result.timestamp.isoformat(),
            'success': result.success,
            'total_records': result.total_records,
            'processed_records': result.processed_records,
            'failed_records': result.failed_records,
            'success_rate': result.success_rate,
            'processing_time': result.processing_time,
            'errors': result.errors,
            'warnings': result.warnings,
            'field_mapping': self.field_mapping
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        return log_file