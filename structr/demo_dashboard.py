#!/usr/bin/env python3
"""
Dashboard Demo Script

Generate sample data and test dashboard functionality
"""

import json
import time
import subprocess
from pathlib import Path


def create_sample_data():
    """Create sample product data for dashboard testing"""
    
    print("📦 Creating sample data for dashboard demo...")
    
    # Create sample products with varying quality
    sample_products = [
        {
            "handle": "premium-organic-shirt",
            "title": "Premium Organic Cotton T-Shirt",
            "description": "Luxuriously soft organic cotton t-shirt made from 100% GOTS certified organic cotton. Perfect for everyday wear with a classic fit that flatters every body type. Machine washable and built to last.",
            "price": 89.99,
            "brand": "EcoWear Premium",
            "category": "Clothing > Shirts > T-Shirts",
            "images": [
                "https://example.com/images/organic-shirt-front.jpg",
                "https://example.com/images/organic-shirt-back.jpg"
            ],
            "features": [
                "100% GOTS certified organic cotton",
                "Machine washable cold water",
                "Classic fit design",
                "Pre-shrunk fabric",
                "Available in 8 colors"
            ],
            "metafields": {
                "material": "100% Organic Cotton",
                "care_instructions": "Machine wash cold, tumble dry low",
                "sustainability_info": "GOTS certified, carbon neutral shipping",
                "gtin": "1234567890123",
                "mpn": "ECO-SHIRT-001",
                "weight": "0.5",
                "weight_unit": "LB",
                "color": "Navy Blue",
                "size": "Large",
                "rating": 4.8,
                "review_count": 156
            }
        },
        {
            "handle": "wireless-noise-cancelling-headphones",
            "title": "ProSound Wireless Bluetooth Headphones with Active Noise Cancellation",
            "description": "Experience crystal-clear audio with industry-leading noise cancellation technology. 30-hour battery life, premium comfort design, and instant pairing make these headphones perfect for work, travel, and entertainment.",
            "price": 249.99,
            "brand": "ProSound Audio",
            "category": "Electronics > Audio > Headphones",
            "images": [
                "https://example.com/images/headphones-main.jpg",
                "https://example.com/images/headphones-wearing.jpg",
                "https://example.com/images/headphones-case.jpg"
            ],
            "features": [
                "Active noise cancellation technology",
                "30-hour battery life with ANC on",
                "Bluetooth 5.2 connectivity",
                "Quick charge: 15 min = 3 hours playback",
                "Premium memory foam ear cushions",
                "Built-in microphone for calls"
            ],
            "metafields": {
                "battery_life": "30 hours with ANC",
                "connectivity": "Bluetooth 5.2, 3.5mm wired",
                "weight": "0.8",
                "weight_unit": "LB",
                "color": "Midnight Black",
                "warranty": "2 years international",
                "gtin": "2345678901234",
                "mpn": "PS-ANC-250",
                "rating": 4.6,
                "review_count": 89
            }
        },
        {
            "handle": "artisan-coffee-colombia",
            "title": "Colombian Single Origin Coffee Beans - Medium Roast",
            "description": "Hand-picked premium coffee beans from the highlands of Colombia. Medium roast with notes of chocolate, caramel, and citrus. Freshly roasted to order for maximum flavor and aroma.",
            "price": 24.99,
            "brand": "Mountain Peak Coffee Co",
            "category": "Food & Beverage > Coffee > Whole Bean",
            "images": [
                "https://example.com/images/coffee-bag.jpg",
                "https://example.com/images/coffee-beans-close.jpg"
            ],
            "features": [
                "Single origin Colombian beans",
                "Medium roast profile",
                "Freshly roasted to order",
                "Fair trade and organic certified",
                "Resealable valve bag for freshness"
            ],
            "metafields": {
                "origin": "Huila, Colombia",
                "roast_level": "Medium",
                "processing_method": "Washed",
                "altitude": "1600-1800m",
                "flavor_notes": "Chocolate, caramel, bright citrus",
                "certifications": "Fair Trade, USDA Organic",
                "weight": "1",
                "weight_unit": "LB",
                "gtin": "3456789012345",
                "mpn": "MPC-COL-001",
                "rating": 4.9,
                "review_count": 203
            }
        },
        {
            "handle": "basic-product",
            "title": "Basic Product",
            "description": "A basic product for testing.",
            "price": 19.99,
            "metafields": {
                "rating": 3.2,
                "review_count": 5
            }
        },
        {
            "handle": "incomplete-product", 
            "title": "Incomplete Product Title That Is Way Too Long And Will Definitely Fail The SEO Title Length Check",
            "description": "Short",
            "price": 9.99,
            "brand": "Poor Brand",
            "metafields": {
                "rating": 2.1,
                "review_count": 2
            }
        }
    ]
    
    # Save individual product files
    examples_dir = Path("examples")
    examples_dir.mkdir(exist_ok=True)
    
    for product in sample_products:
        filename = f"{product['handle']}.json"
        filepath = examples_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(product, f, indent=2)
        
        print(f"✅ Created: {filename}")
    
    return sample_products


def generate_sample_bundles():
    """Generate PDP bundles from sample data"""
    
    print("\n🏗️  Generating PDP bundles...")
    
    examples_dir = Path("examples")
    product_files = list(examples_dir.glob("*.json"))
    
    for i, product_file in enumerate(product_files, 1):
        print(f"Generating {i}/{len(product_files)}: {product_file.stem}")
        
        try:
            result = subprocess.run([
                'python', 'cli.py', 'enqueue', str(product_file)
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode == 0:
                print(f"  ✅ Success")
            else:
                print(f"  ❌ Failed: {result.stderr}")
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
        
        # Small delay between generations
        time.sleep(0.5)


def run_sample_audits():
    """Run audits on generated bundles"""
    
    print("\n🔍 Running audit analysis...")
    
    try:
        result = subprocess.run([
            'python', 'cli.py', 'audit', '--all'
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print("✅ Audit completed")
            if result.stdout:
                print("Audit results:")
                print(result.stdout)
        else:
            print(f"❌ Audit failed: {result.stderr}")
    
    except Exception as e:
        print(f"❌ Audit error: {str(e)}")


def fix_sample_issues():
    """Fix issues in sample bundles"""
    
    print("\n🔧 Fixing sample issues...")
    
    try:
        result = subprocess.run([
            'python', 'cli.py', 'fix', '--all', '--min-score', '85'
        ], capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print("✅ Fixes applied")
            if result.stdout:
                print("Fix results:")
                print(result.stdout)
        else:
            print(f"❌ Fix failed: {result.stderr}")
    
    except Exception as e:
        print(f"❌ Fix error: {str(e)}")


def check_dashboard_readiness():
    """Check if dashboard dependencies are ready"""
    
    print("\n🔍 Checking dashboard readiness...")
    
    # Check for required modules
    try:
        import streamlit
        print("✅ Streamlit available")
    except ImportError:
        print("❌ Streamlit not found - run: pip install streamlit")
        return False
    
    try:
        import plotly
        print("✅ Plotly available")
    except ImportError:
        print("❌ Plotly not found - run: pip install plotly")
        return False
    
    try:
        import pandas
        print("✅ Pandas available")
    except ImportError:
        print("❌ Pandas not found - run: pip install pandas")
        return False
    
    # Check for bundles
    output_dir = Path("output/bundles")
    if output_dir.exists():
        bundle_count = len([d for d in output_dir.iterdir() if d.is_dir()])
        print(f"✅ Found {bundle_count} bundles for dashboard")
    else:
        print("⚠️  No bundles found - dashboard will have limited functionality")
    
    return True


def main():
    """Run complete dashboard demo setup"""
    
    print("🎨 Structr Dashboard Demo Setup")
    print("=" * 50)
    
    # Step 1: Create sample data
    create_sample_data()
    
    # Step 2: Generate bundles
    generate_sample_bundles()
    
    # Step 3: Run audits
    run_sample_audits()
    
    # Step 4: Apply some fixes
    fix_sample_issues()
    
    # Step 5: Check dashboard readiness
    ready = check_dashboard_readiness()
    
    print("\n" + "=" * 50)
    
    if ready:
        print("🎉 Dashboard demo setup complete!")
        print("\n🚀 Launch the dashboard:")
        print("   python start_dashboard.py")
        print("\n📊 Or run directly:")
        print("   streamlit run dashboard_app.py")
        print("\n🌐 Dashboard URL: http://localhost:8501")
        
        print("\n🎯 Try these dashboard features:")
        print("   • Overview: View metrics and charts")
        print("   • Batch Processor: Upload more products")
        print("   • Audit Manager: Analyze compliance")
        print("   • Bundle Explorer: Inspect individual PDPs")
        print("   • Export Center: Download catalogs")
    else:
        print("❌ Dashboard setup incomplete")
        print("   Install missing dependencies and try again")


if __name__ == "__main__":
    main()