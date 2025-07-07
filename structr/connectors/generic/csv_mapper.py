"""
Generic CSV Mapper

Flexible CSV import/export with intelligent field mapping
for any product catalog format.
"""

import csv
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Tuple
import json
import re
import time
from datetime import datetime

from ..base import BaseConnector, ConnectorConfig, ImportResult, ExportResult
from models.pdp import ProductData


class GenericCSVMapper(BaseConnector):
    """
    Generic CSV mapper for any product catalog format.
    
    Features:
    - Automatic field detection and mapping
    - Custom mapping configuration
    - Data type inference
    - Validation and cleaning
    - Multiple export formats
    """
    
    def __init__(self, config: Optional[ConnectorConfig] = None):
        if config is None:
            config = ConnectorConfig(
                name="generic_csv",
                source_type="csv",
                batch_size=1000
            )
        super().__init__(config)
        
        # Cache for detected mappings
        self._detected_mappings: Dict[str, str] = {}
        self._column_types: Dict[str, str] = {}
    
    def _default_field_mapping(self) -> Dict[str, str]:
        """Return flexible field mapping patterns"""
        return {
            # Common product fields
            'id': 'id',
            'product_id': 'id',
            'handle': 'id',
            'slug': 'id',
            'name': 'title',
            'title': 'title',
            'product_name': 'title',
            'description': 'body_html',
            'body': 'body_html',
            'content': 'body_html',
            'details': 'body_html',
            'brand': 'vendor',
            'vendor': 'vendor',
            'manufacturer': 'vendor',
            'category': 'product_type',
            'type': 'product_type',
            'product_type': 'product_type',
            'price': 'price',
            'cost': 'price',
            'amount': 'price',
            'sku': 'sku',
            'code': 'sku',
            'product_code': 'sku',
            'weight': 'weight',
            'mass': 'weight',
            'inventory': 'inventory_quantity',
            'stock': 'inventory_quantity',
            'quantity': 'inventory_quantity',
            'tags': 'tags',
            'keywords': 'tags',
            'labels': 'tags',
            'image': 'images',
            'images': 'images',
            'photo': 'images',
            'picture': 'images',
            'status': 'status',
            'state': 'status',
            'published': 'published',
            'active': 'published',
            'visible': 'published',
            'barcode': 'barcode',
            'upc': 'barcode',
            'ean': 'barcode'
        }
    
    def _validate_config(self) -> None:
        """Validate generic CSV mapper configuration"""
        if self.config.source_type != "csv":
            raise ValueError("GenericCSVMapper only supports CSV source type")
    
    def analyze_csv_structure(self, csv_path: Path, sample_size: int = 1000) -> Dict[str, Any]:
        """
        Comprehensive CSV analysis and mapping suggestions.
        
        Returns detailed analysis including:
        - Column detection and types
        - Data quality metrics  
        - Suggested field mappings
        - Sample data
        - Recommendations
        """
        analysis = {
            'file_info': {
                'path': str(csv_path),
                'size_mb': round(csv_path.stat().st_size / (1024 * 1024), 2),
                'encoding': 'utf-8',
                'delimiter': ',',
                'has_header': True
            },
            'columns': {},
            'row_count': 0,
            'data_quality': {
                'overall_score': 0,
                'completeness': {},
                'consistency': {},
                'issues': []
            },
            'suggested_mappings': {},
            'mapping_confidence': {},
            'sample_data': [],
            'recommendations': []
        }
        
        try:
            # Detect encoding and delimiter
            encoding_info = self._detect_csv_encoding(csv_path)
            analysis['file_info'].update(encoding_info)
            
            # Read sample for analysis
            df = pd.read_csv(
                csv_path,
                encoding=analysis['file_info']['encoding'],
                delimiter=analysis['file_info']['delimiter'],
                nrows=sample_size
            )
            
            analysis['row_count'] = len(df)
            
            # Analyze each column
            for col in df.columns:
                col_analysis = self._analyze_column(df[col], col)
                analysis['columns'][col] = col_analysis
            
            # Generate field mapping suggestions
            mapping_results = self._suggest_advanced_mappings(df.columns, df)
            analysis['suggested_mappings'] = mapping_results['mappings']
            analysis['mapping_confidence'] = mapping_results['confidence']
            
            # Data quality assessment
            analysis['data_quality'] = self._assess_data_quality(df)
            
            # Sample data
            analysis['sample_data'] = df.head(3).to_dict('records')
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_recommendations(analysis)
            
        except Exception as e:
            analysis['error'] = str(e)
        
        return analysis
    
    def _detect_csv_encoding(self, csv_path: Path) -> Dict[str, str]:
        """Detect CSV encoding and delimiter"""
        info = {'encoding': 'utf-8', 'delimiter': ',', 'has_header': True}
        
        try:
            # Read raw sample
            with open(csv_path, 'rb') as f:
                raw_sample = f.read(10000)
            
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    decoded = raw_sample.decode(encoding)
                    info['encoding'] = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            # Detect delimiter
            sample_lines = decoded.split('\n')[:5]
            delimiter_counts = {}
            
            for delimiter in [',', ';', '\t', '|']:
                count = sum(line.count(delimiter) for line in sample_lines)
                if count > 0:
                    delimiter_counts[delimiter] = count
            
            if delimiter_counts:
                info['delimiter'] = max(delimiter_counts, key=delimiter_counts.get)
            
            # Check for header
            if len(sample_lines) >= 2:
                first_line = sample_lines[0].split(info['delimiter'])
                second_line = sample_lines[1].split(info['delimiter'])
                
                # Header likely if first row has no numbers and second does
                first_has_numbers = any(self._is_number(cell) for cell in first_line)
                second_has_numbers = any(self._is_number(cell) for cell in second_line)
                
                info['has_header'] = not first_has_numbers and second_has_numbers
        
        except Exception:
            pass  # Use defaults
        
        return info
    
    def _analyze_column(self, series: pd.Series, column_name: str) -> Dict[str, Any]:
        """Analyze individual column characteristics"""
        analysis = {
            'name': column_name,
            'data_type': str(series.dtype),
            'inferred_type': self._infer_column_type(series),
            'completeness': {
                'total': len(series),
                'filled': series.notna().sum(),
                'empty': series.isna().sum(),
                'percentage': round((series.notna().sum() / len(series)) * 100, 2)
            },
            'unique_values': {
                'count': series.nunique(),
                'percentage': round((series.nunique() / len(series)) * 100, 2),
                'samples': series.dropna().unique()[:10].tolist()
            },
            'statistics': {},
            'quality_issues': []
        }
        
        # Type-specific analysis
        if analysis['inferred_type'] == 'numeric':
            analysis['statistics'] = {
                'min': float(series.min()) if series.notna().any() else None,
                'max': float(series.max()) if series.notna().any() else None,
                'mean': float(series.mean()) if series.notna().any() else None,
                'median': float(series.median()) if series.notna().any() else None
            }
        elif analysis['inferred_type'] == 'text':
            analysis['statistics'] = {
                'avg_length': series.str.len().mean() if series.notna().any() else 0,
                'max_length': series.str.len().max() if series.notna().any() else 0,
                'min_length': series.str.len().min() if series.notna().any() else 0
            }
        
        # Quality issues
        if analysis['completeness']['percentage'] < 50:
            analysis['quality_issues'].append("High percentage of missing values")
        
        if analysis['inferred_type'] == 'mixed':
            analysis['quality_issues'].append("Inconsistent data types")
        
        return analysis
    
    def _infer_column_type(self, series: pd.Series) -> str:
        """Infer the semantic type of a column"""
        non_null = series.dropna()
        
        if len(non_null) == 0:
            return 'empty'
        
        # Check for numeric
        numeric_count = sum(1 for x in non_null if self._is_number(x))
        numeric_ratio = numeric_count / len(non_null)
        
        if numeric_ratio > 0.8:
            return 'numeric'
        elif numeric_ratio > 0.3:
            return 'mixed'
        
        # Check for boolean
        bool_values = {'true', 'false', 'yes', 'no', '1', '0', 'y', 'n'}
        bool_count = sum(1 for x in non_null if str(x).lower().strip() in bool_values)
        bool_ratio = bool_count / len(non_null)
        
        if bool_ratio > 0.8:
            return 'boolean'
        
        # Check for URL/image
        url_count = sum(1 for x in non_null if self._is_url(str(x)))
        if url_count / len(non_null) > 0.5:
            return 'url'
        
        # Check for email
        email_count = sum(1 for x in non_null if '@' in str(x) and '.' in str(x))
        if email_count / len(non_null) > 0.5:
            return 'email'
        
        return 'text'
    
    def _is_number(self, value: Any) -> bool:
        """Check if value can be converted to a number"""
        try:
            # Remove common non-numeric characters
            clean_value = str(value).replace(',', '').replace('$', '').replace('%', '').strip()
            float(clean_value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _is_url(self, value: str) -> bool:
        """Check if value looks like a URL"""
        return value.startswith(('http://', 'https://', 'ftp://')) or '.' in value and '/' in value
    
    def _suggest_advanced_mappings(self, columns: List[str], df: pd.DataFrame) -> Dict[str, Dict]:
        """Advanced field mapping with confidence scores"""
        mappings = {}
        confidence = {}
        
        for col in columns:
            best_match, score = self._find_best_field_match(col, df[col])
            if best_match and score > 0.3:  # Minimum confidence threshold
                mappings[col] = best_match
                confidence[col] = score
        
        return {'mappings': mappings, 'confidence': confidence}
    
    def _find_best_field_match(self, column_name: str, series: pd.Series) -> Tuple[Optional[str], float]:
        """Find best matching Structr field with confidence score"""
        col_lower = column_name.lower().replace(' ', '_').replace('-', '_')
        
        # Exact matches get highest score
        if col_lower in self._default_field_mapping():
            return self._default_field_mapping()[col_lower], 1.0
        
        best_match = None
        best_score = 0.0
        
        # Pattern-based matching with data validation
        patterns_with_validation = [
            (r'.*id.*', 'id', lambda s: self._validate_id_field(s)),
            (r'.*(title|name).*', 'title', lambda s: self._validate_text_field(s, min_length=3)),
            (r'.*(desc|content|body).*', 'body_html', lambda s: self._validate_text_field(s, min_length=10)),
            (r'.*(price|cost|amount).*', 'price', lambda s: self._validate_numeric_field(s)),
            (r'.*sku.*', 'sku', lambda s: self._validate_text_field(s, max_length=50)),
            (r'.*(vendor|brand|manufacturer).*', 'vendor', lambda s: self._validate_text_field(s)),
            (r'.*(category|type).*', 'product_type', lambda s: self._validate_text_field(s)),
            (r'.*(weight|mass).*', 'weight', lambda s: self._validate_numeric_field(s)),
            (r'.*(inventory|stock|quantity).*', 'inventory_quantity', lambda s: self._validate_numeric_field(s, integer=True)),
            (r'.*(tag|keyword|label).*', 'tags', lambda s: self._validate_text_field(s)),
            (r'.*(image|photo|picture).*', 'images', lambda s: self._validate_url_field(s)),
            (r'.*(status|state).*', 'status', lambda s: self._validate_status_field(s)),
            (r'.*(published|active|visible).*', 'published', lambda s: self._validate_boolean_field(s)),
            (r'.*(barcode|upc|ean).*', 'barcode', lambda s: self._validate_text_field(s, max_length=20))
        ]
        
        for pattern, field, validator in patterns_with_validation:
            if re.match(pattern, col_lower):
                # Base score from pattern match
                pattern_score = 0.7
                
                # Validation score
                validation_score = validator(series)
                
                # Combined score
                total_score = pattern_score * validation_score
                
                if total_score > best_score:
                    best_match = field
                    best_score = total_score
        
        return best_match, best_score
    
    def _validate_id_field(self, series: pd.Series) -> float:
        """Validate if series looks like product IDs"""
        non_null = series.dropna()
        if len(non_null) == 0:
            return 0.0
        
        # Check uniqueness
        uniqueness = len(non_null.unique()) / len(non_null)
        
        # Check for reasonable ID patterns
        pattern_score = 0.0
        for value in non_null.head(10):
            val_str = str(value)
            if (val_str.isalnum() and len(val_str) < 50) or val_str.isdigit():
                pattern_score += 0.1
        
        return min(uniqueness + pattern_score, 1.0)
    
    def _validate_text_field(self, series: pd.Series, min_length: int = 1, max_length: int = 1000) -> float:
        """Validate if series looks like text content"""
        non_null = series.dropna()
        if len(non_null) == 0:
            return 0.0
        
        valid_count = 0
        for value in non_null.head(20):
            val_str = str(value)
            if min_length <= len(val_str) <= max_length and val_str.strip():
                valid_count += 1
        
        return valid_count / min(len(non_null), 20)
    
    def _validate_numeric_field(self, series: pd.Series, integer: bool = False) -> float:
        """Validate if series looks like numeric data"""
        non_null = series.dropna()
        if len(non_null) == 0:
            return 0.0
        
        numeric_count = 0
        for value in non_null.head(20):
            if self._is_number(value):
                if integer:
                    try:
                        float_val = float(str(value).replace(',', '').replace('$', ''))
                        if float_val.is_integer():
                            numeric_count += 1
                    except:
                        pass
                else:
                    numeric_count += 1
        
        return numeric_count / min(len(non_null), 20)
    
    def _validate_url_field(self, series: pd.Series) -> float:
        """Validate if series looks like URLs"""
        non_null = series.dropna()
        if len(non_null) == 0:
            return 0.0
        
        url_count = 0
        for value in non_null.head(20):
            if self._is_url(str(value)):
                url_count += 1
        
        return url_count / min(len(non_null), 20)
    
    def _validate_status_field(self, series: pd.Series) -> float:
        """Validate if series looks like status values"""
        non_null = series.dropna()
        if len(non_null) == 0:
            return 0.0
        
        common_statuses = {'active', 'inactive', 'draft', 'published', 'archived', 'enabled', 'disabled'}
        unique_values = set(str(v).lower().strip() for v in non_null.unique())
        
        matches = len(unique_values & common_statuses)
        return min(matches / len(unique_values), 1.0) if unique_values else 0.0
    
    def _validate_boolean_field(self, series: pd.Series) -> float:
        """Validate if series looks like boolean values"""
        non_null = series.dropna()
        if len(non_null) == 0:
            return 0.0
        
        bool_values = {'true', 'false', 'yes', 'no', '1', '0', 'y', 'n'}
        unique_values = set(str(v).lower().strip() for v in non_null.unique())
        
        matches = len(unique_values & bool_values)
        return min(matches / len(unique_values), 1.0) if unique_values else 0.0
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Comprehensive data quality assessment"""
        quality = {
            'overall_score': 0,
            'completeness': {},
            'consistency': {},
            'issues': [],
            'strengths': []
        }
        
        # Completeness analysis
        total_cells = df.size
        filled_cells = df.notna().sum().sum()
        overall_completeness = (filled_cells / total_cells) * 100
        
        quality['completeness'] = {
            'overall_percentage': round(overall_completeness, 2),
            'by_column': {col: round((df[col].notna().sum() / len(df)) * 100, 2) 
                         for col in df.columns}
        }
        
        # Consistency analysis
        consistency_score = 0
        for col in df.columns:
            col_type = self._infer_column_type(df[col])
            if col_type not in ['mixed', 'empty']:
                consistency_score += 1
        
        quality['consistency']['type_consistency'] = round((consistency_score / len(df.columns)) * 100, 2)
        
        # Issues and strengths
        if overall_completeness < 70:
            quality['issues'].append(f"Low overall completeness ({overall_completeness:.1f}%)")
        elif overall_completeness > 90:
            quality['strengths'].append(f"High data completeness ({overall_completeness:.1f}%)")
        
        if quality['consistency']['type_consistency'] < 80:
            quality['issues'].append("Inconsistent data types in some columns")
        elif quality['consistency']['type_consistency'] > 95:
            quality['strengths'].append("Consistent data types")
        
        # Calculate overall score
        quality['overall_score'] = round((overall_completeness + quality['consistency']['type_consistency']) / 2, 2)
        
        return quality
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # Data quality recommendations
        quality_score = analysis['data_quality']['overall_score']
        if quality_score < 70:
            recommendations.append("Consider data cleaning before import - low quality score detected")
        
        # Mapping recommendations
        mapped_fields = len(analysis['suggested_mappings'])
        total_fields = len(analysis['columns'])
        
        if mapped_fields < total_fields * 0.5:
            recommendations.append("Review and customize field mappings - many columns couldn't be auto-mapped")
        
        # File size recommendations
        file_size = analysis['file_info']['size_mb']
        if file_size > 100:
            recommendations.append("Large file detected - consider batch processing for better performance")
        
        # Required field checks
        required_fields = {'id', 'title', 'price'}
        mapped_values = set(analysis['suggested_mappings'].values())
        missing_required = required_fields - mapped_values
        
        if missing_required:
            recommendations.append(f"Missing required fields: {', '.join(missing_required)}")
        
        if not recommendations:
            recommendations.append("Data looks good for import!")
        
        return recommendations
    
    def import_data(self, source: Union[str, Path]) -> ImportResult:
        """Import products from generic CSV file"""
        start_time = time.time()
        csv_path = Path(source)
        
        result = ImportResult(
            success=True,
            total_records=0,
            processed_records=0,
            failed_records=0
        )
        
        if not csv_path.exists():
            result.success = False
            result.errors.append(f"CSV file not found: {csv_path}")
            return result
        
        try:
            # Analyze CSV structure if not cached
            if not self._detected_mappings:
                analysis = self.analyze_csv_structure(csv_path)
                if 'error' in analysis:
                    result.success = False
                    result.errors.append(f"CSV analysis failed: {analysis['error']}")
                    return result
                
                self._detected_mappings = analysis['suggested_mappings']
                
                # Use detected mappings if no custom mapping provided
                if not self.field_mapping or self.field_mapping == self._default_field_mapping():
                    self.field_mapping = self._detected_mappings
            
            # Read CSV with proper settings
            df = pd.read_csv(csv_path, encoding='utf-8')
            result.total_records = len(df)
            
            # Process in batches
            batch_size = self.config.batch_size
            
            for start_idx in range(0, len(df), batch_size):
                end_idx = min(start_idx + batch_size, len(df))
                batch_df = df.iloc[start_idx:end_idx]
                
                for _, row in batch_df.iterrows():
                    try:
                        product = self.normalize_product(row.to_dict())
                        result.imported_products.append(product)
                        result.processed_records += 1
                        
                    except Exception as e:
                        result.failed_records += 1
                        result.errors.append(f"Row {start_idx + len(result.imported_products) + result.failed_records}: {str(e)}")
                        
                        # Limit error logging
                        if len(result.errors) > 20:
                            result.errors.append("... additional errors truncated")
                            break
            
            result.success = result.processed_records > 0
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Import failed: {str(e)}")
        
        result.processing_time = time.time() - start_time
        return result
    
    def export_data(self, products: List[ProductData], destination: Union[str, Path]) -> ExportResult:
        """Export products to CSV format"""
        start_time = time.time()
        output_path = Path(destination)
        
        result = ExportResult(
            success=True,
            exported_count=0,
            output_path=output_path,
            format="csv"
        )
        
        try:
            # Convert products to CSV format
            rows = []
            
            for product in products:
                row = self._product_to_csv_row(product)
                rows.append(row)
            
            if rows:
                # Create DataFrame and export
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
    
    def _product_to_csv_row(self, product: ProductData) -> Dict[str, Any]:
        """Convert ProductData to CSV row format"""
        # Use reverse field mapping if available
        reverse_mapping = {v: k for k, v in self.field_mapping.items()} if self.field_mapping else {}
        
        row = {}
        product_dict = product.dict()
        
        for structr_field, value in product_dict.items():
            if structr_field in reverse_mapping:
                csv_field = reverse_mapping[structr_field]
            else:
                csv_field = structr_field
            
            # Format special fields
            if isinstance(value, list):
                row[csv_field] = ', '.join(str(v) for v in value)
            elif isinstance(value, dict):
                row[csv_field] = json.dumps(value)
            else:
                row[csv_field] = value
        
        return row
    
    def create_custom_mapping(self, csv_path: Path, mapping_config: Dict[str, str]) -> Dict[str, Any]:
        """Create and validate custom field mapping"""
        result = {
            'success': True,
            'mapping': mapping_config,
            'validation': {},
            'issues': []
        }
        
        try:
            # Analyze CSV to validate mapping
            analysis = self.analyze_csv_structure(csv_path, sample_size=100)
            available_columns = set(analysis['columns'].keys())
            mapped_columns = set(mapping_config.keys())
            
            # Check for invalid column mappings
            invalid_columns = mapped_columns - available_columns
            if invalid_columns:
                result['issues'].append(f"Invalid columns in mapping: {invalid_columns}")
            
            # Validate mapped fields against Structr schema
            valid_structr_fields = set(self._default_field_mapping().values())
            mapped_structr_fields = set(mapping_config.values())
            invalid_structr_fields = mapped_structr_fields - valid_structr_fields
            
            if invalid_structr_fields:
                result['issues'].append(f"Invalid Structr fields: {invalid_structr_fields}")
            
            # Store validated mapping
            if not result['issues']:
                self.field_mapping = mapping_config
                self._detected_mappings = mapping_config
            else:
                result['success'] = False
        
        except Exception as e:
            result['success'] = False
            result['issues'].append(f"Mapping validation failed: {str(e)}")
        
        return result