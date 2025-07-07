"""
Unit tests for GoogleProductSchemaGenerator

Tests schema generation, validation, and compliance with Google Rich Results requirements.
"""

import pytest
import json
from datetime import datetime

from models.pdp import ProductData
from schemas.schema_generator import GoogleProductSchemaGenerator, generate_product_schema, validate_product_schema


class TestGoogleProductSchemaGenerator:
    """Test suite for GoogleProductSchemaGenerator"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.generator = GoogleProductSchemaGenerator()
        
        # Basic product data for testing
        self.basic_product = ProductData(
            handle="test-product",
            title="Test Product",
            description="A high-quality test product for testing purposes",
            price=29.99,
            brand="Test Brand"
        )
        
        # Rich product data with all fields
        self.rich_product = ProductData(
            handle="premium-shirt",
            title="Premium Cotton Shirt",
            description="Premium 100% organic cotton shirt with superior comfort and style",
            price=89.99,
            brand="Premium Brand",
            category="Clothing > Shirts",
            images=[
                "https://example.com/shirt-front.jpg",
                "https://example.com/shirt-back.jpg"
            ],
            features=[
                "100% organic cotton",
                "Machine washable",
                "Available in multiple colors"
            ],
            metafields={
                "gtin": "1234567890123",
                "mpn": "PS-001",
                "material": "Organic Cotton",
                "color": "Blue",
                "size": "Large",
                "weight": "0.5",
                "weight_unit": "LB",
                "rating": 4.5,
                "review_count": 25
            }
        )
    
    def test_generate_basic_schema(self):
        """Test generating schema with minimal product data"""
        schema = self.generator.generate_product_schema(self.basic_product)
        
        # Check required fields
        assert schema["@context"] == "https://schema.org"
        assert schema["@type"] == "Product"
        assert schema["name"] == "Test Product"
        assert schema["description"] == "A high-quality test product for testing purposes"
        assert "offers" in schema
        assert "image" in schema
        
        # Check offers structure
        offers = schema["offers"]
        assert offers["@type"] == "Offer"
        assert offers["price"] == "29.99"
        assert offers["priceCurrency"] == "USD"
        assert offers["availability"] == "https://schema.org/InStock"
    
    def test_generate_rich_schema(self):
        """Test generating schema with rich product data"""
        schema = self.generator.generate_product_schema(self.rich_product)
        
        # Check all basic fields are present
        assert schema["name"] == "Premium Cotton Shirt"
        assert schema["description"] == "Premium 100% organic cotton shirt with superior comfort and style"
        
        # Check brand object
        assert "brand" in schema
        assert schema["brand"]["@type"] == "Brand"
        assert schema["brand"]["name"] == "Premium Brand"
        
        # Check images array
        assert isinstance(schema["image"], list)
        assert len(schema["image"]) == 2
        assert "https://example.com/shirt-front.jpg" in schema["image"]
        
        # Check additional identifiers
        assert schema["sku"] == "premium-shirt"
        assert schema["model"] == "premium-shirt"
        assert schema["gtin"] == "1234567890123"
        assert schema["mpn"] == "PS-001"
        
        # Check additional properties
        assert "additionalProperty" in schema
        properties = schema["additionalProperty"]
        assert len(properties) == 3  # 3 features
        
        # Check weight
        assert "weight" in schema
        assert schema["weight"]["@type"] == "QuantitativeValue"
        assert schema["weight"]["value"] == "0.5"
        assert schema["weight"]["unitCode"] == "LB"
        
        # Check aggregate rating
        assert "aggregateRating" in schema
        rating = schema["aggregateRating"]
        assert rating["@type"] == "AggregateRating"
        assert rating["ratingValue"] == "4.5"
        assert rating["ratingCount"] == "25"
    
    def test_minimal_schema_generation(self):
        """Test minimal schema generation"""
        minimal_schema = self.generator.generate_minimal_schema(self.basic_product)
        
        # Should only have required fields
        required_keys = {"@context", "@type", "name", "description", "image", "offers"}
        assert set(minimal_schema.keys()) == required_keys
        
        # Validate minimal schema structure
        assert minimal_schema["offers"]["price"] == "29.99"
        assert len(minimal_schema["image"]) == 1
    
    def test_schema_validation_valid(self):
        """Test validation of valid schema"""
        schema = self.generator.generate_product_schema(self.rich_product)
        errors = self.generator.validate_schema(schema)
        
        assert len(errors) == 0, f"Valid schema should have no errors: {errors}"
    
    def test_schema_validation_missing_required_fields(self):
        """Test validation catches missing required fields"""
        invalid_schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Test Product"
            # Missing description, image, offers
        }
        
        errors = self.generator.validate_schema(invalid_schema)
        
        assert len(errors) > 0
        assert any("Missing required field: description" in error for error in errors)
        assert any("Missing required field: image" in error for error in errors)
        assert any("Missing required field: offers" in error for error in errors)
    
    def test_schema_validation_invalid_offers(self):
        """Test validation catches invalid offers structure"""
        schema_invalid_offers = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Test Product",
            "description": "Test description",
            "image": ["https://example.com/image.jpg"],
            "offers": {
                "@type": "InvalidType",  # Should be "Offer"
                "price": "invalid_price",  # Should be numeric string
                "priceCurrency": "USD"
                # Missing availability
            }
        }
        
        errors = self.generator.validate_schema(schema_invalid_offers)
        
        assert len(errors) > 0
        assert any("Offer @type must be 'Offer'" in error for error in errors)
        assert any("Invalid price format" in error for error in errors)
        assert any("Missing required offer field: availability" in error for error in errors)
    
    def test_schema_validation_invalid_images(self):
        """Test validation catches invalid image formats"""
        schema_invalid_images = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Test Product",
            "description": "Test description",
            "image": "not_an_array",  # Should be array
            "offers": {
                "@type": "Offer",
                "price": "29.99",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock"
            }
        }
        
        errors = self.generator.validate_schema(schema_invalid_images)
        
        assert any("Image field must be an array" in error for error in errors)
    
    def test_offers_validation_detailed(self):
        """Test detailed offers validation"""
        # Test invalid availability
        invalid_offers = {
            "@type": "Offer",
            "price": "29.99",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InvalidAvailability"
        }
        
        errors = self.generator._validate_offers(invalid_offers)
        assert any("Invalid availability value" in error for error in errors)
        
        # Test valid availability options
        valid_availabilities = [
            "https://schema.org/InStock",
            "https://schema.org/OutOfStock",
            "https://schema.org/OnlineOnly",
            "https://schema.org/InStoreOnly",
            "https://schema.org/LimitedAvailability",
            "https://schema.org/PreOrder"
        ]
        
        for availability in valid_availabilities:
            valid_offers = {
                "@type": "Offer",
                "price": "29.99",
                "priceCurrency": "USD",
                "availability": availability
            }
            
            errors = self.generator._validate_offers(valid_offers)
            availability_errors = [e for e in errors if "Invalid availability" in e]
            assert len(availability_errors) == 0
    
    def test_product_without_images(self):
        """Test schema generation for product without images"""
        product_no_images = ProductData(
            handle="no-image-product",
            title="Product Without Images",
            description="A product that has no images",
            price=19.99
        )
        
        schema = self.generator.generate_product_schema(product_no_images)
        
        # Should have placeholder image
        assert len(schema["image"]) == 1
        assert schema["image"][0].endswith("/placeholder-product.jpg")
    
    def test_product_without_price(self):
        """Test schema generation for product without price"""
        product_no_price = ProductData(
            handle="free-product",
            title="Free Product",
            description="A free product"
        )
        
        schema = self.generator.generate_product_schema(product_no_price)
        
        # Should have price as "0"
        assert schema["offers"]["price"] == "0"
    
    def test_schema_html_formatting(self):
        """Test HTML script tag formatting"""
        schema = self.generator.generate_product_schema(self.basic_product)
        html_output = self.generator.format_for_html(schema)
        
        assert html_output.startswith('<script type="application/ld+json">')
        assert html_output.endswith('</script>')
        
        # Should be valid JSON inside script tag
        json_content = html_output.replace('<script type="application/ld+json">', '')
        json_content = json_content.replace('</script>', '').strip()
        
        # Should parse as valid JSON
        parsed_schema = json.loads(json_content)
        assert parsed_schema["@type"] == "Product"
    
    def test_convenience_functions(self):
        """Test convenience functions work correctly"""
        # Test generate_product_schema function
        schema = generate_product_schema(self.basic_product)
        assert schema["@type"] == "Product"
        assert schema["name"] == "Test Product"
        
        # Test validate_product_schema function
        errors = validate_product_schema(schema)
        assert len(errors) == 0
        
        # Test with invalid schema
        invalid_schema = {"@type": "Product"}  # Missing required fields
        errors = validate_product_schema(invalid_schema)
        assert len(errors) > 0
    
    def test_custom_base_url_and_currency(self):
        """Test schema generation with custom base URL and currency"""
        schema = self.generator.generate_product_schema(
            self.basic_product,
            base_url="https://mystore.com",
            currency="EUR"
        )
        
        # Check currency in offers
        assert schema["offers"]["priceCurrency"] == "EUR"
        
        # Check URL in offers
        assert schema["offers"]["url"] == "https://mystore.com/products/test-product"
        
        # Check image URLs (when using relative images)
        product_with_relative_image = ProductData(
            handle="test",
            title="Test",
            description="Test",
            images=["images/product.jpg"]
        )
        
        schema_with_images = self.generator.generate_product_schema(
            product_with_relative_image,
            base_url="https://mystore.com"
        )
        
        assert schema_with_images["image"][0] == "https://mystore.com/images/product.jpg"


class TestSchemaEdgeCases:
    """Test edge cases and error conditions"""
    
    def setup_method(self):
        self.generator = GoogleProductSchemaGenerator()
    
    def test_empty_product_data(self):
        """Test with minimal/empty product data"""
        empty_product = ProductData(handle="", title="", description="")
        
        schema = self.generator.generate_product_schema(empty_product)
        
        # Should have fallback values
        assert schema["name"] == "Unknown Product"
        assert "High-quality" in schema["description"]
        assert len(schema["image"]) == 1
    
    def test_very_long_title_and_description(self):
        """Test validation with overly long content"""
        long_title = "x" * 100  # Very long title
        long_description = "x" * 6000  # Very long description
        
        product = ProductData(
            handle="long-content",
            title=long_title,
            description=long_description
        )
        
        schema = self.generator.generate_product_schema(product)
        errors = self.generator.validate_schema(schema)
        
        # Should flag long content
        title_errors = [e for e in errors if "Product name should be 70 characters" in e]
        desc_errors = [e for e in errors if "Description should be 5000 characters" in e]
        
        assert len(title_errors) > 0
        assert len(desc_errors) > 0
    
    def test_invalid_metafield_data_types(self):
        """Test handling of invalid metafield data types"""
        product = ProductData(
            handle="test",
            title="Test",
            description="Test",
            metafields={
                "rating": "not_a_number",  # Should be numeric
                "review_count": "also_not_a_number",
                "weight": {"invalid": "object"}  # Should be string/number
            }
        )
        
        # Should not crash, should handle gracefully
        schema = self.generator.generate_product_schema(product)
        assert schema["@type"] == "Product"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__])