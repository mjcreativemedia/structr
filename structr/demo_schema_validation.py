#!/usr/bin/env python3
"""
Demo script showing the Google Product Schema Validation functionality in Structr
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, '/home/scrapybara/structr')

from validators.schema_validator import validate_all_bundles, validate_single_bundle, GoogleProductSchemaValidator

def demo_validation_overview():
    """Demo the validation overview functionality"""
    print("🔍 DEMO: Google Product Schema Validation")
    print("=" * 60)
    
    print("\n📊 VALIDATION OVERVIEW")
    print("-" * 30)
    
    # Get all validation results
    results = validate_all_bundles()
    
    if not results:
        print("❌ No bundles found to validate")
        return
    
    # Summary statistics
    total_bundles = len(results)
    schema_found = sum(1 for r in results if r.get('schema_found', False))
    google_eligible = sum(1 for r in results if r.get('google_eligible', False))
    
    scores = [r.get('compliance_score', 0) for r in results if r.get('compliance_score')]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    print(f"📋 Total Bundles: {total_bundles}")
    print(f"🔍 Schema Found: {schema_found}/{total_bundles} ({schema_found/total_bundles*100:.1f}%)")
    print(f"✅ Google Eligible: {google_eligible}/{total_bundles} ({google_eligible/total_bundles*100:.1f}%)")
    print(f"📊 Average Compliance: {avg_score:.1f}%")
    
    print(f"\n📈 INDIVIDUAL RESULTS")
    print("-" * 30)
    
    # Show individual results
    for result in results:
        bundle_id = result.get('bundle_id', 'Unknown')
        schema_found = result.get('schema_found', False)
        google_eligible = result.get('google_eligible', False)
        compliance_score = result.get('compliance_score', 0)
        
        if schema_found:
            status_icon = "✅" if google_eligible else "⚠️"
            print(f"{status_icon} {bundle_id:<25} | {compliance_score:>5.1f}% | Google: {'Yes' if google_eligible else 'No'}")
        else:
            print(f"❌ {bundle_id:<25} | No schema found")

def demo_detailed_validation():
    """Demo detailed validation for specific bundles"""
    print(f"\n\n🔬 DETAILED VALIDATION ANALYSIS")
    print("=" * 60)
    
    # Test bundles to analyze
    test_bundles = ["test-product-1", "incomplete-product"]
    
    for bundle_id in test_bundles:
        print(f"\n📦 ANALYZING: {bundle_id}")
        print("-" * 40)
        
        result = validate_single_bundle(bundle_id)
        
        if not result:
            print(f"❌ Bundle not found: {bundle_id}")
            continue
        
        if not result.get('schema_found', False):
            print(f"❌ No schema found in bundle: {bundle_id}")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            continue
        
        # Summary
        google_eligible = result.get('google_eligible', False)
        compliance_score = result.get('compliance_score', 0)
        schema_type = result.get('schema_type', 'Unknown')
        
        print(f"Schema Type: {schema_type}")
        print(f"Compliance Score: {compliance_score:.1f}%")
        print(f"Google Eligible: {'✅ Yes' if google_eligible else '❌ No'}")
        
        # Field analysis
        summary = result.get('summary', {})
        
        print(f"\n📊 Field Compliance:")
        print(f"   Required: {summary.get('required_passed', 0)}/{summary.get('required_total', 0)}")
        print(f"   Recommended: {summary.get('recommended_passed', 0)}/{summary.get('recommended_total', 0)}")
        print(f"   Offers: {summary.get('offers_passed', 0)}/{summary.get('offers_total', 0)}")
        print(f"   Total Issues: {summary.get('total_issues', 0)}")
        
        # Show specific field issues
        required_fields = result.get('required_fields', {})
        offers_fields = result.get('offers_fields', {})
        
        print(f"\n🔍 Field Details:")
        
        # Required fields
        for field_name, field_result in required_fields.items():
            present = field_result.get('present', False)
            valid = field_result.get('valid', False)
            issues = field_result.get('issues', [])
            
            if present and valid:
                status = "✅"
            elif present and not valid:
                status = "⚠️"
            else:
                status = "❌"
            
            print(f"   {status} {field_name}")
            if issues:
                for issue in issues[:2]:  # Show first 2 issues
                    print(f"      • {issue}")
        
        # Offers fields
        for field_name, field_result in offers_fields.items():
            present = field_result.get('present', False)
            valid = field_result.get('valid', False)
            issues = field_result.get('issues', [])
            
            if present and valid:
                status = "✅"
            elif present and not valid:
                status = "⚠️"
            else:
                status = "❌"
            
            print(f"   {status} offers.{field_name}")
            if issues:
                for issue in issues[:2]:
                    print(f"      • {issue}")

def demo_validation_rules():
    """Demo the validation rules and requirements"""
    print(f"\n\n📚 VALIDATION RULES & REQUIREMENTS")
    print("=" * 60)
    
    validator = GoogleProductSchemaValidator()
    
    print(f"\n🔴 REQUIRED FIELDS (60% weight)")
    print("-" * 40)
    for field_name, config in validator.REQUIRED_FIELDS.items():
        print(f"✓ {field_name:<15} - {config['description']}")
        print(f"   Path: {' > '.join(config['path'])}")
        print(f"   Rule: {config['google_docs']}")
        print()
    
    print(f"\n💰 OFFERS REQUIRED FIELDS (25% weight)")
    print("-" * 40)
    for field_name, config in validator.OFFERS_REQUIRED_FIELDS.items():
        print(f"✓ {field_name:<15} - {config['description']}")
        print(f"   Path: offers > {' > '.join(config['path'])}")
        print(f"   Rule: {config['google_docs']}")
        print()
    
    print(f"\n🟡 RECOMMENDED FIELDS (15% weight)")
    print("-" * 40)
    for field_name, config in validator.RECOMMENDED_FIELDS.items():
        print(f"○ {field_name:<15} - {config['description']}")
        print(f"   Path: {' > '.join(config['path'])}")
        print(f"   Rule: {config['google_docs']}")
        print()

def demo_validation_examples():
    """Demo validation with real examples"""
    print(f"\n\n🧪 VALIDATION EXAMPLES")
    print("=" * 60)
    
    validator = GoogleProductSchemaValidator()
    
    print(f"\n✅ VALID EXAMPLES")
    print("-" * 30)
    
    # Test valid values
    valid_tests = [
        ("Product Name", validator._validate_required_string("Premium Wireless Headphones")),
        ("Price", validator._validate_required_price("299.99")),
        ("Currency", validator._validate_required_currency("USD")),
        ("Availability", validator._validate_required_availability("InStock")),
    ]
    
    for test_name, result in valid_tests:
        status = "✅" if result['valid'] else "❌"
        print(f"{status} {test_name}: {result}")
    
    print(f"\n❌ INVALID EXAMPLES")
    print("-" * 30)
    
    # Test invalid values
    invalid_tests = [
        ("Empty Name", validator._validate_required_string("")),
        ("Zero Price", validator._validate_required_price("0")),
        ("Invalid Currency", validator._validate_required_currency("XYZ")),
        ("Invalid Availability", validator._validate_required_availability("Available")),
    ]
    
    for test_name, result in invalid_tests:
        status = "✅" if result['valid'] else "❌"
        print(f"{status} {test_name}: {result}")

def demo_usage_instructions():
    """Show how to use the validation tool"""
    print(f"\n\n🎯 HOW TO USE SCHEMA VALIDATION")
    print("=" * 60)
    
    print(f"""
📋 STEP-BY-STEP USAGE:

1. 🚀 START DASHBOARD
   cd /home/scrapybara/structr
   python start_dashboard.py

2. 🔍 NAVIGATE TO VALIDATION
   → Go to "Audit Manager" tab
   → Select "Schema Validation" sub-tab

3. 📊 CHOOSE VALIDATION MODE

   🌐 ALL BUNDLES OVERVIEW:
   • See summary metrics across all products
   • View compliance score distribution charts
   • Identify products needing attention
   • Export validation reports

   🔬 SINGLE BUNDLE ANALYSIS:
   • Select specific product for detailed analysis
   • See field-by-field validation results
   • Get specific recommendations for improvements
   • Use quick action buttons (auto-fix, re-validate)

   📚 VALIDATION RULES:
   • Reference Google Product Schema requirements
   • Understand field validation rules
   • Learn best practices for schema compliance

4. 🔧 IMPROVE COMPLIANCE
   • Fix missing required fields (name, image, sku, etc.)
   • Complete offers information (price, currency, availability)
   • Add recommended fields (brand, gtin, reviews)
   • Re-validate to confirm improvements

5. ✅ ACHIEVE GOOGLE ELIGIBILITY
   • All required fields present and valid
   • Complete offers object with price info
   • High compliance score (80%+)
   • Ready for Google Rich Results!

📖 DOCUMENTATION REFERENCES:
• Google Product Schema: https://developers.google.com/search/docs/appearance/structured-data/product
• Schema.org Product: https://schema.org/Product
• Rich Results Test: https://search.google.com/test/rich-results
""")

def main():
    """Run the complete demo"""
    try:
        demo_validation_overview()
        demo_detailed_validation() 
        demo_validation_rules()
        demo_validation_examples()
        demo_usage_instructions()
        
        print(f"\n" + "=" * 60)
        print(f"🎉 DEMO COMPLETE!")
        print(f"✅ Google Product Schema Validation is ready to use!")
        print(f"📊 Start the dashboard to see the full interactive interface")
        print(f"=" * 60)
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())