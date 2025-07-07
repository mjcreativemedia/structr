#!/usr/bin/env python3
"""
Test script for Google Product Schema Validator
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, '/home/scrapybara/structr')

from validators.schema_validator import GoogleProductSchemaValidator, validate_all_bundles, validate_single_bundle

def test_single_bundle_validation():
    """Test validation of a single bundle"""
    print("🧪 Testing Single Bundle Validation")
    print("-" * 50)
    
    # Test the complete product
    print("\n✅ Testing complete product (test-product-1):")
    result = validate_single_bundle("test-product-1")
    
    if result:
        print(f"Bundle ID: {result['bundle_id']}")
        print(f"Schema Found: {result['schema_found']}")
        print(f"Google Eligible: {result['google_eligible']}")
        print(f"Compliance Score: {result.get('compliance_score', 0):.1f}%")
        
        if result.get('summary'):
            summary = result['summary']
            print(f"Required Fields: {summary.get('required_passed', 0)}/{summary.get('required_total', 0)}")
            print(f"Recommended Fields: {summary.get('recommended_passed', 0)}/{summary.get('recommended_total', 0)}")
            print(f"Offers Fields: {summary.get('offers_passed', 0)}/{summary.get('offers_total', 0)}")
            print(f"Total Issues: {summary.get('total_issues', 0)}")
    else:
        print("❌ Validation failed")
    
    # Test the incomplete product
    print("\n⚠️  Testing incomplete product (incomplete-product):")
    result = validate_single_bundle("incomplete-product")
    
    if result:
        print(f"Bundle ID: {result['bundle_id']}")
        print(f"Schema Found: {result['schema_found']}")
        print(f"Google Eligible: {result['google_eligible']}")
        print(f"Compliance Score: {result.get('compliance_score', 0):.1f}%")
        
        if result.get('summary'):
            summary = result['summary']
            print(f"Required Fields: {summary.get('required_passed', 0)}/{summary.get('required_total', 0)}")
            print(f"Critical Issues: {summary.get('critical_issues', 0)}")
    else:
        print("❌ Validation failed")

def test_all_bundles_validation():
    """Test validation of all bundles"""
    print("\n\n🧪 Testing All Bundles Validation")
    print("-" * 50)
    
    results = validate_all_bundles()
    
    print(f"Total bundles validated: {len(results)}")
    
    for result in results:
        bundle_id = result.get('bundle_id', 'Unknown')
        schema_found = result.get('schema_found', False)
        google_eligible = result.get('google_eligible', False)
        compliance_score = result.get('compliance_score', 0)
        
        status_icon = "✅" if google_eligible else "❌"
        print(f"{status_icon} {bundle_id}: {compliance_score:.1f}% compliance, Google Eligible: {google_eligible}")

def test_field_validation():
    """Test individual field validation"""
    print("\n\n🧪 Testing Field Validation Logic")
    print("-" * 50)
    
    validator = GoogleProductSchemaValidator()
    
    # Test required string validation
    print("\nTesting required string validation:")
    print("Valid string:", validator._validate_required_string("Valid Product Name"))
    print("Empty string:", validator._validate_required_string(""))
    print("None value:", validator._validate_required_string(None))
    print("Too short:", validator._validate_required_string("Hi"))
    
    # Test price validation
    print("\nTesting price validation:")
    print("Valid price:", validator._validate_required_price("29.99"))
    print("Zero price:", validator._validate_required_price("0"))
    print("Negative price:", validator._validate_required_price("-5.00"))
    print("Invalid price:", validator._validate_required_price("abc"))
    
    # Test currency validation
    print("\nTesting currency validation:")
    print("Valid USD:", validator._validate_required_currency("USD"))
    print("Valid EUR:", validator._validate_required_currency("EUR"))
    print("Invalid currency:", validator._validate_required_currency("XYZ"))
    print("Lowercase currency:", validator._validate_required_currency("usd"))
    
    # Test availability validation
    print("\nTesting availability validation:")
    print("Valid InStock:", validator._validate_required_availability("InStock"))
    print("Valid Schema.org URL:", validator._validate_required_availability("https://schema.org/InStock"))
    print("Invalid availability:", validator._validate_required_availability("Available"))

def test_schema_extraction():
    """Test schema extraction from different sources"""
    print("\n\n🧪 Testing Schema Extraction")
    print("-" * 50)
    
    validator = GoogleProductSchemaValidator()
    
    # Test extraction from test-product-1
    bundle_path = Path("/home/scrapybara/structr/output/bundles/test-product-1")
    
    print("Testing schema extraction from bundle:", bundle_path.name)
    
    schema_data = validator._extract_schema_from_bundle(bundle_path)
    
    if schema_data:
        print("✅ Schema extracted successfully")
        print(f"Schema type: {schema_data.get('@type', 'Unknown')}")
        print(f"Product name: {schema_data.get('name', 'Unknown')}")
        print(f"Has offers: {'offers' in schema_data}")
        
        offers_data = validator._extract_offers_data(schema_data)
        if offers_data:
            print(f"Offers price: {offers_data.get('price', 'Unknown')}")
            print(f"Offers currency: {offers_data.get('priceCurrency', 'Unknown')}")
        else:
            print("No offers data found")
    else:
        print("❌ No schema extracted")

def main():
    """Run all tests"""
    print("🔍 Google Product Schema Validator Tests")
    print("=" * 60)
    
    try:
        test_schema_extraction()
        test_field_validation()
        test_single_bundle_validation()
        test_all_bundles_validation()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())