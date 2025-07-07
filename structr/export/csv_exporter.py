"""
CSV Exporter for Structr PDP Bundles

This module exports normalized catalog data from PDP bundles into CSV format
that can be imported back into Shopify, PIM systems, or other platforms.
"""

import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup

# Import centralized configuration
from config import StructrConfig as CONFIG

from models.pdp import ProductData


class StructrCatalogExporter:
    """Exports PDP bundles to normalized CSV catalog format"""
    
    # Standard catalog fields for cross-platform compatibility
    STANDARD_FIELDS = [
        'handle',
        'title', 
        'body_html',
        'vendor',
        'product_type',
        'published',
        'template_suffix',
        'tags',
        'price',
        'compare_at_price',
        'requires_shipping',
        'taxable',
        'weight',
        'weight_unit',
        'inventory_tracker',
        'inventory_qty',
        'inventory_policy',
        'fulfillment_service',
        'sku',
        'barcode',
        'image_src',
        'image_alt_text',
        'seo_title',
        'seo_description'
    ]
    
    # Structr-specific fields for audit and tracking
    STRUCTR_FIELDS = [
        'audit_score',
        'audit_issues',
        'generation_time',
        'model_used',
        'last_updated',
        'bundle_path',
        'schema_valid',
        'metadata_complete'
    ]
    
    # Metafields that should be exported as separate columns
    METAFIELD_COLUMNS = [
        'features',
        'materials',
        'care_instructions',
        'size_guide',
        'brand_story',
        'sustainability_info'
    ]
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.bundles_dir = self.output_dir / "bundles"
    
    def export_catalog(self, output_file: str = None, 
                      include_html: bool = True,
                      include_audit_data: bool = True,
                      format_for_platform: str = "shopify") -> Dict[str, Any]:
        """Export all bundles to normalized CSV catalog"""
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"catalog_structr_{timestamp}.csv"
        
        output_path = self.output_dir / output_file
        
        # Collect all bundle data
        catalog_data = []
        errors = []
        
        if not self.bundles_dir.exists():
            return {
                "success": False,
                "error": f"Bundles directory not found: {self.bundles_dir}"
            }
        
        for product_dir in self.bundles_dir.iterdir():
            if product_dir.is_dir():
                try:
                    bundle_data = self._process_bundle(
                        product_dir, 
                        include_html, 
                        include_audit_data,
                        format_for_platform
                    )
                    if bundle_data:
                        catalog_data.append(bundle_data)
                except Exception as e:
                    errors.append(f"Failed to process {product_dir.name}: {str(e)}")
        
        if not catalog_data:
            return {
                "success": False,
                "error": "No valid bundles found to export",
                "errors": errors
            }
        
        # Write CSV
        try:
            self._write_csv(catalog_data, output_path, format_for_platform)
            
            # Generate summary
            total_products = len(catalog_data)
            avg_score = sum(row.get('audit_score', 0) for row in catalog_data) / total_products
            flagged_count = sum(1 for row in catalog_data if row.get('audit_score', 100) < 80)
            
            return {
                "success": True,
                "output_file": str(output_path),
                "total_products": total_products,
                "average_audit_score": round(avg_score, 2),
                "flagged_products": flagged_count,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write CSV: {str(e)}",
                "errors": errors
            }
    
    def _process_bundle(self, product_dir: Path, include_html: bool, 
                       include_audit_data: bool, format_for_platform: str) -> Optional[Dict[str, Any]]:
        """Process a single bundle directory into catalog row"""
        
        bundle_data = {}
        
        # Load sync.json for input data
        sync_file = product_dir / "sync.json"
        if sync_file.exists():
            with open(sync_file, 'r') as f:
                sync_data = json.load(f)
            input_data = sync_data.get('input', {})
            output_data = sync_data.get('output', {})
        else:
            input_data = {}
            output_data = {}
        
        # Load HTML content
        html_content = ""
        seo_data = {}
        if include_html:
            html_file = product_dir / "index.html"
            if html_file.exists():
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                    seo_data = self._extract_seo_data(html_content)
        
        # Load audit data
        audit_data = {}
        if include_audit_data:
            audit_file = product_dir / "audit.json"
            if audit_file.exists():
                with open(audit_file, 'r') as f:
                    audit_data = json.load(f)
        
        # Build standard catalog fields
        bundle_data.update(self._build_standard_fields(
            input_data, html_content, seo_data, format_for_platform
        ))
        
        # Add Structr-specific fields
        if include_audit_data:
            bundle_data.update(self._build_structr_fields(
                audit_data, output_data, product_dir
            ))
        
        # Add metafield columns
        bundle_data.update(self._build_metafield_columns(input_data))
        
        return bundle_data
    
    def _build_standard_fields(self, input_data: Dict, html_content: str, 
                              seo_data: Dict, format_for_platform: str) -> Dict[str, Any]:
        """Build standard catalog fields"""
        
        fields = {}
        
        # Basic product info
        fields['handle'] = input_data.get('handle', '')
        fields['title'] = input_data.get('title', '')
        fields['body_html'] = html_content if html_content else input_data.get('description', '')
        fields['vendor'] = input_data.get('brand', '')
        fields['product_type'] = input_data.get('category', '')
        fields['published'] = 'TRUE'
        fields['template_suffix'] = ''
        
        # Tags from features
        features = input_data.get('features', [])
        if isinstance(features, list):
            fields['tags'] = ', '.join(features)
        else:
            fields['tags'] = str(features) if features else ''
        
        # Pricing
        fields['price'] = input_data.get('price', '')
        fields['compare_at_price'] = ''
        
        # Shipping and inventory
        fields['requires_shipping'] = 'TRUE'
        fields['taxable'] = 'TRUE'
        fields['weight'] = input_data.get('metafields', {}).get('weight', '')
        fields['weight_unit'] = input_data.get('metafields', {}).get('weight_unit', 'lb')
        fields['inventory_tracker'] = 'shopify' if format_for_platform == 'shopify' else ''
        fields['inventory_qty'] = '10'  # Default inventory
        fields['inventory_policy'] = 'deny'
        fields['fulfillment_service'] = 'manual'
        
        # SKU and identifiers
        fields['sku'] = input_data.get('handle', '')
        fields['barcode'] = input_data.get('metafields', {}).get('upc', '')
        
        # Images
        images = input_data.get('images', [])
        if images:
            fields['image_src'] = images[0]
            fields['image_alt_text'] = f"{input_data.get('title', '')} product image"
        else:
            fields['image_src'] = ''
            fields['image_alt_text'] = ''
        
        # SEO fields from extracted HTML
        fields['seo_title'] = seo_data.get('title', input_data.get('title', ''))
        fields['seo_description'] = seo_data.get('meta_description', '')
        
        return fields
    
    def _build_structr_fields(self, audit_data: Dict, output_data: Dict, 
                             product_dir: Path) -> Dict[str, Any]:
        """Build Structr-specific tracking fields"""
        
        fields = {}
        
        fields['audit_score'] = audit_data.get('score', 0)
        
        # Combine all issues into summary
        issues = []
        issues.extend(audit_data.get('missing_fields', []))
        issues.extend(audit_data.get('flagged_issues', []))
        issues.extend(audit_data.get('schema_errors', []))
        fields['audit_issues'] = '; '.join(issues) if issues else ''
        
        fields['generation_time'] = output_data.get('generation_time', '')
        fields['model_used'] = output_data.get('model_used', '')
        fields['last_updated'] = output_data.get('timestamp', '')
        fields['bundle_path'] = str(product_dir)
        
        # Schema and metadata completeness flags
        fields['schema_valid'] = 'TRUE' if not audit_data.get('schema_errors') else 'FALSE'
        fields['metadata_complete'] = 'TRUE' if not audit_data.get('missing_fields') else 'FALSE'
        
        return fields
    
    def _build_metafield_columns(self, input_data: Dict) -> Dict[str, Any]:
        """Build metafield columns"""
        
        fields = {}
        metafields = input_data.get('metafields', {})
        
        for column in self.METAFIELD_COLUMNS:
            value = metafields.get(column, '')
            # Convert lists and dicts to JSON strings
            if isinstance(value, (list, dict)):
                fields[f'metafields_{column}'] = json.dumps(value)
            else:
                fields[f'metafields_{column}'] = str(value) if value else ''
        
        return fields
    
    def _extract_seo_data(self, html_content: str) -> Dict[str, Any]:
        """Extract SEO data from HTML content"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        seo_data = {}
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            seo_data['title'] = title_tag.text.strip()
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            seo_data['meta_description'] = meta_desc.get('content', '')
        
        return seo_data
    
    def _write_csv(self, catalog_data: List[Dict], output_path: Path, 
                   format_for_platform: str):
        """Write catalog data to CSV file"""
        
        if not catalog_data:
            raise ValueError("No data to write")
        
        # Determine field order based on platform
        if format_for_platform == "shopify":
            fieldnames = self.STANDARD_FIELDS + self.STRUCTR_FIELDS
        else:
            # Generic format - include all fields found
            all_fields = set()
            for row in catalog_data:
                all_fields.update(row.keys())
            fieldnames = sorted(list(all_fields))
        
        # Add metafield columns
        for column in self.METAFIELD_COLUMNS:
            fieldnames.append(f'metafields_{column}')
        
        # Filter fieldnames to only include fields that exist in data
        existing_fields = set()
        for row in catalog_data:
            existing_fields.update(row.keys())
        
        final_fieldnames = [f for f in fieldnames if f in existing_fields]
        
        # Write CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=final_fieldnames, 
                                  extrasaction='ignore')
            writer.writeheader()
            writer.writerows(catalog_data)
    
    def export_shopify_format(self, output_file: str = None) -> Dict[str, Any]:
        """Export in Shopify-compatible CSV format"""
        return self.export_catalog(
            output_file=output_file,
            include_html=True,
            include_audit_data=False,  # Shopify doesn't need audit data
            format_for_platform="shopify"
        )
    
    def export_audit_report(self, output_file: str = None) -> Dict[str, Any]:
        """Export CSV focused on audit data for analysis"""
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"audit_report_{timestamp}.csv"
        
        return self.export_catalog(
            output_file=output_file,
            include_html=False,
            include_audit_data=True,
            format_for_platform="audit"
        )
    
    def get_export_stats(self) -> Dict[str, Any]:
        """Get statistics about exportable bundles"""
        
        if not self.bundles_dir.exists():
            return {"error": "Bundles directory not found"}
        
        total_bundles = 0
        valid_bundles = 0
        avg_score = 0
        score_distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        
        for product_dir in self.bundles_dir.iterdir():
            if product_dir.is_dir():
                total_bundles += 1
                
                audit_file = product_dir / "audit.json"
                if audit_file.exists():
                    try:
                        with open(audit_file, 'r') as f:
                            audit_data = json.load(f)
                        
                        score = audit_data.get('score', 0)
                        avg_score += score
                        valid_bundles += 1
                        
                        if score >= 90:
                            score_distribution["excellent"] += 1
                        elif score >= 80:
                            score_distribution["good"] += 1
                        elif score >= 60:
                            score_distribution["fair"] += 1
                        else:
                            score_distribution["poor"] += 1
                            
                    except:
                        pass
        
        return {
            "total_bundles": total_bundles,
            "valid_bundles": valid_bundles,
            "average_score": round(avg_score / valid_bundles, 2) if valid_bundles > 0 else 0,
            "score_distribution": score_distribution
        }