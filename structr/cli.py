#!/usr/bin/env python3
"""
Structr CLI - Enhanced command-line interface for PDP optimization

Usage:
    # Original commands
    python cli.py enqueue <product_data>         # Enqueue generation job
    python cli.py audit <product_id>             # Audit specific product
    python cli.py fix <product_id>               # Fix specific product
    python cli.py export                         # Export normalized catalog CSV
    
    # New Sprint 3 commands
    python cli.py connect shopify <csv_file>     # Import from Shopify CSV
    python cli.py connect pim <api_url>          # Connect to PIM system
    python cli.py connect analyze <csv_file>     # Analyze CSV structure
    python cli.py batch generate <products.json> # Batch generate PDPs
    python cli.py batch audit --all              # Batch audit all products
    python cli.py batch fix --threshold 70       # Batch fix low-scoring products
    python cli.py batch status <batch_id>        # Check batch status
    python cli.py api start                      # Start FastAPI server
"""

import os
import json
import csv
import click
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import centralized configuration
from config import StructrConfig as CONFIG

from models.pdp import ProductData, AuditResult
from models.audit import PDPAuditor
from fix_broken_pdp import PDPFixer
from llm_service.generator import OllamaLLMService

# Sprint 3 imports
from connectors import ShopifyCSVImporter, PIMConnector, GenericCSVMapper
from connectors.base import ConnectorConfig, ImportResult
from batch.processors.batch_manager import BatchManager
from batch.queues.job_queue import get_job_queue, JobStatus


# Initialize Sprint 3 components
batch_manager = BatchManager()
job_queue = get_job_queue()


@click.group()
def cli():
    """Structr - PDP Optimization Engine CLI"""
    pass


@cli.command()
@click.argument('product_data_file', type=click.Path(exists=True))
@click.option('--output-dir', default=CONFIG.DEFAULT_OUTPUT_DIR, help='Output directory')
@click.option('--model', default=CONFIG.DEFAULT_LLM_MODEL, help='LLM model to use')
def enqueue(product_data_file: str, output_dir: str, model: str):
    """Enqueue PDP generation job from JSON file"""
    
    with open(product_data_file, 'r') as f:
        product_data_dict = json.load(f)
    
    # Handle both single product and list of products
    if isinstance(product_data_dict, list):
        products = [ProductData(**p) for p in product_data_dict]
        
        # Use batch processing for multiple products
        click.echo(f"📦 Processing {len(products)} products with batch manager...")
        batch_id = batch_manager.generate_batch(products)
        
        click.echo(f"✅ Batch job submitted: {batch_id}")
        click.echo(f"🔍 Check status: python cli.py batch status {batch_id}")
        return
    
    # Single product processing (original logic)
    product_data = ProductData(**product_data_dict)
    
    # Initialize services
    llm_service = OllamaLLMService(model=model)
    
    # Generate PDP
    click.echo(f"Generating PDP for {product_data.id}...")
    start_time = time.time()
    
    bundle = llm_service.generate_pdp(product_data)
    
    # Create output directory
    output_path = CONFIG.get_bundle_path(product_data.id)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save bundle files
    with open(CONFIG.get_html_file_path(product_data.id), 'w', encoding='utf-8') as f:
        f.write(bundle.html_content)
    
    sync_data = {
        "input": product_data_dict,
        "output": {
            "bundle_path": str(output_path),
            "generation_time": bundle.generation_time,
            "model_used": bundle.model_used,
            "timestamp": bundle.timestamp.isoformat()
        }
    }
    
    with open(CONFIG.get_sync_file_path(product_data.id), 'w') as f:
        json.dump(sync_data, f, indent=2, default=str)
    
    # Run audit
    auditor = PDPAuditor()
    audit_result = auditor.audit_pdp_bundle(str(output_path), product_data.id)
    
    with open(CONFIG.get_audit_file_path(product_data.id), 'w') as f:
        json.dump(audit_result.model_dump(), f, indent=2, default=str)
    
    total_time = time.time() - start_time
    
    click.echo(f"✅ Generated PDP bundle for {product_data.id}")
    click.echo(f"📁 Path: {output_path}")
    click.echo(f"⏱️  Time: {total_time:.2f}s")
    click.echo(f"📊 Audit Score: {audit_result.score}/100")
    
    if audit_result.flagged_issues:
        click.echo(f"⚠️  Issues: {len(audit_result.flagged_issues)} flagged")


@cli.command()
@click.argument('product_id', required=False)
@click.option('--all', is_flag=True, help='Audit all products')
@click.option('--output-dir', default=CONFIG.DEFAULT_OUTPUT_DIR, help='Output directory')
@click.option('--min-score', type=float, help='Only show products below this score')
@click.option('--export', type=click.Path(), help='Export results to CSV file')
def audit(product_id: str, all: bool, output_dir: str, min_score: float, export: str):
    """Audit product(s) for SEO compliance"""
    
    if not product_id and not all:
        raise click.UsageError("Must specify product_id or --all")
    
    auditor = PDPAuditor()
    results = []
    
    if product_id:
        # Audit specific product
        bundle_path = CONFIG.get_bundle_path(product_id)
        
        if not bundle_path.exists():
            click.echo(f"❌ Bundle not found: {bundle_path}", err=True)
            return
        
        audit_result = auditor.audit_pdp_bundle(str(bundle_path), product_id)
        results.append(audit_result)
        
    elif all:
        # Use batch processing for auditing all products
        bundles_dir = Path(output_dir) / "bundles"
        
        if not bundles_dir.exists():
            click.echo(f"❌ Bundles directory not found: {bundles_dir}", err=True)
            return
        
        product_ids = [d.name for d in bundles_dir.iterdir() if d.is_dir()]
        
        if product_ids:
            click.echo(f"📦 Starting batch audit for {len(product_ids)} products...")
            batch_id = batch_manager.audit_batch(product_ids)
            
            click.echo(f"✅ Batch audit submitted: {batch_id}")
            click.echo(f"🔍 Check status: python cli.py batch status {batch_id}")
            return
        else:
            click.echo("❌ No product bundles found")
            return
    
    # Filter by min_score if specified
    if min_score is not None:
        results = [r for r in results if r.score < min_score]
    
    # Display results
    click.echo(f"\n📊 Audit Results ({len(results)} products):")
    click.echo("-" * 80)
    
    for result in sorted(results, key=lambda x: x.score):
        status = "🔴" if result.score < 60 else "🟡" if result.score < 80 else "🟢"
        click.echo(f"{status} {result.product_id:<20} Score: {result.score:>6.1f}/100")
        
        if result.missing_fields:
            click.echo(f"   Missing: {', '.join(result.missing_fields)}")
        
        if result.flagged_issues:
            click.echo(f"   Issues:  {', '.join(result.flagged_issues[:3])}{'...' if len(result.flagged_issues) > 3 else ''}")
    
    # Export if requested
    if export:
        _export_audit_results(results, export)
        click.echo(f"\n📄 Results exported to: {export}")


@cli.command()
@click.argument('product_id', required=False)
@click.option('--all', is_flag=True, help='Fix all flagged products')
@click.option('--only', help='Fix specific product (alias for product_id)')
@click.option('--issues', multiple=True, help='Target specific issues')
@click.option('--min-score', type=float, default=CONFIG.DEFAULT_MIN_SCORE, help='Minimum score for --all')
@click.option('--dry-run', is_flag=True, help='Show what would be fixed')
@click.option('--output-dir', default=CONFIG.DEFAULT_OUTPUT_DIR, help='Output directory')
@click.option('--model', default=CONFIG.DEFAULT_LLM_MODEL, help='LLM model to use')
def fix(product_id: str, all: bool, only: str, issues: tuple, min_score: float, 
        dry_run: bool, output_dir: str, model: str):
    """Fix broken PDPs based on audit results"""
    
    target_product = product_id or only
    
    if not target_product and not all:
        raise click.UsageError("Must specify product_id, --only, or --all")
    
    # Initialize fixer
    llm_service = OllamaLLMService(model=model)
    fixer = PDPFixer(output_dir=output_dir, llm_service=llm_service)
    
    if dry_run:
        click.echo("🔍 DRY RUN - No changes will be made\n")
    
    if target_product:
        # Fix specific product
        click.echo(f"🔧 Fixing product: {target_product}")
        
        result = fixer.fix_product(
            product_id=target_product,
            target_issues=list(issues) if issues else None,
            dry_run=dry_run
        )
        
        if result['success']:
            if dry_run:
                click.echo(f"✅ Would fix {len(result['issues_to_fix'])} issue categories")
                click.echo(f"⏱️  Estimated time: {result['fix_time']:.2f}s")
            else:
                improvement = result.get('improvement', 0)
                click.echo(f"✅ Fixed {target_product}")
                click.echo(f"📊 Score: {result['original_score']:.1f} → {result['new_score']:.1f} (+{improvement:.1f})")
                click.echo(f"⏱️  Time: {result['fix_time']:.2f}s")
        else:
            click.echo(f"❌ Failed to fix {target_product}: {result['error']}")
    
    elif all:
        # Use batch processing for fixing all flagged products
        bundles_dir = Path(output_dir) / "bundles"
        
        if not bundles_dir.exists():
            click.echo(f"❌ Bundles directory not found: {bundles_dir}", err=True)
            return
        
        # Find products that need fixing
        product_ids = []
        for product_dir in bundles_dir.iterdir():
            if product_dir.is_dir():
                audit_file = product_dir / "audit.json"
                if audit_file.exists():
                    try:
                        with open(audit_file, 'r') as f:
                            audit_data = json.load(f)
                        if audit_data.get('score', 100) < min_score:
                            product_ids.append(product_dir.name)
                    except Exception:
                        continue
        
        if product_ids:
            if dry_run:
                click.echo(f"🔍 DRY RUN - Would fix {len(product_ids)} products with score < {min_score}")
                for pid in product_ids[:10]:  # Show first 10
                    click.echo(f"  - {pid}")
                if len(product_ids) > 10:
                    click.echo(f"  ... and {len(product_ids) - 10} more")
            else:
                click.echo(f"📦 Starting batch fix for {len(product_ids)} products...")
                batch_id = batch_manager.fix_batch(product_ids)
                
                click.echo(f"✅ Batch fix submitted: {batch_id}")
                click.echo(f"🔍 Check status: python cli.py batch status {batch_id}")
        else:
            click.echo(f"✅ No products need fixing (all have score >= {min_score})")


@cli.command()
@click.option('--output-dir', default=CONFIG.DEFAULT_OUTPUT_DIR, help='Output directory')
@click.option('--export-file', default=None, help='Export file path')
def export(output_dir: str, export_file: str):
    """Export normalized catalog CSV from PDP bundles"""
    
    bundles_dir = CONFIG.get_bundles_dir()
    
    if not bundles_dir.exists():
        click.echo(f"❌ Bundles directory not found: {bundles_dir}", err=True)
        return
    
    # Use default export file if not specified
    if not export_file:
        export_file = CONFIG.get_file_path("output", CONFIG.get_timestamp_filename(CONFIG.CATALOG_EXPORT_PATTERN))
    
    export_path = Path(export_file)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    
    catalog_data = []
    
    for product_dir in bundles_dir.iterdir():
        if product_dir.is_dir():
            try:
                # Load sync data
                sync_file = product_dir / "sync.json"
                if sync_file.exists():
                    with open(sync_file, 'r') as f:
                        sync_data = json.load(f)
                    
                    # Load HTML content
                    html_file = product_dir / "index.html"
                    html_content = ""
                    if html_file.exists():
                        with open(html_file, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                    
                    # Load audit data
                    audit_file = product_dir / "audit.json"
                    audit_score = 0
                    if audit_file.exists():
                        with open(audit_file, 'r') as f:
                            audit_data = json.load(f)
                            audit_score = audit_data.get('score', 0)
                    
                    # Build catalog row
                    input_data = sync_data.get('input', {})
                    
                    catalog_row = {
                        'handle': input_data.get('id', product_dir.name),
                        'title': input_data.get('title', ''),
                        'body_html': html_content,
                        'price': input_data.get('price', ''),
                        'vendor': input_data.get('vendor', ''),
                        'product_type': input_data.get('product_type', ''),
                        'audit_score': audit_score,
                        'bundle_path': str(product_dir),
                        'last_updated': sync_data.get('output', {}).get('timestamp', ''),
                        'metafields_features': json.dumps(input_data.get('features', [])),
                        'metafields_custom': json.dumps(input_data.get('metafields', {}))
                    }
                    
                    catalog_data.append(catalog_row)
                    
            except Exception as e:
                click.echo(f"⚠️  Failed to process {product_dir.name}: {e}")
    
    # Write CSV
    if catalog_data:
        fieldnames = catalog_data[0].keys()
        
        with open(export_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(catalog_data)
        
        click.echo(f"✅ Exported {len(catalog_data)} products to {export_path}")
        click.echo(f"📊 Average score: {sum(row['audit_score'] for row in catalog_data) / len(catalog_data):.1f}")
    else:
        click.echo("❌ No products found to export")


# Sprint 3 Commands

@cli.group()
def connect():
    """Connect to external data sources"""
    pass


@connect.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--generate', is_flag=True, help='Generate PDPs after import')
@click.option('--batch-size', default=500, help='Import batch size')
@click.option('--output-dir', default='output', help='Output directory')
def shopify(csv_file: str, generate: bool, batch_size: int, output_dir: str):
    """Import products from Shopify CSV export"""
    
    click.echo(f"📊 Analyzing Shopify CSV: {csv_file}")
    
    # Create Shopify connector
    config = ConnectorConfig(
        name="shopify_cli_import",
        source_type="csv",
        batch_size=batch_size
    )
    
    connector = ShopifyCSVImporter(config)
    
    # Analyze CSV structure
    csv_path = Path(csv_file)
    analysis = connector.detect_csv_structure(csv_path)
    
    click.echo(f"📄 File: {analysis['file_path']}")
    click.echo(f"📈 Rows: {analysis['row_count']:,}")
    click.echo(f"📋 Columns: {len(analysis['columns'])}")
    
    # Show data quality
    data_quality = analysis.get('data_quality', {})
    if data_quality:
        click.echo(f"🏆 Quality Score: {data_quality.get('overall_score', 0):.1f}%")
    
    # Import data
    click.echo(f"\n🚀 Starting import...")
    
    if generate:
        # Use batch manager for import + generation
        batch_id = batch_manager.import_and_generate(
            connector=connector,
            source=csv_file
        )
        
        click.echo(f"✅ Import and generation job submitted: {batch_id}")
        click.echo(f"🔍 Check status: python cli.py batch status {batch_id}")
    else:
        # Direct import only
        import_result = connector.import_data(csv_file)
        
        if import_result.success:
            click.echo(f"✅ Imported {import_result.processed_records} products")
            click.echo(f"⚠️  Failed: {import_result.failed_records}")
            click.echo(f"⏱️  Time: {import_result.processing_time:.2f}s")
            
            if import_result.errors:
                click.echo("❌ Errors:")
                for error in import_result.errors[:5]:
                    click.echo(f"  - {error}")
        else:
            click.echo(f"❌ Import failed: {'; '.join(import_result.errors)}")


@connect.command()
@click.argument('api_url')
@click.option('--api-key', help='API key for authentication')
@click.option('--endpoint', default='/products', help='Products endpoint')
@click.option('--test-only', is_flag=True, help='Only test connection')
@click.option('--generate', is_flag=True, help='Generate PDPs after import')
def pim(api_url: str, api_key: str, endpoint: str, test_only: bool, generate: bool):
    """Connect to PIM system or API"""
    
    click.echo(f"🔌 Connecting to PIM: {api_url}")
    
    # Create PIM connector
    credentials = {"base_url": api_url}
    if api_key:
        credentials["api_key"] = api_key
    
    config = ConnectorConfig(
        name="pim_cli_import",
        source_type="api",
        credentials=credentials
    )
    
    connector = PIMConnector(config)
    
    # Test connection
    is_connected = connector.test_connection()
    
    if is_connected:
        click.echo("✅ Connection successful")
        
        # Get available fields
        try:
            fields = connector.get_available_fields()
            if fields:
                click.echo(f"📋 Available fields: {', '.join(fields[:10])}")
                if len(fields) > 10:
                    click.echo(f"   ... and {len(fields) - 10} more")
        except Exception:
            pass
        
        if test_only:
            return
        
        # Import data
        click.echo(f"\n🚀 Starting import from {endpoint}...")
        
        if generate:
            # Use batch manager
            batch_id = batch_manager.import_and_generate(
                connector=connector,
                source=endpoint
            )
            
            click.echo(f"✅ Import and generation job submitted: {batch_id}")
            click.echo(f"🔍 Check status: python cli.py batch status {batch_id}")
        else:
            # Direct import
            import_result = connector.import_data(endpoint)
            
            if import_result.success:
                click.echo(f"✅ Imported {import_result.processed_records} products")
                click.echo(f"⚠️  Failed: {import_result.failed_records}")
                click.echo(f"⏱️  Time: {import_result.processing_time:.2f}s")
            else:
                click.echo(f"❌ Import failed: {'; '.join(import_result.errors)}")
    else:
        click.echo("❌ Connection failed - check URL and credentials")


@connect.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--sample-size', default=1000, help='Number of rows to analyze')
@click.option('--export-mapping', type=click.Path(), help='Export suggested mapping to JSON file')
def analyze(csv_file: str, sample_size: int, export_mapping: str):
    """Analyze CSV structure and suggest field mappings"""
    
    click.echo(f"🔍 Analyzing CSV structure: {csv_file}")
    
    # Create generic CSV mapper
    connector = GenericCSVMapper()
    
    # Analyze CSV
    csv_path = Path(csv_file)
    analysis = connector.analyze_csv_structure(csv_path, sample_size)
    
    # Display file info
    file_info = analysis['file_info']
    click.echo(f"\n📄 File Information:")
    click.echo(f"  Size: {file_info['size_mb']} MB")
    click.echo(f"  Encoding: {file_info['encoding']}")
    click.echo(f"  Delimiter: '{file_info['delimiter']}'")
    click.echo(f"  Rows: {analysis['row_count']:,}")
    
    # Display columns
    click.echo(f"\n📋 Columns ({len(analysis['columns'])}):")
    for col_name, col_info in analysis['columns'].items():
        completeness = col_info['completeness']['percentage']
        data_type = col_info['inferred_type']
        
        status = "✅" if completeness > 90 else "⚠️" if completeness > 50 else "❌"
        click.echo(f"  {status} {col_name:<30} {data_type:<10} {completeness:>5.1f}% complete")
    
    # Display suggested mappings
    mappings = analysis['suggested_mappings']
    confidence = analysis['mapping_confidence']
    
    if mappings:
        click.echo(f"\n🎯 Suggested Field Mappings:")
        for source_field, target_field in mappings.items():
            conf = confidence.get(source_field, 0) * 100
            conf_icon = "🟢" if conf > 80 else "🟡" if conf > 50 else "🔴"
            click.echo(f"  {conf_icon} {source_field:<30} → {target_field:<20} ({conf:.0f}%)")
    
    # Display data quality
    quality = analysis['data_quality']
    click.echo(f"\n🏆 Data Quality Score: {quality['overall_score']:.1f}%")
    
    if quality['issues']:
        click.echo("⚠️  Issues:")
        for issue in quality['issues']:
            click.echo(f"  - {issue}")
    
    # Display recommendations
    if analysis['recommendations']:
        click.echo("\n💡 Recommendations:")
        for rec in analysis['recommendations']:
            click.echo(f"  • {rec}")
    
    # Export mapping if requested
    if export_mapping:
        mapping_data = {
            'file_analyzed': csv_file,
            'suggested_mappings': mappings,
            'mapping_confidence': confidence,
            'analysis_timestamp': time.time(),
            'instructions': 'Use this mapping with: python cli.py connect generic --mapping mapping.json'
        }
        
        with open(export_mapping, 'w') as f:
            json.dump(mapping_data, f, indent=2)
        
        click.echo(f"\n📄 Mapping exported to: {export_mapping}")


@cli.group()
def batch():
    """Batch processing operations"""
    pass


@batch.command()
@click.argument('products_file', type=click.Path(exists=True))
@click.option('--priority', default=0, help='Job priority (higher = more priority)')
@click.option('--wait', is_flag=True, help='Wait for completion')
def generate(products_file: str, priority: int, wait: bool):
    """Generate PDPs for batch of products"""
    
    click.echo(f"📦 Loading products from: {products_file}")
    
    with open(products_file, 'r') as f:
        products_data = json.load(f)
    
    if not isinstance(products_data, list):
        products_data = [products_data]
    
    # Convert to ProductData objects
    products = []
    for i, product_data in enumerate(products_data):
        try:
            product = ProductData(**product_data)
            products.append(product)
        except Exception as e:
            click.echo(f"❌ Invalid product data at index {i}: {e}")
            return
    
    click.echo(f"🚀 Starting batch generation for {len(products)} products...")
    
    # Submit batch job
    batch_id = batch_manager.generate_batch(products, priority=priority)
    
    click.echo(f"✅ Batch submitted: {batch_id}")
    click.echo(f"🔍 Status: python cli.py batch status {batch_id}")
    
    if wait:
        _wait_for_batch_completion(batch_id)


@batch.command()
@click.option('--all', is_flag=True, help='Audit all products')
@click.option('--products', help='Comma-separated list of product IDs')
@click.option('--priority', default=0, help='Job priority')
@click.option('--wait', is_flag=True, help='Wait for completion')
def audit(all: bool, products: str, priority: int, wait: bool):
    """Batch audit products"""
    
    if not all and not products:
        raise click.UsageError("Must specify --all or --products")
    
    if all:
        # Get all product IDs
        bundles_dir = Path("output/bundles")
        if not bundles_dir.exists():
            click.echo("❌ No bundles directory found")
            return
        
        product_ids = [d.name for d in bundles_dir.iterdir() if d.is_dir()]
    else:
        product_ids = [pid.strip() for pid in products.split(',')]
    
    if not product_ids:
        click.echo("❌ No products found to audit")
        return
    
    click.echo(f"🔍 Starting batch audit for {len(product_ids)} products...")
    
    # Submit batch job
    batch_id = batch_manager.audit_batch(product_ids, priority=priority)
    
    click.echo(f"✅ Batch submitted: {batch_id}")
    click.echo(f"🔍 Status: python cli.py batch status {batch_id}")
    
    if wait:
        _wait_for_batch_completion(batch_id)


@batch.command()
@click.option('--all', is_flag=True, help='Fix all flagged products')
@click.option('--products', help='Comma-separated list of product IDs')
@click.option('--threshold', default=80.0, help='Score threshold for --all')
@click.option('--priority', default=0, help='Job priority')
@click.option('--wait', is_flag=True, help='Wait for completion')
def fix(all: bool, products: str, threshold: float, priority: int, wait: bool):
    """Batch fix products"""
    
    if not all and not products:
        raise click.UsageError("Must specify --all or --products")
    
    if all:
        # Find products below threshold
        bundles_dir = Path("output/bundles")
        if not bundles_dir.exists():
            click.echo("❌ No bundles directory found")
            return
        
        product_ids = []
        for product_dir in bundles_dir.iterdir():
            if product_dir.is_dir():
                audit_file = product_dir / "audit.json"
                if audit_file.exists():
                    try:
                        with open(audit_file, 'r') as f:
                            audit_data = json.load(f)
                        if audit_data.get('score', 100) < threshold:
                            product_ids.append(product_dir.name)
                    except Exception:
                        continue
    else:
        product_ids = [pid.strip() for pid in products.split(',')]
    
    if not product_ids:
        click.echo(f"✅ No products need fixing (all have score >= {threshold})")
        return
    
    click.echo(f"🔧 Starting batch fix for {len(product_ids)} products...")
    
    # Submit batch job
    batch_id = batch_manager.fix_batch(product_ids, priority=priority)
    
    click.echo(f"✅ Batch submitted: {batch_id}")
    click.echo(f"🔍 Status: python cli.py batch status {batch_id}")
    
    if wait:
        _wait_for_batch_completion(batch_id)


@batch.command()
@click.argument('batch_id')
@click.option('--follow', is_flag=True, help='Follow progress in real-time')
@click.option('--interval', default=5, help='Update interval for --follow (seconds)')
def status(batch_id: str, follow: bool, interval: int):
    """Check batch operation status"""
    
    if follow:
        _follow_batch_progress(batch_id, interval)
    else:
        _show_batch_status(batch_id)


@batch.command()
@click.option('--limit', default=20, help='Number of batches to show')
@click.option('--status-filter', help='Filter by status: running, completed, failed')
def list(limit: int, status_filter: str):
    """List recent batch operations"""
    
    click.echo("📋 Recent Batch Operations:")
    click.echo("-" * 80)
    
    # Get batch statuses
    active_batches = batch_manager.get_active_batches()
    
    # Filter by status if specified
    if status_filter:
        active_batches = [b for b in active_batches if b and b.get('status') == status_filter]
    
    # Sort by creation time and limit
    active_batches = sorted(active_batches, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]
    
    if not active_batches:
        click.echo("No batch operations found")
        return
    
    for batch_info in active_batches:
        batch_id = batch_info['batch_id']
        status = batch_info['status']
        total = batch_info['total_products']
        processed = batch_info['processed_products']
        completion = batch_info['completion_percentage']
        
        status_icon = {
            'running': '🟡',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '⚪'
        }.get(status, '❓')
        
        click.echo(f"{status_icon} {batch_id:<20} {status:<12} {processed}/{total} ({completion:.1f}%)")


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def api(host: str, port: int, reload: bool):
    """Start FastAPI server for external integration"""
    
    try:
        import uvicorn
        from api.app import app
        
        click.echo(f"🚀 Starting Structr API server...")
        click.echo(f"📡 Server: http://{host}:{port}")
        click.echo(f"📖 Docs: http://{host}:{port}/docs")
        click.echo(f"🔄 Reload: {'enabled' if reload else 'disabled'}")
        
        uvicorn.run(
            "api.app:app",
            host=host,
            port=port,
            reload=reload
        )
        
    except ImportError:
        click.echo("❌ uvicorn not installed. Install with: pip install uvicorn")
    except Exception as e:
        click.echo(f"❌ Failed to start API server: {e}")


# Helper functions

def _wait_for_batch_completion(batch_id: str, timeout: int = 3600):
    """Wait for batch completion with progress updates"""
    
    click.echo(f"⏳ Waiting for batch completion...")
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = batch_manager.get_batch_status(batch_id)
        
        if not status:
            click.echo(f"❌ Batch {batch_id} not found")
            return
        
        if status['status'] in ['completed', 'failed', 'cancelled']:
            _show_batch_status(batch_id)
            return
        
        # Show progress
        completion = status['completion_percentage']
        processed = status['processed_products']
        total = status['total_products']
        
        click.echo(f"\r⏳ Progress: {processed}/{total} ({completion:.1f}%)", nl=False)
        
        time.sleep(5)
    
    click.echo(f"\n⏰ Timeout waiting for batch completion")


def _follow_batch_progress(batch_id: str, interval: int):
    """Follow batch progress in real-time"""
    
    click.echo(f"👀 Following batch progress (Ctrl+C to stop)...")
    
    try:
        while True:
            status = batch_manager.get_batch_status(batch_id)
            
            if not status:
                click.echo(f"❌ Batch {batch_id} not found")
                return
            
            # Clear screen and show status
            click.clear()
            _show_batch_status(batch_id)
            
            if status['status'] in ['completed', 'failed', 'cancelled']:
                break
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        click.echo("\n👋 Stopped following batch progress")


def _show_batch_status(batch_id: str):
    """Show detailed batch status"""
    
    status = batch_manager.get_batch_status(batch_id)
    
    if not status:
        click.echo(f"❌ Batch {batch_id} not found")
        return
    
    # Status icon
    status_icon = {
        'running': '🟡',
        'importing': '📥',
        'generating': '⚙️',
        'auditing': '🔍',
        'fixing': '🔧',
        'exporting': '📤',
        'completed': '✅',
        'failed': '❌',
        'cancelled': '⚪'
    }.get(status['status'], '❓')
    
    click.echo(f"\n📊 Batch Status: {batch_id}")
    click.echo("-" * 50)
    click.echo(f"Status: {status_icon} {status['status']}")
    click.echo(f"Progress: {status['processed_products']}/{status['total_products']} ({status['completion_percentage']:.1f}%)")
    click.echo(f"Created: {status['created_at']}")
    
    if status.get('estimated_remaining_time'):
        remaining = status['estimated_remaining_time']
        click.echo(f"ETA: {remaining/60:.1f} minutes")
    
    # Job details
    if status.get('job_details'):
        job_details = status['job_details']
        if job_details.get('started_at'):
            click.echo(f"Started: {job_details['started_at']}")
        if job_details.get('duration'):
            click.echo(f"Duration: {job_details['duration']:.1f}s")
    
    # Results
    if status.get('result'):
        result = status['result']
        click.echo(f"\nResults:")
        click.echo(f"Success: {result.get('success', 'unknown')}")
        if result.get('processing_time'):
            click.echo(f"Processing time: {result['processing_time']:.2f}s")
        if result.get('error'):
            click.echo(f"Error: {result['error']}")


def _export_audit_results(results: List[AuditResult], filepath: str):
    """Export audit results to CSV"""
    
    with open(filepath, 'w', newline='') as csvfile:
        fieldnames = ['product_id', 'score', 'missing_fields', 'flagged_issues', 
                     'schema_errors', 'metadata_issues', 'timestamp']
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'product_id': result.product_id,
                'score': result.score,
                'missing_fields': ', '.join(result.missing_fields),
                'flagged_issues': ', '.join(result.flagged_issues),
                'schema_errors': ', '.join(result.schema_errors),
                'metadata_issues': ', '.join(result.metadata_issues),
                'timestamp': result.timestamp
            })


if __name__ == '__main__':
    cli()