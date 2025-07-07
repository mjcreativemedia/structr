"""
Shopify CSV Importer

Intelligent CSV importer for Shopify product exports with automatic
field mapping and validation.
"""

import csv
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Union, Optional
import re
import time
from datetime import datetime

from ..base import BaseConnector, ConnectorConfig, ImportResult, ExportResult
from models.pdp import ProductData


class ShopifyCSVImporter(BaseConnector):
    """
    Import products from Shopify CSV exports.
    
    Supports both standard Shopify exports and custom CSV formats
    with intelligent field mapping.
    """
    
    # Standard Shopify field mappings
    SHOPIFY_FIELD_MAP = {
        'Handle': 'id',
        'Title': 'title', 
        'Body (HTML)': 'body_html',
        'Vendor': 'vendor',
        'Product Category': 'product_type',
        'Type': 'product_type',
        'Tags': 'tags',
        'Published': 'published',
        'Option1 Name': 'option1_name',
        'Option1 Value': 'option1_value',
        'Option2 Name': 'option2_name', 
        'Option2 Value': 'option2_value',
        'Option3 Name': 'option3_name',
        'Option3 Value': 'option3_value',
        'Variant SKU': 'sku',
        'Variant Grams': 'weight',
        'Variant Inventory Tracker': 'inventory_tracker',
        'Variant Inventory Qty': 'inventory_quantity',
        'Variant Inventory Policy': 'inventory_policy',
        'Variant Fulfillment Service': 'fulfillment_service',
        'Variant Price': 'price',
        'Variant Compare At Price': 'compare_at_price',
        'Variant Requires Shipping': 'requires_shipping',
        'Variant Taxable': 'taxable',
        'Variant Barcode': 'barcode',
        'Image Src': 'images',
        'Image Position': 'image_position',
        'Image Alt Text': 'image_alt',
        'Gift Card': 'gift_card',
        'SEO Title': 'seo_title',
        'SEO Description': 'seo_description',
        'Google Shopping / Google Product Category': 'google_product_category',
        'Google Shopping / Gender': 'google_gender',
        'Google Shopping / Age Group': 'google_age_group',
        'Google Shopping / MPN': 'google_mpn',
        'Google Shopping / AdWords Grouping': 'google_adwords_grouping',
        'Google Shopping / AdWords Labels': 'google_adwords_labels',
        'Google Shopping / Condition': 'google_condition',
        'Google Shopping / Custom Product': 'google_custom_product',
        'Google Shopping / Custom Label 0': 'google_custom_label_0',
        'Google Shopping / Custom Label 1': 'google_custom_label_1',
        'Google Shopping / Custom Label 2': 'google_custom_label_2',
        'Google Shopping / Custom Label 3': 'google_custom_label_3',
        'Google Shopping / Custom Label 4': 'google_custom_label_4',
        'Status': 'status'
    }
    
    def __init__(self, config: Optional[ConnectorConfig] = None):
        if config is None:
            config = ConnectorConfig(
                name="shopify_csv",
                source_type="csv",
                field_mapping=self.SHOPIFY_FIELD_MAP,
                batch_size=500
            )
        super().__init__(config)
    
    def _default_field_mapping(self) -> Dict[str, str]:
        """Return default Shopify field mapping"""
        return self.SHOPIFY_FIELD_MAP.copy()
    
    def _validate_config(self) -> None:
        """Validate Shopify connector configuration"""
        if self.config.source_type != "csv":
            raise ValueError("ShopifyCSVImporter only supports CSV source type")
    
    def detect_csv_structure(self, csv_path: Path) -> Dict[str, Any]:
        """
        Analyze CSV structure and suggest field mappings.
        
        Returns analysis including:
        - Detected columns
        - Suggested mappings
        - Data quality insights
        - Sample records
        """
        analysis = {
            'file_path': str(csv_path),
            'columns': [],
            'row_count': 0,
            'suggested_mappings': {},
            'data_quality': {},
            'sample_records': [],
            'encoding': 'utf-8',
            'delimiter': ','
        }
        
        try:
            # Try to detect encoding and delimiter
            with open(csv_path, 'rb') as f:
                raw_sample = f.read(10000)
                
            # Simple encoding detection
            try:
                raw_sample.decode('utf-8')
                analysis['encoding'] = 'utf-8'
            except UnicodeDecodeError:
                analysis['encoding'] = 'latin-1'
            
            # Read with pandas for analysis
            df = pd.read_csv(csv_path, encoding=analysis['encoding'], nrows=1000)
            
            analysis['columns'] = list(df.columns)
            analysis['row_count'] = len(df)
            
            # Suggest field mappings using fuzzy matching
            analysis['suggested_mappings'] = self._suggest_field_mappings(df.columns)
            
            # Data quality analysis
            analysis['data_quality'] = self._analyze_data_quality(df)
            
            # Sample records
            analysis['sample_records'] = df.head(3).to_dict('records')
            
        except Exception as e:
            analysis['error'] = str(e)
        
        return analysis
    
    def _suggest_field_mappings(self, columns: List[str]) -> Dict[str, str]:
        """Suggest field mappings using fuzzy string matching"""
        suggestions = {}
        
        # Exact matches first
        for col in columns:
            if col in self.SHOPIFY_FIELD_MAP:
                suggestions[col] = self.SHOPIFY_FIELD_MAP[col]
        
        # Fuzzy matches for unmapped columns
        unmapped_cols = [col for col in columns if col not in suggestions]
        
        for col in unmapped_cols:
            best_match = self._find_best_field_match(col)
            if best_match:
                suggestions[col] = best_match
        
        return suggestions
    
    def _find_best_field_match(self, column_name: str) -> Optional[str]:
        """Find best matching Structr field for column name"""
        col_lower = column_name.lower().replace(' ', '_').replace('-', '_')
        
        # Common patterns
        mapping_patterns = {
            r'.*title.*': 'title',
            r'.*name.*': 'title', 
            r'.*product.*name.*': 'title',
            r'.*description.*': 'body_html',
            r'.*body.*': 'body_html',
            r'.*content.*': 'body_html',
            r'.*price.*': 'price',
            r'.*cost.*': 'price',
            r'.*amount.*': 'price',
            r'.*sku.*': 'sku',
            r'.*code.*': 'sku',
            r'.*id.*': 'id',
            r'.*handle.*': 'id',
            r'.*slug.*': 'id',
            r'.*vendor.*': 'vendor',
            r'.*brand.*': 'vendor',
            r'.*manufacturer.*': 'vendor',
            r'.*category.*': 'product_type',
            r'.*type.*': 'product_type',
            r'.*tag.*': 'tags',
            r'.*label.*': 'tags',
            r'.*weight.*': 'weight',
            r'.*mass.*': 'weight',
            r'.*inventory.*': 'inventory_quantity',
            r'.*stock.*': 'inventory_quantity',
            r'.*quantity.*': 'inventory_quantity',
            r'.*image.*': 'images',
            r'.*photo.*': 'images',
            r'.*picture.*': 'images',
            r'.*status.*': 'status',
            r'.*published.*': 'published',
            r'.*active.*': 'published',
            r'.*barcode.*': 'barcode',
            r'.*upc.*': 'barcode',
            r'.*ean.*': 'barcode',
        }
        
        for pattern, field in mapping_patterns.items():
            if re.match(pattern, col_lower):
                return field
        
        return None
    
    def _analyze_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data quality of the CSV"""
        quality = {
            'completeness': {},
            'data_types': {},
            'unique_values': {},
            'issues': []
        }
        
        for col in df.columns:
            # Completeness
            non_null_count = df[col].notna().sum()
            quality['completeness'][col] = {
                'filled': int(non_null_count),
                'total': len(df),
                'percentage': round((non_null_count / len(df)) * 100, 2)
            }
            
            # Data types
            quality['data_types'][col] = str(df[col].dtype)
            
            # Unique values (for categorical columns)
            unique_count = df[col].nunique()
            quality['unique_values'][col] = {
                'count': int(unique_count),
                'percentage': round((unique_count / len(df)) * 100, 2)
            }
            
            # Quality issues
            if non_null_count == 0:
                quality['issues'].append(f"Column '{col}' is completely empty")
            elif non_null_count < len(df) * 0.5:
                quality['issues'].append(f"Column '{col}' is more than 50% empty")
        
        return quality
    
    def import_data(self, source: Union[str, Path]) -> ImportResult:
        """Import products from Shopify CSV file"""
        start_time = time.time()
        csv_path = Path(source)
        
        if not csv_path.exists():
            return ImportResult(
                success=False,
                total_records=0,
                processed_records=0,
                failed_records=0,
                errors=[f"CSV file not found: {csv_path}"]
            )
        
        result = ImportResult(
            success=True,
            total_records=0,
            processed_records=0,
            failed_records=0
        )
        
        try:
            # Detect CSV structure
            structure = self.detect_csv_structure(csv_path)
            if 'error' in structure:
                result.success = False
                result.errors.append(f"CSV analysis failed: {structure['error']}")
                return result
            
            # Read CSV with detected settings
            df = pd.read_csv(
                csv_path, 
                encoding=structure['encoding']
            )
            
            result.total_records = len(df)
            
            # Group by product handle (Shopify exports have multiple rows per product)
            if 'Handle' in df.columns:
                products_data = self._group_shopify_variants(df)
            else:
                # Treat each row as a separate product
                products_data = df.to_dict('records')
            
            # Process each product
            for raw_product in products_data:
                try:
                    product = self.normalize_product(raw_product)
                    result.imported_products.append(product)
                    result.processed_records += 1
                    
                except Exception as e:
                    result.failed_records += 1
                    result.errors.append(f"Failed to process product: {str(e)}")
                    
                    # Continue processing if batch size allows
                    if len(result.errors) > 10:  # Limit error logging
                        result.errors.append("... additional errors truncated")
                        break
            
            # Calculate success
            result.success = result.processed_records > 0 and result.failed_records < result.total_records
            
            if result.processed_records == 0:
                result.warnings.append("No products could be processed")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Import failed: {str(e)}")
        
        result.processing_time = time.time() - start_time
        return result
    
    def _group_shopify_variants(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Group Shopify CSV rows by product handle.
        
        Shopify exports have one row per variant, we need to combine them
        into single products with variant arrays.
        """
        products = []
        
        # Group by Handle
        grouped = df.groupby('Handle')
        
        for handle, group in grouped:
            # Take first row for main product data
            main_row = group.iloc[0].to_dict()
            
            # Collect variants from all rows
            variants = []
            images = []
            
            for _, row in group.iterrows():
                variant_data = {}
                
                # Extract variant-specific fields
                variant_fields = [
                    'Variant SKU', 'Variant Price', 'Variant Compare At Price',
                    'Variant Grams', 'Variant Inventory Qty', 'Variant Barcode',
                    'Option1 Value', 'Option2 Value', 'Option3 Value'
                ]
                
                for field in variant_fields:
                    if field in row and pd.notna(row[field]):
                        variant_data[field] = row[field]
                
                if variant_data:  # Only add if has variant data
                    variants.append(variant_data)
                
                # Collect images
                if 'Image Src' in row and pd.notna(row['Image Src']):
                    if row['Image Src'] not in images:
                        images.append(row['Image Src'])
            
            # Add variants and images to main product
            main_row['variants'] = variants
            main_row['images'] = images
            
            products.append(main_row)
        
        return products
    
    def export_data(self, products: List[ProductData], destination: Union[str, Path]) -> ExportResult:
        """Export products to Shopify CSV format"""
        start_time = time.time()
        output_path = Path(destination)
        
        result = ExportResult(
            success=True,
            exported_count=0,
            output_path=output_path,
            format="csv"
        )
        
        try:
            # Convert products to Shopify CSV format
            rows = []
            
            for product in products:
                # Handle products with variants
                if product.variants and len(product.variants) > 0:
                    for i, variant in enumerate(product.variants):
                        row = self._product_to_shopify_row(product, variant, i == 0)
                        rows.append(row)
                else:
                    # Single variant product
                    row = self._product_to_shopify_row(product, None, True)
                    rows.append(row)
            
            # Write to CSV
            if rows:
                df = pd.DataFrame(rows)
                df.to_csv(output_path, index=False, encoding='utf-8')
                result.exported_count = len(products)
            else:
                result.success = False
                result.errors.append("No products to export")
        
        except Exception as e:
            result.success = False
            result.errors.append(f"Export failed: {str(e)}")
        
        result.processing_time = time.time() - start_time
        return result
    
    def _product_to_shopify_row(self, product: ProductData, variant: Optional[Dict] = None, is_main_row: bool = True) -> Dict[str, Any]:
        """Convert ProductData to Shopify CSV row format"""
        row = {}
        
        # Main product fields (only in first row)
        if is_main_row:
            row.update({
                'Handle': product.id,
                'Title': product.title,
                'Body (HTML)': product.body_html,
                'Vendor': product.vendor,
                'Type': product.product_type,
                'Tags': ', '.join(product.tags) if product.tags else '',
                'Published': str(product.published).upper(),
                'SEO Title': product.seo_title,
                'SEO Description': product.seo_description,
                'Status': product.status
            })
            
            # Images (first image only in main row)
            if product.images:
                row['Image Src'] = product.images[0]
        
        # Variant fields
        if variant:
            row.update({
                'Variant SKU': variant.get('sku', product.sku),
                'Variant Price': variant.get('price', product.price),
                'Variant Compare At Price': variant.get('compare_at_price', product.compare_at_price),
                'Variant Grams': variant.get('weight', product.weight),
                'Variant Inventory Qty': variant.get('inventory_quantity', product.inventory_quantity),
                'Variant Barcode': variant.get('barcode', product.barcode)
            })
        else:
            # Single variant
            row.update({
                'Variant SKU': product.sku,
                'Variant Price': product.price,
                'Variant Compare At Price': product.compare_at_price or '',
                'Variant Grams': product.weight,
                'Variant Inventory Qty': product.inventory_quantity,
                'Variant Barcode': product.barcode
            })
        
        return row
    
    def get_available_fields(self) -> List[str]:
        """Get list of available Shopify fields"""
        return list(self.SHOPIFY_FIELD_MAP.keys())
    
    def validate_csv_format(self, csv_path: Path) -> Dict[str, Any]:
        """Validate if CSV matches expected Shopify format"""
        validation = {
            'is_valid': True,
            'format_type': 'unknown',
            'issues': [],
            'suggestions': []
        }
        
        try:
            df = pd.read_csv(csv_path, nrows=5)
            columns = set(df.columns)
            
            # Check for standard Shopify fields
            shopify_fields = set(self.SHOPIFY_FIELD_MAP.keys())
            
            if 'Handle' in columns and 'Title' in columns:
                validation['format_type'] = 'shopify_standard'
                
                # Check for missing important fields
                important_fields = {'Handle', 'Title', 'Variant Price', 'Variant SKU'}
                missing_important = important_fields - columns
                
                if missing_important:
                    validation['issues'].append(f"Missing important fields: {missing_important}")
                
            elif len(columns & shopify_fields) > 3:
                validation['format_type'] = 'shopify_partial'
                validation['suggestions'].append("Consider using standard Shopify export format")
                
            else:
                validation['format_type'] = 'custom'
                validation['suggestions'].append("Custom CSV detected - field mapping required")
                
        except Exception as e:
            validation['is_valid'] = False
            validation['issues'].append(f"CSV validation failed: {str(e)}")
        
        return validation