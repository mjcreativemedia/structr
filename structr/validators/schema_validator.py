"""
Google Product Schema Validator for Structr

Validates JSON-LD Product schema against Google Merchant Listings 
and Schema.org requirements for Rich Results eligibility.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse
import streamlit as st

from config import CONFIG


class GoogleProductSchemaValidator:
    """Validates Product schema against Google requirements"""
    
    # Based on Google's Product Schema documentation
    # https://developers.google.com/search/docs/appearance/structured-data/product
    
    REQUIRED_FIELDS = {
        'name': {
            'path': ['name'],
            'description': 'Product name/title',
            'validation': 'required_string',
            'google_docs': 'Required for all products'
        },
        'image': {
            'path': ['image'],
            'description': 'Product image URL(s)',
            'validation': 'required_image',
            'google_docs': 'Required - must be high-quality images'
        },
        'description': {
            'path': ['description'],
            'description': 'Product description',
            'validation': 'required_string',
            'google_docs': 'Required for product understanding'
        },
        'sku': {
            'path': ['sku'],
            'description': 'Stock Keeping Unit',
            'validation': 'required_string',
            'google_docs': 'Required identifier for inventory'
        },
        'offers': {
            'path': ['offers'],
            'description': 'Offer information',
            'validation': 'required_offers',
            'google_docs': 'Required - contains price and availability'
        }
    }
    
    RECOMMENDED_FIELDS = {
        'brand': {
            'path': ['brand', 'name'],
            'alt_paths': [['brand'], ['manufacturer', 'name'], ['manufacturer']],
            'description': 'Product brand',
            'validation': 'recommended_string',
            'google_docs': 'Strongly recommended for brand recognition'
        },
        'mpn': {
            'path': ['mpn'],
            'description': 'Manufacturer Part Number',
            'validation': 'recommended_string',
            'google_docs': 'Recommended for product identification'
        },
        'gtin13': {
            'path': ['gtin13'],
            'alt_paths': [['gtin'], ['gtin12'], ['gtin14'], ['upc'], ['ean']],
            'description': 'Global Trade Item Number',
            'validation': 'recommended_gtin',
            'google_docs': 'Recommended for product matching'
        },
        'aggregateRating': {
            'path': ['aggregateRating'],
            'description': 'Product ratings summary',
            'validation': 'recommended_rating',
            'google_docs': 'Recommended for rich snippets'
        },
        'review': {
            'path': ['review'],
            'description': 'Product reviews',
            'validation': 'recommended_reviews',
            'google_docs': 'Recommended for trust signals'
        }
    }
    
    OFFERS_REQUIRED_FIELDS = {
        'price': {
            'path': ['price'],
            'description': 'Offer price',
            'validation': 'required_price',
            'google_docs': 'Required in offers'
        },
        'priceCurrency': {
            'path': ['priceCurrency'],
            'description': 'Price currency code',
            'validation': 'required_currency',
            'google_docs': 'Required in offers (ISO 4217)'
        },
        'availability': {
            'path': ['availability'],
            'description': 'Product availability',
            'validation': 'required_availability',
            'google_docs': 'Required in offers'
        }
    }
    
    # Valid values for specific fields
    VALID_AVAILABILITY_VALUES = [
        'https://schema.org/InStock',
        'https://schema.org/OutOfStock',
        'https://schema.org/PreOrder',
        'https://schema.org/BackOrder',
        'https://schema.org/Discontinued',
        'https://schema.org/LimitedAvailability',
        'InStock',
        'OutOfStock',
        'PreOrder',
        'BackOrder',
        'Discontinued',
        'LimitedAvailability'
    ]
    
    VALID_CURRENCY_CODES = [
        'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'SEK', 'NZD',
        'MXN', 'SGD', 'HKD', 'NOK', 'TRY', 'RUB', 'INR', 'BRL', 'ZAR', 'KRW'
    ]
    
    def __init__(self):
        self.validation_results = {}
        self.schema_data = None
        self.offers_data = None
    
    def validate_bundle_schema(self, bundle_path: Path) -> Dict[str, Any]:
        """Validate schema for a specific bundle"""
        
        bundle_id = bundle_path.name
        
        # Try to find schema data
        schema_data = self._extract_schema_from_bundle(bundle_path)
        
        if not schema_data:
            return {
                'bundle_id': bundle_id,
                'schema_found': False,
                'error': 'No valid Product schema found',
                'google_eligible': False
            }
        
        self.schema_data = schema_data
        self.offers_data = self._extract_offers_data(schema_data)
        
        # Validate all fields
        required_results = self._validate_required_fields()
        recommended_results = self._validate_recommended_fields()
        offers_results = self._validate_offers_fields()
        
        # Calculate overall compliance
        google_eligible = self._calculate_google_eligibility(
            required_results, offers_results
        )
        
        compliance_score = self._calculate_compliance_score(
            required_results, recommended_results, offers_results
        )
        
        return {
            'bundle_id': bundle_id,
            'schema_found': True,
            'schema_type': schema_data.get('@type', 'Unknown'),
            'required_fields': required_results,
            'recommended_fields': recommended_results,
            'offers_fields': offers_results,
            'google_eligible': google_eligible,
            'compliance_score': compliance_score,
            'summary': self._generate_summary(
                required_results, recommended_results, offers_results, google_eligible
            )
        }
    
    def _extract_schema_from_bundle(self, bundle_path: Path) -> Optional[Dict[str, Any]]:
        """Extract Product schema from bundle files"""
        
        # 1. Try schema.json file first
        schema_file = bundle_path / 'schema.json'
        if schema_file.exists():
            try:
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)
                    if self._is_product_schema(schema_data):
                        return schema_data
            except (json.JSONDecodeError, Exception):
                pass
        
        # 2. Try to extract from HTML file
        html_file = bundle_path / CONFIG.HTML_FILENAME
        if html_file.exists():
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                    
                schema_data = self._extract_jsonld_from_html(html_content)
                if schema_data and self._is_product_schema(schema_data):
                    return schema_data
            except Exception:
                pass
        
        # 3. Try sync.json for generated schema
        sync_file = bundle_path / CONFIG.SYNC_FILENAME
        if sync_file.exists():
            try:
                with open(sync_file, 'r') as f:
                    sync_data = json.load(f)
                    
                # Check if schema was generated in output
                output_data = sync_data.get('output', {})
                if 'schema' in output_data:
                    schema_data = output_data['schema']
                    if self._is_product_schema(schema_data):
                        return schema_data
            except (json.JSONDecodeError, Exception):
                pass
        
        return None
    
    def _extract_jsonld_from_html(self, html_content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON-LD from HTML content"""
        
        # Pattern to find JSON-LD script tags
        jsonld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        
        matches = re.findall(jsonld_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                # Clean and parse JSON
                json_content = match.strip()
                schema_data = json.loads(json_content)
                
                # Handle array of schema objects
                if isinstance(schema_data, list):
                    for item in schema_data:
                        if self._is_product_schema(item):
                            return item
                else:
                    if self._is_product_schema(schema_data):
                        return schema_data
                        
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _is_product_schema(self, data: Any) -> bool:
        """Check if data contains Product schema"""
        
        if not isinstance(data, dict):
            return False
        
        schema_type = data.get('@type', '')
        
        # Handle string or list of types
        if isinstance(schema_type, list):
            return 'Product' in schema_type
        else:
            return schema_type == 'Product'
    
    def _extract_offers_data(self, schema_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract offers data from schema"""
        
        offers = schema_data.get('offers')
        
        if not offers:
            return None
        
        # Handle single offer or array of offers
        if isinstance(offers, list):
            return offers[0] if offers else None
        else:
            return offers
    
    def _validate_required_fields(self) -> Dict[str, Dict[str, Any]]:
        """Validate required fields"""
        
        results = {}
        
        for field_name, field_config in self.REQUIRED_FIELDS.items():
            result = self._validate_field(
                self.schema_data, field_name, field_config, required=True
            )
            results[field_name] = result
        
        return results
    
    def _validate_recommended_fields(self) -> Dict[str, Dict[str, Any]]:
        """Validate recommended fields"""
        
        results = {}
        
        for field_name, field_config in self.RECOMMENDED_FIELDS.items():
            result = self._validate_field(
                self.schema_data, field_name, field_config, required=False
            )
            results[field_name] = result
        
        return results
    
    def _validate_offers_fields(self) -> Dict[str, Dict[str, Any]]:
        """Validate offers fields"""
        
        results = {}
        
        if not self.offers_data:
            # Return all offers fields as missing
            for field_name, field_config in self.OFFERS_REQUIRED_FIELDS.items():
                results[field_name] = {
                    'present': False,
                    'valid': False,
                    'value': None,
                    'issues': ['Offers object not found'],
                    'field_config': field_config
                }
            return results
        
        for field_name, field_config in self.OFFERS_REQUIRED_FIELDS.items():
            result = self._validate_field(
                self.offers_data, field_name, field_config, required=True
            )
            results[field_name] = result
        
        return results
    
    def _validate_field(self, data: Dict[str, Any], field_name: str, 
                       field_config: Dict[str, Any], required: bool = True) -> Dict[str, Any]:
        """Validate individual field"""
        
        # Try main path first
        value = self._get_nested_value(data, field_config['path'])
        
        # Try alternative paths if main path fails
        if value is None and 'alt_paths' in field_config:
            for alt_path in field_config['alt_paths']:
                value = self._get_nested_value(data, alt_path)
                if value is not None:
                    break
        
        # Validate the value
        validation_method = field_config['validation']
        validation_result = getattr(self, f'_validate_{validation_method}')(value)
        
        return {
            'present': value is not None,
            'valid': validation_result['valid'],
            'value': value,
            'issues': validation_result['issues'],
            'recommendations': validation_result.get('recommendations', []),
            'field_config': field_config
        }
    
    def _get_nested_value(self, data: Dict[str, Any], path: List[str]) -> Any:
        """Get value from nested dictionary using path"""
        
        current = data
        
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    # Validation methods for different field types
    
    def _validate_required_string(self, value: Any) -> Dict[str, Any]:
        """Validate required string field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['Field is missing']
            }
        
        if not isinstance(value, str) or not value.strip():
            return {
                'valid': False,
                'issues': ['Field must be a non-empty string']
            }
        
        if len(value.strip()) < 3:
            return {
                'valid': False,
                'issues': ['Field too short (minimum 3 characters)']
            }
        
        return {
            'valid': True,
            'issues': []
        }
    
    def _validate_recommended_string(self, value: Any) -> Dict[str, Any]:
        """Validate recommended string field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['Recommended field is missing'],
                'recommendations': ['Adding this field improves SEO and user experience']
            }
        
        result = self._validate_required_string(value)
        if not result['valid']:
            result['recommendations'] = ['Fix this field to improve schema compliance']
        
        return result
    
    def _validate_required_image(self, value: Any) -> Dict[str, Any]:
        """Validate image field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['Image field is missing']
            }
        
        # Handle single image or array of images
        images = value if isinstance(value, list) else [value]
        
        issues = []
        valid_images = 0
        
        for img in images:
            if isinstance(img, dict):
                # Schema.org ImageObject format
                url = img.get('url') or img.get('@id')
                if url and self._is_valid_url(url):
                    valid_images += 1
                else:
                    issues.append('ImageObject missing valid URL')
            elif isinstance(img, str):
                # Direct URL
                if self._is_valid_url(img):
                    valid_images += 1
                else:
                    issues.append(f'Invalid image URL: {img[:50]}...')
            else:
                issues.append('Invalid image format')
        
        if valid_images == 0:
            return {
                'valid': False,
                'issues': issues or ['No valid images found']
            }
        
        return {
            'valid': True,
            'issues': issues,
            'recommendations': [
                'Use high-resolution images (1200px+ width)',
                'Include multiple angles/views',
                'Ensure images are accessible and fast-loading'
            ]
        }
    
    def _validate_required_offers(self, value: Any) -> Dict[str, Any]:
        """Validate offers field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['Offers field is missing']
            }
        
        # Handle single offer or array of offers
        offers = value if isinstance(value, list) else [value]
        
        if not offers:
            return {
                'valid': False,
                'issues': ['Offers array is empty']
            }
        
        issues = []
        valid_offers = 0
        
        for offer in offers:
            if not isinstance(offer, dict):
                issues.append('Offer must be an object')
                continue
            
            # Check if offer has @type
            offer_type = offer.get('@type')
            if offer_type and offer_type != 'Offer':
                issues.append(f'Invalid offer type: {offer_type}')
            
            valid_offers += 1
        
        return {
            'valid': valid_offers > 0,
            'issues': issues
        }
    
    def _validate_required_price(self, value: Any) -> Dict[str, Any]:
        """Validate price field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['Price is missing from offers']
            }
        
        # Convert to string for validation
        price_str = str(value).strip()
        
        # Remove currency symbols for validation
        clean_price = re.sub(r'[^\d\.]', '', price_str)
        
        try:
            price_float = float(clean_price)
            if price_float <= 0:
                return {
                    'valid': False,
                    'issues': ['Price must be greater than 0']
                }
        except ValueError:
            return {
                'valid': False,
                'issues': ['Price must be a valid number']
            }
        
        return {
            'valid': True,
            'issues': []
        }
    
    def _validate_required_currency(self, value: Any) -> Dict[str, Any]:
        """Validate currency field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['Currency code is missing from offers']
            }
        
        currency = str(value).upper().strip()
        
        if currency not in self.VALID_CURRENCY_CODES:
            return {
                'valid': False,
                'issues': [f'Invalid currency code: {currency}'],
                'recommendations': [f'Use ISO 4217 codes like: {", ".join(self.VALID_CURRENCY_CODES[:5])}...']
            }
        
        return {
            'valid': True,
            'issues': []
        }
    
    def _validate_required_availability(self, value: Any) -> Dict[str, Any]:
        """Validate availability field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['Availability is missing from offers']
            }
        
        availability = str(value).strip()
        
        if availability not in self.VALID_AVAILABILITY_VALUES:
            return {
                'valid': False,
                'issues': [f'Invalid availability value: {availability}'],
                'recommendations': [f'Use Schema.org values like: {", ".join(self.VALID_AVAILABILITY_VALUES[:3])}...']
            }
        
        return {
            'valid': True,
            'issues': []
        }
    
    def _validate_recommended_gtin(self, value: Any) -> Dict[str, Any]:
        """Validate GTIN field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['GTIN is missing'],
                'recommendations': ['Add GTIN/UPC/EAN for better product matching']
            }
        
        gtin = str(value).strip()
        
        # Basic GTIN validation (8, 12, 13, or 14 digits)
        if not re.match(r'^\d{8}$|^\d{12}$|^\d{13}$|^\d{14}$', gtin):
            return {
                'valid': False,
                'issues': ['GTIN must be 8, 12, 13, or 14 digits'],
                'recommendations': ['Verify GTIN format and check digits']
            }
        
        return {
            'valid': True,
            'issues': []
        }
    
    def _validate_recommended_rating(self, value: Any) -> Dict[str, Any]:
        """Validate aggregate rating field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['AggregateRating is missing'],
                'recommendations': ['Add customer ratings for rich snippets']
            }
        
        if not isinstance(value, dict):
            return {
                'valid': False,
                'issues': ['AggregateRating must be an object']
            }
        
        issues = []
        
        # Check required rating fields
        if 'ratingValue' not in value:
            issues.append('Missing ratingValue in aggregateRating')
        
        if 'reviewCount' not in value and 'ratingCount' not in value:
            issues.append('Missing reviewCount or ratingCount')
        
        # Validate rating value
        if 'ratingValue' in value:
            try:
                rating = float(value['ratingValue'])
                if not (1 <= rating <= 5):
                    issues.append('ratingValue should be between 1 and 5')
            except (ValueError, TypeError):
                issues.append('ratingValue must be a number')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    def _validate_recommended_reviews(self, value: Any) -> Dict[str, Any]:
        """Validate reviews field"""
        
        if value is None:
            return {
                'valid': False,
                'issues': ['Reviews are missing'],
                'recommendations': ['Add customer reviews for trust and SEO']
            }
        
        # Handle single review or array of reviews
        reviews = value if isinstance(value, list) else [value]
        
        if not reviews:
            return {
                'valid': False,
                'issues': ['Reviews array is empty']
            }
        
        issues = []
        valid_reviews = 0
        
        for review in reviews:
            if not isinstance(review, dict):
                issues.append('Review must be an object')
                continue
            
            # Check basic review fields
            if 'reviewBody' not in review and 'description' not in review:
                issues.append('Review missing reviewBody or description')
            
            if 'author' not in review:
                issues.append('Review missing author')
            
            if 'reviewRating' not in review:
                issues.append('Review missing reviewRating')
            
            if len(issues) == 0:
                valid_reviews += 1
        
        return {
            'valid': valid_reviews > 0,
            'issues': issues[:3]  # Limit issues for readability
        }
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if string is a valid URL"""
        
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _calculate_google_eligibility(self, required_results: Dict, offers_results: Dict) -> bool:
        """Calculate if product is eligible for Google Rich Results"""
        
        # All required fields must be valid
        required_valid = all(
            result['present'] and result['valid'] 
            for result in required_results.values()
        )
        
        # All offers fields must be valid
        offers_valid = all(
            result['present'] and result['valid'] 
            for result in offers_results.values()
        )
        
        return required_valid and offers_valid
    
    def _calculate_compliance_score(self, required_results: Dict, 
                                  recommended_results: Dict, offers_results: Dict) -> float:
        """Calculate overall compliance score (0-100)"""
        
        # Required fields: 60% weight
        required_score = sum(
            1 for result in required_results.values() 
            if result['present'] and result['valid']
        ) / len(required_results) if required_results else 0
        
        # Offers fields: 25% weight  
        offers_score = sum(
            1 for result in offers_results.values()
            if result['present'] and result['valid']
        ) / len(offers_results) if offers_results else 0
        
        # Recommended fields: 15% weight
        recommended_score = sum(
            1 for result in recommended_results.values()
            if result['present'] and result['valid']
        ) / len(recommended_results) if recommended_results else 0
        
        # Total score
        total_score = (required_score * 0.6) + (offers_score * 0.25) + (recommended_score * 0.15)
        
        return round(total_score * 100, 1)
    
    def _generate_summary(self, required_results: Dict, recommended_results: Dict, 
                         offers_results: Dict, google_eligible: bool) -> Dict[str, Any]:
        """Generate validation summary"""
        
        required_passed = sum(
            1 for result in required_results.values() 
            if result['present'] and result['valid']
        )
        
        recommended_passed = sum(
            1 for result in recommended_results.values()
            if result['present'] and result['valid']
        )
        
        offers_passed = sum(
            1 for result in offers_results.values()
            if result['present'] and result['valid']
        )
        
        total_issues = []
        for results in [required_results, recommended_results, offers_results]:
            for result in results.values():
                total_issues.extend(result['issues'])
        
        return {
            'google_eligible': google_eligible,
            'required_passed': required_passed,
            'required_total': len(required_results),
            'recommended_passed': recommended_passed,
            'recommended_total': len(recommended_results),
            'offers_passed': offers_passed,
            'offers_total': len(offers_results),
            'total_issues': len(total_issues),
            'critical_issues': len([
                issue for results in [required_results, offers_results]
                for result in results.values()
                for issue in result['issues']
            ])
        }


def validate_all_bundles() -> List[Dict[str, Any]]:
    """Validate schema for all available bundles"""
    
    validator = GoogleProductSchemaValidator()
    results = []
    
    bundles_dir = CONFIG.get_bundles_dir()
    
    if not bundles_dir.exists():
        return results
    
    for bundle_dir in bundles_dir.iterdir():
        if bundle_dir.is_dir():
            try:
                result = validator.validate_bundle_schema(bundle_dir)
                results.append(result)
            except Exception as e:
                results.append({
                    'bundle_id': bundle_dir.name,
                    'schema_found': False,
                    'error': f'Validation error: {str(e)}',
                    'google_eligible': False
                })
    
    return results


def validate_single_bundle(bundle_id: str) -> Optional[Dict[str, Any]]:
    """Validate schema for a single bundle"""
    
    bundle_path = CONFIG.get_bundle_path(bundle_id)
    
    if not bundle_path.exists():
        return None
    
    validator = GoogleProductSchemaValidator()
    return validator.validate_bundle_schema(bundle_path)