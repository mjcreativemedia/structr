"""
Generic PIM Connector

Flexible connector for Product Information Management (PIM) systems
and headless CMS platforms like Contentful, Strapi, etc.
"""

import requests
import json
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Iterator
from urllib.parse import urljoin
import time
from datetime import datetime

from ..base import BaseConnector, ConnectorConfig, ImportResult, ExportResult
from models.pdp import ProductData


class PIMConnector(BaseConnector):
    """
    Generic connector for PIM systems and headless CMS.
    
    Supports:
    - REST API integration
    - GraphQL queries  
    - Webhook endpoints
    - File-based sync (JSON/XML)
    - Custom field mapping
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.session = requests.Session()
        self._setup_authentication()
    
    def _default_field_mapping(self) -> Dict[str, str]:
        """Return generic PIM field mapping"""
        return {
            'id': 'id',
            'name': 'title',
            'title': 'title',
            'description': 'body_html',
            'content': 'body_html', 
            'brand': 'vendor',
            'vendor': 'vendor',
            'category': 'product_type',
            'type': 'product_type',
            'price': 'price',
            'cost': 'price',
            'sku': 'sku',
            'code': 'sku',
            'weight': 'weight',
            'inventory': 'inventory_quantity',
            'stock': 'inventory_quantity',
            'tags': 'tags',
            'images': 'images',
            'status': 'status',
            'published': 'published',
            'active': 'published'
        }
    
    def _validate_config(self) -> None:
        """Validate PIM connector configuration"""
        if self.config.source_type not in ['api', 'webhook', 'file']:
            raise ValueError(f"Unsupported source type: {self.config.source_type}")
        
        if self.config.source_type == 'api':
            if 'base_url' not in self.config.credentials:
                raise ValueError("API base_url required in credentials")
    
    def _setup_authentication(self) -> None:
        """Setup authentication for API requests"""
        creds = self.config.credentials
        
        if 'api_key' in creds:
            # API Key authentication
            self.session.headers.update({
                'Authorization': f"Bearer {creds['api_key']}"
            })
        elif 'username' in creds and 'password' in creds:
            # Basic authentication  
            self.session.auth = (creds['username'], creds['password'])
        elif 'headers' in creds:
            # Custom headers
            self.session.headers.update(creds['headers'])
    
    def test_connection(self) -> bool:
        """Test connection to PIM system"""
        if self.config.source_type != 'api':
            return True
        
        try:
            base_url = self.config.credentials.get('base_url')
            health_endpoint = self.config.credentials.get('health_endpoint', '/health')
            
            response = self.session.get(
                urljoin(base_url, health_endpoint),
                timeout=self.config.timeout
            )
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def get_available_fields(self) -> List[str]:
        """Get available fields from PIM system"""
        if self.config.source_type != 'api':
            return []
        
        try:
            # Try to fetch schema or sample record
            base_url = self.config.credentials.get('base_url')
            schema_endpoint = self.config.credentials.get('schema_endpoint', '/schema')
            
            response = self.session.get(
                urljoin(base_url, schema_endpoint),
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                schema_data = response.json()
                return self._extract_fields_from_schema(schema_data)
                
        except Exception:
            pass
        
        return list(self._default_field_mapping().keys())
    
    def _extract_fields_from_schema(self, schema_data: Dict) -> List[str]:
        """Extract field names from API schema response"""
        fields = []
        
        # Try different schema formats
        if 'properties' in schema_data:
            # JSON Schema format
            fields = list(schema_data['properties'].keys())
        elif 'fields' in schema_data:
            # Custom fields format
            fields = [f['name'] for f in schema_data['fields'] if 'name' in f]
        elif isinstance(schema_data, list) and schema_data:
            # Array of field definitions
            fields = [f.get('name', f.get('key', '')) for f in schema_data]
        elif isinstance(schema_data, dict):
            # Flat dictionary - use keys
            fields = list(schema_data.keys())
        
        return [f for f in fields if f]  # Filter empty strings
    
    def import_data(self, source: Union[str, Path, Dict]) -> ImportResult:
        """Import data from PIM system"""
        start_time = time.time()
        
        result = ImportResult(
            success=True,
            total_records=0,
            processed_records=0,
            failed_records=0
        )
        
        try:
            if self.config.source_type == 'api':
                result = self._import_from_api(source, result)
            elif self.config.source_type == 'file':
                result = self._import_from_file(source, result)
            elif self.config.source_type == 'webhook':
                result = self._import_from_webhook(source, result)
            else:
                result.success = False
                result.errors.append(f"Unsupported source type: {self.config.source_type}")
                
        except Exception as e:
            result.success = False
            result.errors.append(f"Import failed: {str(e)}")
        
        result.processing_time = time.time() - start_time
        return result
    
    def _import_from_api(self, endpoint: str, result: ImportResult) -> ImportResult:
        """Import products from REST API"""
        base_url = self.config.credentials.get('base_url')
        full_url = urljoin(base_url, endpoint) if not endpoint.startswith('http') else endpoint
        
        # Handle pagination
        page = 1
        per_page = self.config.batch_size
        has_more = True
        
        while has_more:
            try:
                # Build paginated request
                params = {
                    'page': page,
                    'per_page': per_page,
                    **self.config.filters
                }
                
                response = self.session.get(
                    full_url,
                    params=params,
                    timeout=self.config.timeout
                )
                
                if response.status_code != 200:
                    result.errors.append(f"API request failed: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                
                # Extract products from response
                products_data = self._extract_products_from_response(data)
                
                if not products_data:
                    has_more = False
                    break
                
                # Process batch
                for raw_product in products_data:
                    try:
                        product = self.normalize_product(raw_product)
                        result.imported_products.append(product)
                        result.processed_records += 1
                    except Exception as e:
                        result.failed_records += 1
                        result.errors.append(f"Failed to process product: {str(e)}")
                
                result.total_records += len(products_data)
                
                # Check if more pages available
                has_more = len(products_data) == per_page
                page += 1
                
                # Rate limiting
                if 'rate_limit_delay' in self.config.credentials:
                    time.sleep(float(self.config.credentials['rate_limit_delay']))
                
            except Exception as e:
                result.errors.append(f"API page {page} failed: {str(e)}")
                break
        
        result.success = result.processed_records > 0
        return result
    
    def _import_from_file(self, file_path: Union[str, Path], result: ImportResult) -> ImportResult:
        """Import products from JSON/XML file"""
        path = Path(file_path)
        
        if not path.exists():
            result.success = False
            result.errors.append(f"File not found: {path}")
            return result
        
        try:
            if path.suffix.lower() == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                result.success = False
                result.errors.append(f"Unsupported file format: {path.suffix}")
                return result
            
            # Extract products from file data
            products_data = self._extract_products_from_response(data)
            result.total_records = len(products_data)
            
            # Process products
            for raw_product in products_data:
                try:
                    product = self.normalize_product(raw_product)
                    result.imported_products.append(product)
                    result.processed_records += 1
                except Exception as e:
                    result.failed_records += 1
                    result.errors.append(f"Failed to process product: {str(e)}")
            
            result.success = result.processed_records > 0
            
        except Exception as e:
            result.success = False
            result.errors.append(f"File processing failed: {str(e)}")
        
        return result
    
    def _import_from_webhook(self, webhook_data: Dict, result: ImportResult) -> ImportResult:
        """Process webhook payload"""
        try:
            # Extract products from webhook payload
            products_data = self._extract_products_from_response(webhook_data)
            result.total_records = len(products_data)
            
            # Process products
            for raw_product in products_data:
                try:
                    product = self.normalize_product(raw_product)
                    result.imported_products.append(product)
                    result.processed_records += 1
                except Exception as e:
                    result.failed_records += 1
                    result.errors.append(f"Failed to process product: {str(e)}")
            
            result.success = result.processed_records > 0
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Webhook processing failed: {str(e)}")
        
        return result
    
    def _extract_products_from_response(self, data: Any) -> List[Dict[str, Any]]:
        """Extract product records from API/file response"""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Try common response structures
            for key in ['products', 'data', 'items', 'results']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            
            # Single product object
            if 'id' in data or 'name' in data or 'title' in data:
                return [data]
        
        return []
    
    def export_data(self, products: List[ProductData], destination: Union[str, Path]) -> ExportResult:
        """Export products to PIM system"""
        start_time = time.time()
        
        result = ExportResult(
            success=True,
            exported_count=0,
            format="json"
        )
        
        try:
            if self.config.source_type == 'api':
                result = self._export_to_api(products, destination, result)
            elif self.config.source_type == 'file':
                result = self._export_to_file(products, destination, result)
            else:
                result.success = False
                result.errors.append(f"Export not supported for source type: {self.config.source_type}")
                
        except Exception as e:
            result.success = False
            result.errors.append(f"Export failed: {str(e)}")
        
        result.processing_time = time.time() - start_time
        return result
    
    def _export_to_api(self, products: List[ProductData], endpoint: str, result: ExportResult) -> ExportResult:
        """Export products to API endpoint"""
        base_url = self.config.credentials.get('base_url')
        full_url = urljoin(base_url, endpoint) if not endpoint.startswith('http') else endpoint
        
        # Batch processing
        batch_size = self.config.batch_size
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            
            try:
                # Convert products to PIM format
                export_data = []
                for product in batch:
                    pim_product = self._product_to_pim_format(product)
                    export_data.append(pim_product)
                
                # Send batch to API
                response = self.session.post(
                    full_url,
                    json={'products': export_data},
                    timeout=self.config.timeout
                )
                
                if response.status_code in [200, 201]:
                    result.exported_count += len(batch)
                else:
                    result.errors.append(f"API batch {i//batch_size + 1} failed: {response.status_code}")
                
                # Rate limiting
                if 'rate_limit_delay' in self.config.credentials:
                    time.sleep(float(self.config.credentials['rate_limit_delay']))
                    
            except Exception as e:
                result.errors.append(f"Batch {i//batch_size + 1} failed: {str(e)}")
        
        result.success = result.exported_count > 0
        return result
    
    def _export_to_file(self, products: List[ProductData], file_path: Union[str, Path], result: ExportResult) -> ExportResult:
        """Export products to JSON file"""
        path = Path(file_path)
        
        try:
            # Convert products to PIM format
            export_data = []
            for product in products:
                pim_product = self._product_to_pim_format(product)
                export_data.append(pim_product)
            
            # Write to file
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'products': export_data,
                    'exported_at': datetime.now().isoformat(),
                    'count': len(export_data)
                }, f, indent=2, default=str)
            
            result.exported_count = len(products)
            result.output_path = path
            
        except Exception as e:
            result.success = False
            result.errors.append(f"File export failed: {str(e)}")
        
        return result
    
    def _product_to_pim_format(self, product: ProductData) -> Dict[str, Any]:
        """Convert ProductData to PIM system format"""
        # Reverse field mapping
        reverse_mapping = {v: k for k, v in self.field_mapping.items()}
        
        pim_product = {}
        product_dict = product.dict()
        
        for structr_field, value in product_dict.items():
            if structr_field in reverse_mapping:
                pim_field = reverse_mapping[structr_field]
                pim_product[pim_field] = value
            else:
                # Keep unmapped fields as-is
                pim_product[structr_field] = value
        
        return pim_product
    
    def create_webhook_handler(self, callback_url: str) -> Dict[str, Any]:
        """Register webhook handler with PIM system"""
        if self.config.source_type != 'api':
            return {'success': False, 'error': 'Webhooks only supported for API connections'}
        
        try:
            base_url = self.config.credentials.get('base_url')
            webhook_endpoint = self.config.credentials.get('webhook_endpoint', '/webhooks')
            
            webhook_data = {
                'url': callback_url,
                'events': ['product.created', 'product.updated', 'product.deleted'],
                'active': True
            }
            
            response = self.session.post(
                urljoin(base_url, webhook_endpoint),
                json=webhook_data,
                timeout=self.config.timeout
            )
            
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'webhook_id': response.json().get('id'),
                    'url': callback_url
                }
            else:
                return {
                    'success': False,
                    'error': f"Webhook creation failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Webhook setup failed: {str(e)}"
            }