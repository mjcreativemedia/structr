"""
PyTest configuration for Structr tests
"""

import pytest
import sys
from pathlib import Path

# Add the project root to Python path so we can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_product_data():
    """Fixture providing sample ProductData for testing"""
    from models.pdp import ProductData
    
    return ProductData(
        handle="test-product-fixture",
        title="Test Product from Fixture",
        description="This is a test product created by pytest fixture",
        price=39.99,
        brand="Test Brand",
        category="Test Category",
        images=["https://example.com/test1.jpg", "https://example.com/test2.jpg"],
        features=["Feature 1", "Feature 2", "Feature 3"],
        metafields={
            "material": "Cotton",
            "color": "Blue",
            "size": "Medium",
            "gtin": "1234567890123"
        }
    )


@pytest.fixture
def sample_html_content():
    """Fixture providing sample HTML content for testing"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Test Product - High Quality Test Item</title>
        <meta name="description" content="High quality test product designed for comprehensive testing. Features include durability, reliability, and excellent performance.">
        <meta property="og:title" content="Test Product - High Quality Test Item">
        <meta property="og:description" content="High quality test product designed for comprehensive testing.">
        <meta property="og:image" content="https://example.com/test-product.jpg">
        <meta property="og:type" content="product">
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Test Product",
            "description": "High quality test product designed for comprehensive testing",
            "image": ["https://example.com/test-product.jpg"],
            "brand": {
                "@type": "Brand",
                "name": "Test Brand"
            },
            "offers": {
                "@type": "Offer",
                "price": "39.99",
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock",
                "url": "https://example.com/products/test-product"
            },
            "sku": "TEST-001"
        }
        </script>
    </head>
    <body>
        <main>
            <h1>Test Product</h1>
            <div class="product-image">
                <img src="https://example.com/test-product.jpg" alt="Test Product">
            </div>
            <div class="product-details">
                <p class="price">$39.99</p>
                <p class="description">High quality test product designed for comprehensive testing. Features include durability, reliability, and excellent performance.</p>
                <ul class="features">
                    <li>Feature 1</li>
                    <li>Feature 2</li>
                    <li>Feature 3</li>
                </ul>
            </div>
        </main>
    </body>
    </html>
    '''


@pytest.fixture
def temp_bundle_directory(tmp_path, sample_product_data, sample_html_content):
    """Fixture creating a temporary bundle directory for testing"""
    import json
    
    bundle_dir = tmp_path / "test-bundle"
    bundle_dir.mkdir()
    
    # Create index.html
    html_file = bundle_dir / "index.html"
    html_file.write_text(sample_html_content, encoding='utf-8')
    
    # Create sync.json
    sync_data = {
        "input": sample_product_data.model_dump(),
        "output": {
            "bundle_path": str(bundle_dir),
            "generation_time": 2.5,
            "model_used": "test-model",
            "timestamp": "2024-01-01T00:00:00"
        }
    }
    sync_file = bundle_dir / "sync.json"
    sync_file.write_text(json.dumps(sync_data, indent=2))
    
    # Create audit.json (will be overwritten by actual audit)
    audit_data = {
        "product_id": sample_product_data.handle,
        "score": 95.0,
        "missing_fields": [],
        "flagged_issues": [],
        "schema_errors": [],
        "metadata_issues": [],
        "timestamp": "2024-01-01T00:00:00"
    }
    audit_file = bundle_dir / "audit.json"
    audit_file.write_text(json.dumps(audit_data, indent=2))
    
    return bundle_dir