"""
Unit tests for PDPAuditor

Tests audit functionality for PDP bundles and HTML compliance checking.
"""

import pytest
import json
import tempfile
from pathlib import Path

from models.audit import PDPAuditor
from models.pdp import AuditResult


class TestPDPAuditor:
    """Test suite for PDPAuditor"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.auditor = PDPAuditor()
        
        # Valid HTML with all required elements
        self.valid_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Premium Cotton Shirt - Best Quality Organic Cotton</title>
            <meta name="description" content="Premium 100% organic cotton shirt with superior comfort and style. Perfect for casual and formal occasions. Machine washable and eco-friendly.">
            <meta property="og:title" content="Premium Cotton Shirt - Best Quality">
            <meta property="og:description" content="Premium 100% organic cotton shirt with superior comfort and style. Perfect for casual and formal occasions.">
            <meta property="og:image" content="https://example.com/shirt.jpg">
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Premium Cotton Shirt",
                "description": "Premium 100% organic cotton shirt",
                "image": ["https://example.com/shirt.jpg"],
                "brand": {
                    "@type": "Brand",
                    "name": "Premium Brand"
                },
                "offers": {
                    "@type": "Offer",
                    "price": "89.99",
                    "priceCurrency": "USD",
                    "availability": "https://schema.org/InStock"
                }
            }
            </script>
        </head>
        <body>
            <h1>Premium Cotton Shirt</h1>
            <p>High-quality organic cotton shirt for the modern professional.</p>
        </body>
        </html>
        '''
        
        # HTML missing required elements
        self.missing_elements_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <!-- Missing title -->
            <!-- Missing meta description -->
            <!-- Missing OG tags -->
            <!-- Missing schema -->
        </head>
        <body>
            <h1>Product</h1>
        </body>
        </html>
        '''
        
        # HTML with problematic elements
        self.problematic_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bad</title>  <!-- Too short -->
            <meta name="description" content="Short">  <!-- Too short -->
            <meta property="og:title" content="Very long title that exceeds the recommended character limit for social media">  <!-- Too long -->
            <meta property="og:description" content="">  <!-- Empty -->
            <meta property="og:image" content="">  <!-- Empty -->
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Product"
                // Missing required fields
            }
            </script>
        </head>
        <body>
            <h1>Product</h1>
        </body>
        </html>
        '''
    
    def test_analyze_valid_html(self):
        """Test analyzing valid HTML content"""
        result = self.auditor._analyze_html(self.valid_html, "test-product")
        
        assert isinstance(result, AuditResult)
        assert result.product_id == "test-product"
        assert result.score > 90  # Should have high score
        assert len(result.missing_fields) == 0
        assert len(result.metadata_issues) == 0
        assert len(result.schema_errors) == 0
    
    def test_analyze_html_missing_elements(self):
        """Test analyzing HTML with missing required elements"""
        result = self.auditor._analyze_html(self.missing_elements_html, "missing-test")
        
        assert result.product_id == "missing-test"
        assert result.score < 50  # Should have low score
        
        # Check for missing required fields
        expected_missing = ['title', 'meta_description', 'og:title', 'og:description', 'og:image', 'json_ld_schema']
        for field in expected_missing:
            if field == 'json_ld_schema':
                assert any('JSON-LD schema' in error for error in result.schema_errors)
            else:
                assert field in result.missing_fields or any(field.replace('_', ' ') in issue for issue in result.metadata_issues)
    
    def test_analyze_html_problematic_elements(self):
        """Test analyzing HTML with problematic elements"""
        result = self.auditor._analyze_html(self.problematic_html, "problem-test")
        
        assert result.product_id == "problem-test"
        assert result.score < 80  # Should have medium-low score
        
        # Check for flagged issues
        issues = result.flagged_issues + result.metadata_issues
        assert any('too short' in issue.lower() for issue in issues)
        
        # Check for schema errors
        assert len(result.schema_errors) > 0
    
    def test_validate_product_schema_valid(self):
        """Test validation of valid Product schema"""
        valid_schema = {
            "@type": "Product",
            "name": "Test Product",
            "description": "Test description",
            "image": ["https://example.com/image.jpg"],
            "brand": {"@type": "Brand", "name": "Test Brand"},
            "offers": {
                "@type": "Offer",
                "price": "29.99",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock"
            }
        }
        
        errors = self.auditor._validate_product_schema(valid_schema)
        assert len(errors) == 0
    
    def test_validate_product_schema_missing_fields(self):
        """Test validation catches missing schema fields"""
        invalid_schema = {
            "@type": "Product",
            "name": "Test Product"
            # Missing required fields
        }
        
        errors = self.auditor._validate_product_schema(invalid_schema)
        
        assert len(errors) > 0
        required_fields = ['description', 'image', 'offers', 'brand']
        for field in required_fields:
            assert any(field in error for error in errors)
    
    def test_validate_product_schema_invalid_offers(self):
        """Test validation of invalid offers structure"""
        schema_with_bad_offers = {
            "@type": "Product",
            "name": "Test Product",
            "description": "Test description",
            "image": ["https://example.com/image.jpg"],
            "brand": {"@type": "Brand", "name": "Test Brand"},
            "offers": {
                "@type": "InvalidOffer",  # Wrong type
                # Missing price and priceCurrency
            }
        }
        
        errors = self.auditor._validate_product_schema(schema_with_bad_offers)
        
        assert len(errors) > 0
        assert any("@type must be" in error for error in errors)
        assert any("price" in error for error in errors)
    
    def test_audit_pdp_bundle_with_temp_files(self):
        """Test auditing a complete PDP bundle with temporary files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = Path(temp_dir)
            
            # Create bundle files
            html_file = bundle_path / "index.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self.valid_html)
            
            sync_file = bundle_path / "sync.json"
            with open(sync_file, 'w') as f:
                json.dump({"input": {"handle": "test-product"}}, f)
            
            # Audit the bundle
            result = self.auditor.audit_pdp_bundle(str(bundle_path), "test-product")
            
            assert isinstance(result, AuditResult)
            assert result.product_id == "test-product"
            assert result.score > 0
    
    def test_audit_pdp_bundle_missing_files(self):
        """Test auditing bundle with missing files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_path = Path(temp_dir)
            
            # Don't create any files - should handle gracefully
            result = self.auditor.audit_pdp_bundle(str(bundle_path), "missing-files")
            
            assert isinstance(result, AuditResult)
            assert result.product_id == "missing-files"
            assert result.score == 0.0
            assert len(result.flagged_issues) > 0
    
    def test_title_length_validation(self):
        """Test title length validation edge cases"""
        # Test exactly at boundaries
        title_29_chars = 'a' * 29
        title_30_chars = 'a' * 30
        title_60_chars = 'a' * 60
        title_61_chars = 'a' * 61
        
        test_cases = [
            (title_29_chars, True),   # Should flag as too short
            (title_30_chars, False),  # Should be fine
            (title_60_chars, False),  # Should be fine
            (title_61_chars, True),   # Should flag as too long
        ]
        
        for title, should_have_issue in test_cases:
            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>{title}</title>
                <meta name="description" content="Valid description that meets the minimum length requirements for SEO">
            </head>
            <body>Content</body>
            </html>
            '''
            
            result = self.auditor._analyze_html(html, "test")
            title_issues = [issue for issue in result.flagged_issues if 'title' in issue.lower()]
            
            if should_have_issue:
                assert len(title_issues) > 0, f"Expected title issue for length {len(title)}"
            else:
                assert len(title_issues) == 0, f"Unexpected title issue for length {len(title)}"
    
    def test_meta_description_length_validation(self):
        """Test meta description length validation"""
        # Test boundary cases
        desc_119_chars = 'a' * 119
        desc_120_chars = 'a' * 120
        desc_160_chars = 'a' * 160
        desc_161_chars = 'a' * 161
        
        test_cases = [
            (desc_119_chars, True),   # Too short
            (desc_120_chars, False),  # Good
            (desc_160_chars, False),  # Good
            (desc_161_chars, True),   # Too long
        ]
        
        for desc, should_have_issue in test_cases:
            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Valid Title for Testing Meta Description</title>
                <meta name="description" content="{desc}">
            </head>
            <body>Content</body>
            </html>
            '''
            
            result = self.auditor._analyze_html(html, "test")
            desc_issues = [issue for issue in result.flagged_issues if 'description' in issue.lower()]
            
            if should_have_issue:
                assert len(desc_issues) > 0, f"Expected description issue for length {len(desc)}"
            else:
                assert len(desc_issues) == 0, f"Unexpected description issue for length {len(desc)}"
    
    def test_score_calculation(self):
        """Test audit score calculation logic"""
        # Perfect HTML should get high score
        perfect_result = self.auditor._analyze_html(self.valid_html, "perfect")
        assert perfect_result.score >= 90
        
        # HTML with many issues should get low score
        bad_result = self.auditor._analyze_html(self.missing_elements_html, "bad")
        assert bad_result.score <= 50
        
        # Score should be between 0 and 100
        assert 0 <= perfect_result.score <= 100
        assert 0 <= bad_result.score <= 100


if __name__ == "__main__":
    pytest.main([__file__])