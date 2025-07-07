"""
Enhanced Schema Generator with full Google Product schema parity

This module generates JSON-LD schema markup that complies with Google's
Rich Results requirements for Product structured data.

Google Requirements Reference:
https://developers.google.com/search/docs/appearance/structured-data/product
"""

import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from models.pdp import ProductData


class GoogleProductSchemaGenerator:
    """Generates Google-compliant Product schema markup"""
    
    # Required fields according to Google's documentation
    REQUIRED_FIELDS = {
        '@type': 'Product',
        'name': str,
        'image': [str, list],
        'description': str,
        'offers': dict
    }
    
    # Recommended fields for better Rich Results
    RECOMMENDED_FIELDS = {
        'brand': [str, dict],
        'model': str,
        'sku': str,
        'gtin': str,
        'mpn': str,
        'category': str,
        'aggregateRating': dict,
        'review': [dict, list]
    }
    
    def __init__(self):
        self.context = "https://schema.org"
    
    def generate_product_schema(self, product_data: ProductData, 
                              base_url: str = "https://example.com",
                              currency: str = "USD") -> Dict[str, Any]:
        """Generate complete Product schema with all required and recommended fields"""
        
        schema = {
            "@context": self.context,
            "@type": "Product"
        }
        
        # Required fields
        schema.update(self._build_required_fields(product_data, base_url, currency))
        
        # Recommended fields (when data is available)
        schema.update(self._build_recommended_fields(product_data))
        
        # Additional useful fields
        schema.update(self._build_additional_fields(product_data))
        
        return schema
    
    def _build_required_fields(self, product_data: ProductData, 
                              base_url: str, currency: str) -> Dict[str, Any]:
        """Build all required Product schema fields"""
        
        fields = {}
        
        # Name (required)
        fields["name"] = product_data.title or "Unknown Product"
        
        # Description (required)
        fields["description"] = (
            product_data.description or 
            f"High-quality {product_data.title or 'product'} from {product_data.brand or 'our collection'}"
        )
        
        # Image (required) - must be array of URLs
        if product_data.images:
            # Ensure all images are full URLs
            images = []
            for img in product_data.images:
                if img.startswith('http'):
                    images.append(img)
                else:
                    images.append(f"{base_url.rstrip('/')}/{img.lstrip('/')}")
            fields["image"] = images
        else:
            # Provide fallback placeholder image
            fields["image"] = [f"{base_url}/placeholder-product.jpg"]
        
        # Offers (required) - must include price, priceCurrency, availability
        fields["offers"] = self._build_offers_object(product_data, base_url, currency)
        
        return fields
    
    def _build_offers_object(self, product_data: ProductData, 
                           base_url: str, currency: str) -> Dict[str, Any]:
        """Build compliant Offer object"""
        
        offer = {
            "@type": "Offer",
            "priceCurrency": currency,
            "availability": "https://schema.org/InStock",  # Default to in stock
            "url": f"{base_url}/products/{product_data.handle}"
        }
        
        # Price (required for Offer)
        if product_data.price:
            offer["price"] = str(product_data.price)
        else:
            # If no price provided, mark as price on request
            offer["price"] = "0"
            offer["priceSpecification"] = {
                "@type": "PriceSpecification",
                "valueAddedTaxIncluded": True
            }
        
        # Valid from/through dates (recommended)
        now = datetime.now()
        offer["priceValidUntil"] = now.replace(year=now.year + 1).strftime("%Y-%m-%d")
        
        # Seller information (recommended)
        if product_data.brand:
            offer["seller"] = {
                "@type": "Organization",
                "name": product_data.brand
            }
        
        return offer
    
    def _build_recommended_fields(self, product_data: ProductData) -> Dict[str, Any]:
        """Build recommended fields when data is available"""
        
        fields = {}
        
        # Brand (highly recommended)
        if product_data.brand:
            fields["brand"] = {
                "@type": "Brand",
                "name": product_data.brand
            }
        
        # Model/SKU (recommended for identification)
        if product_data.handle:
            fields["model"] = product_data.handle
            fields["sku"] = product_data.handle
        
        # Category (recommended)
        if product_data.category:
            fields["category"] = product_data.category
        
        # Additional identifiers from metafields
        metafields = product_data.metafields or {}
        
        if metafields.get('gtin'):
            fields["gtin"] = metafields['gtin']
        
        if metafields.get('mpn'):
            fields["mpn"] = metafields['mpn']
        
        if metafields.get('upc'):
            fields["gtin12"] = metafields['upc']
        
        if metafields.get('ean'):
            fields["gtin13"] = metafields['ean']
        
        # Generate aggregate rating if review data exists
        if metafields.get('rating') or metafields.get('reviews'):
            fields["aggregateRating"] = self._build_aggregate_rating(metafields)
        
        return fields
    
    def _build_additional_fields(self, product_data: ProductData) -> Dict[str, Any]:
        """Build additional useful fields"""
        
        fields = {}
        
        # Product features as additionalProperty
        if product_data.features:
            fields["additionalProperty"] = []
            for feature in product_data.features:
                fields["additionalProperty"].append({
                    "@type": "PropertyValue",
                    "name": "Feature",
                    "value": feature
                })
        
        # Weight, dimensions, material from metafields
        metafields = product_data.metafields or {}
        
        if metafields.get('weight'):
            fields["weight"] = {
                "@type": "QuantitativeValue",
                "value": metafields['weight'],
                "unitCode": metafields.get('weight_unit', 'LB')
            }
        
        if metafields.get('material'):
            fields["material"] = metafields['material']
        
        if metafields.get('color'):
            fields["color"] = metafields['color']
        
        if metafields.get('size'):
            fields["size"] = metafields['size']
        
        # Manufacturer if different from brand
        if metafields.get('manufacturer'):
            fields["manufacturer"] = {
                "@type": "Organization", 
                "name": metafields['manufacturer']
            }
        
        return fields
    
    def _build_aggregate_rating(self, metafields: Dict[str, Any]) -> Dict[str, Any]:
        """Build aggregate rating from review data"""
        
        rating_value = metafields.get('rating', 4.5)  # Default good rating
        review_count = metafields.get('review_count', 1)
        
        return {
            "@type": "AggregateRating",
            "ratingValue": str(rating_value),
            "bestRating": "5",
            "worstRating": "1",
            "ratingCount": str(review_count)
        }
    
    def validate_schema(self, schema: Dict[str, Any]) -> List[str]:
        """Validate schema against Google requirements"""
        
        errors = []
        
        # Check required fields
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in schema:
                errors.append(f"Missing required field: {field}")
            elif field == 'offers':
                # Special validation for offers
                offer_errors = self._validate_offers(schema[field])
                errors.extend(offer_errors)
        
        # Validate image array
        if 'image' in schema:
            if not isinstance(schema['image'], list):
                errors.append("Image field must be an array")
            elif not schema['image']:
                errors.append("Image array cannot be empty")
            else:
                for img in schema['image']:
                    if not isinstance(img, str) or not img.startswith('http'):
                        errors.append(f"Invalid image URL: {img}")
        
        # Validate name length
        if 'name' in schema and len(schema['name']) > 70:
            errors.append("Product name should be 70 characters or less")
        
        # Validate description length
        if 'description' in schema and len(schema['description']) > 5000:
            errors.append("Description should be 5000 characters or less")
        
        return errors
    
    def _validate_offers(self, offers: Union[Dict, List]) -> List[str]:
        """Validate offers object/array"""
        
        errors = []
        
        # Normalize to list
        offers_list = offers if isinstance(offers, list) else [offers]
        
        for offer in offers_list:
            if not isinstance(offer, dict):
                errors.append("Offer must be an object")
                continue
            
            # Required offer fields
            required_offer_fields = ['@type', 'price', 'priceCurrency', 'availability']
            
            for field in required_offer_fields:
                if field not in offer:
                    errors.append(f"Missing required offer field: {field}")
            
            # Validate offer type
            if offer.get('@type') != 'Offer':
                errors.append("Offer @type must be 'Offer'")
            
            # Validate price format
            if 'price' in offer:
                try:
                    float(offer['price'])
                except (ValueError, TypeError):
                    errors.append(f"Invalid price format: {offer['price']}")
            
            # Validate availability URL
            if 'availability' in offer:
                valid_availability = [
                    'https://schema.org/InStock',
                    'https://schema.org/OutOfStock', 
                    'https://schema.org/OnlineOnly',
                    'https://schema.org/InStoreOnly',
                    'https://schema.org/LimitedAvailability',
                    'https://schema.org/PreOrder'
                ]
                if offer['availability'] not in valid_availability:
                    errors.append(f"Invalid availability value: {offer['availability']}")
        
        return errors
    
    def generate_minimal_schema(self, product_data: ProductData) -> Dict[str, Any]:
        """Generate minimal valid schema with just required fields"""
        
        return {
            "@context": self.context,
            "@type": "Product",
            "name": product_data.title or "Product",
            "description": product_data.description or f"High-quality {product_data.title or 'product'}",
            "image": product_data.images[:1] if product_data.images else ["https://example.com/placeholder.jpg"],
            "offers": {
                "@type": "Offer",
                "price": str(product_data.price or "0"),
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock"
            }
        }
    
    def format_for_html(self, schema: Dict[str, Any]) -> str:
        """Format schema as HTML script tag"""
        
        json_str = json.dumps(schema, indent=2, ensure_ascii=False)
        
        return f'''<script type="application/ld+json">
{json_str}
</script>'''


# Convenience function for quick schema generation
def generate_product_schema(product_data: ProductData, **kwargs) -> Dict[str, Any]:
    """Quick function to generate product schema"""
    generator = GoogleProductSchemaGenerator()
    return generator.generate_product_schema(product_data, **kwargs)


# Schema validation function
def validate_product_schema(schema: Dict[str, Any]) -> List[str]:
    """Quick function to validate product schema"""
    generator = GoogleProductSchemaGenerator()
    return generator.validate_schema(schema)