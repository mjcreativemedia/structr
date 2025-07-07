#!/usr/bin/env python3
"""
Sprint 1 Demo Script

Demonstrates the complete Structr workflow:
1. Generate PDPs from sample data
2. Audit the results
3. Fix any issues
4. Export the catalog

This script showcases all Sprint 1 features in action.
"""

import os
import json
import time
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and display results"""
    print(f"\n🔧 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        print(f"Return code: {result.returncode}")
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def create_sample_product_files():
    """Create individual product JSON files from examples"""
    
    print("📁 Creating individual product files...")
    
    examples_dir = Path(__file__).parent / "examples"
    with open(examples_dir / "sample_products.json", 'r') as f:
        products = json.load(f)
    
    for product in products:
        filename = f"{product['handle']}.json"
        filepath = examples_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(product, f, indent=2)
        
        print(f"Created: {filename}")
    
    return [f"examples/{product['handle']}.json" for product in products]


def demo_sprint1():
    """Run complete Sprint 1 demonstration"""
    
    print("🚀 Structr Sprint 1 Demonstration")
    print("=" * 60)
    
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    # Step 1: Create individual product files
    product_files = create_sample_product_files()
    
    # Step 2: Generate PDPs for all sample products
    print("\n📦 Step 1: Generating PDPs...")
    for product_file in product_files:
        success = run_command(
            ["python", "cli.py", "enqueue", product_file],
            f"Generating PDP for {Path(product_file).stem}"
        )
        if not success:
            print(f"❌ Failed to generate PDP for {product_file}")
        time.sleep(1)  # Brief pause between generations
    
    # Step 3: Audit all products
    print("\n🔍 Step 2: Auditing all PDPs...")
    run_command(
        ["python", "cli.py", "audit", "--all"],
        "Running audit on all generated PDPs"
    )
    
    # Step 4: Show flagged products
    print("\n⚠️  Step 3: Checking for flagged products...")
    run_command(
        ["python", "cli.py", "audit", "--all", "--min-score", "80"],
        "Showing products with audit score < 80"
    )
    
    # Step 5: Fix flagged products (dry run first)
    print("\n🔧 Step 4: Preview fixes (dry run)...")
    run_command(
        ["python", "cli.py", "fix", "--all", "--min-score", "80", "--dry-run"],
        "Previewing what would be fixed"
    )
    
    # Step 6: Actually fix the products
    print("\n✨ Step 5: Applying fixes...")
    run_command(
        ["python", "cli.py", "fix", "--all", "--min-score", "80"],
        "Fixing all flagged products"
    )
    
    # Step 7: Re-audit to show improvements
    print("\n📊 Step 6: Re-auditing after fixes...")
    run_command(
        ["python", "cli.py", "audit", "--all"],
        "Checking audit scores after fixes"
    )
    
    # Step 8: Export catalog
    print("\n📄 Step 7: Exporting catalog...")
    run_command(
        ["python", "cli.py", "export", "--export-file", "demo_catalog.csv"],
        "Exporting complete catalog to CSV"
    )
    
    # Step 9: Show export statistics
    print("\n📈 Sprint 1 Demo Results:")
    print("-" * 40)
    
    # Check if output directory exists and show statistics
    output_dir = Path("output")
    if output_dir.exists():
        bundles_dir = output_dir / "bundles"
        if bundles_dir.exists():
            bundle_count = len([d for d in bundles_dir.iterdir() if d.is_dir()])
            print(f"✅ Generated bundles: {bundle_count}")
        
        catalog_file = output_dir / "demo_catalog.csv"
        if catalog_file.exists():
            print(f"✅ Catalog exported: {catalog_file}")
            print(f"   File size: {catalog_file.stat().st_size} bytes")
        
        print(f"✅ All files created in: {output_dir.absolute()}")
    
    print("\n🎉 Sprint 1 demonstration complete!")
    print("\nNext steps:")
    print("1. Examine generated bundles in output/bundles/")
    print("2. Review audit scores and fix logs")
    print("3. Import demo_catalog.csv to your platform")
    print("4. Run tests: python run_tests.py")


def demo_specific_features():
    """Demonstrate specific Sprint 1 features"""
    
    print("\n🎯 Feature-Specific Demonstrations:")
    print("=" * 50)
    
    # Test schema generation
    print("\n🏗️  Schema Generation Test:")
    run_command(
        ["python", "-c", """
from models.pdp import ProductData
from schemas.schema_generator import generate_product_schema
import json

product = ProductData(
    handle='demo-test',
    title='Demo Test Product',
    description='A test product for demonstrating schema generation',
    price=99.99,
    brand='Demo Brand'
)

schema = generate_product_schema(product)
print(json.dumps(schema, indent=2))
"""],
        "Testing schema generation directly"
    )
    
    # Test fix functionality on specific product
    if Path("output/bundles").exists():
        bundles = list(Path("output/bundles").iterdir())
        if bundles:
            test_product = bundles[0].name
            print(f"\n🔧 Fix Feature Test (targeting {test_product}):")
            run_command(
                ["python", "cli.py", "fix", test_product, "--issues", "title", "meta_description", "--dry-run"],
                f"Testing targeted fix on {test_product}"
            )
    
    # Test validation
    print("\n✅ Running unit tests:")
    run_command(
        ["python", "run_tests.py"],
        "Running complete test suite"
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Structr Sprint 1 Demonstration")
    parser.add_argument("--features-only", action="store_true", 
                       help="Run feature-specific demos only")
    parser.add_argument("--full", action="store_true", 
                       help="Run complete workflow demo")
    
    args = parser.parse_args()
    
    if args.features_only:
        demo_specific_features()
    elif args.full:
        demo_sprint1()
        demo_specific_features()
    else:
        demo_sprint1()