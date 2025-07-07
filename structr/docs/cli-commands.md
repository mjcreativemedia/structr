# CLI Commands Reference

Structr's command-line interface provides powerful tools for generating, auditing, and managing Product Detail Pages (PDPs). All commands support both interactive and automated workflows.

## Command Overview

```bash
python cli.py <command> [options]
```

| Command | Purpose | Sprint |
|---------|---------|--------|
| [`enqueue`](#enqueue) | Queue single product for generation | 1 |
| [`audit`](#audit) | Analyze PDP quality and compliance | 1 |
| [`fix`](#fix) | Repair identified issues automatically | 1 |
| [`export`](#export) | Export optimized data to various formats | 1 |
| [`connect`](#connect) | Import from external data sources | 3 |
| [`batch`](#batch) | Manage bulk operations and job queues | 3 |

## `enqueue` - Generate PDPs

Queue a product for PDP generation using local LLMs.

### Syntax
```bash
python cli.py enqueue <input> [options]
```

### Arguments
- `input` - Path to JSON file or product data

### Options
- `--model TEXT` - LLM model to use (default: `mistral`)
- `--template TEXT` - Output template (default: `default`)
- `--priority INTEGER` - Job priority 1-10 (default: `5`)
- `--async` - Run asynchronously without waiting

### Examples

=== "Single Product"
    ```bash
    # Generate PDP for a product
    python cli.py enqueue examples/sample_product.json
    ```

=== "Custom Model"
    ```bash
    # Use specific LLM model
    python cli.py enqueue product.json --model llama2
    ```

=== "Async Processing"
    ```bash
    # Queue without waiting for completion
    python cli.py enqueue product.json --async
    ```

=== "High Priority"
    ```bash
    # Process with high priority
    python cli.py enqueue urgent_product.json --priority 9
    ```

### Input Format

Products should be provided as JSON:

```json title="sample_product.json"
{
  "handle": "summer-dress-blue",
  "title": "Summer Blue Dress",
  "description": "Light and airy summer dress perfect for warm days",
  "price": 89.99,
  "brand": "FashionCo",
  "category": "Dresses",
  "features": ["breathable fabric", "machine washable", "midi length"],
  "images": ["https://example.com/dress1.jpg"],
  "sku": "DRESS-001"
}
```

### Output

??? example "Expected Output"
    ```
    ✅ Product enqueued successfully
    📝 Job ID: pdp_gen_20250706_123456
    ⏱️  Estimated completion: 30-60 seconds
    📂 Output will be saved to: output/bundles/summer-dress-blue/
    
    🔄 Processing...
    ✅ Generation complete!
    📊 Audit score: 87/100 (Good)
    ```

---

## `audit` - Quality Analysis

Analyze existing PDP bundles for SEO compliance and content quality.

### Syntax
```bash
python cli.py audit [product_id] [options]
```

### Arguments
- `product_id` - Specific product to audit (optional, audits all if omitted)

### Options
- `--format TEXT` - Output format: `table`, `json`, `csv` (default: `table`)
- `--min-score INTEGER` - Only show products below this score
- `--issues-only` - Show only products with issues
- `--export PATH` - Export results to file
- `--verbose` - Show detailed analysis

### Examples

=== "Audit All Products"
    ```bash
    # Audit entire catalog
    python cli.py audit
    ```

=== "Specific Product"
    ```bash
    # Audit single product with details
    python cli.py audit summer-dress-blue --verbose
    ```

=== "Low Quality Products"
    ```bash
    # Find products needing attention
    python cli.py audit --min-score 80 --issues-only
    ```

=== "Export Audit Report"
    ```bash
    # Generate audit report
    python cli.py audit --format csv --export audit_report.csv
    ```

### Output

??? example "Audit Results"
    ```
    📊 AUDIT RESULTS (3 products analyzed)
    
    ┌─────────────────┬───────┬──────────┬─────────────────┐
    │ Product         │ Score │ Status   │ Issues          │
    ├─────────────────┼───────┼──────────┼─────────────────┤
    │ summer-dress    │ 92/100│ Excellent│ None            │
    │ winter-coat     │ 78/100│ Fair     │ Meta desc, Alt  │
    │ spring-shoes    │ 85/100│ Good     │ Schema warning  │
    └─────────────────┴───────┴──────────┴─────────────────┘
    
    💡 Summary:
    • 1 product excellent (90+ score)
    • 1 product good (80-89 score)  
    • 1 product needs improvement (<80 score)
    ```

### Detailed Analysis

Use `--verbose` for comprehensive insights:

??? example "Verbose Audit Output"
    ```
    📊 DETAILED AUDIT: summer-dress-blue
    
    ✅ TITLE (100/100)
    • Length: 48 characters (optimal: 30-60)
    • Keywords: Contains target keywords
    • Uniqueness: No duplicates found
    
    ⚠️  META DESCRIPTION (70/100)
    • Length: 128 characters (recommend: 150-160)
    • Keywords: Well optimized
    • Call-to-action: Missing
    
    ✅ SCHEMA (100/100)
    • Valid JSON-LD Product schema
    • All required fields present
    • Google Rich Results compatible
    
    🎯 RECOMMENDATIONS:
    1. Expand meta description to 150+ characters
    2. Add call-to-action phrase
    3. Include customer review schema
    ```

---

## `fix` - Automated Repair

Automatically fix identified issues in existing PDP bundles.

### Syntax
```bash
python cli.py fix [product_id] [options]
```

### Arguments
- `product_id` - Product to fix (optional, fixes all flagged if omitted)

### Options
- `--issues LIST` - Specific issues to fix: `title`, `meta`, `schema`, `images`
- `--score-below INTEGER` - Fix products below this score
- `--dry-run` - Preview fixes without applying
- `--backup` - Create backup before fixing
- `--model TEXT` - LLM model for content regeneration

### Examples

=== "Fix Specific Product"
    ```bash
    # Fix all issues in a product
    python cli.py fix summer-dress-blue
    ```

=== "Fix Specific Issues"
    ```bash
    # Fix only meta descriptions
    python cli.py fix --issues meta_description
    ```

=== "Bulk Fix Low Scores"
    ```bash
    # Fix all products scoring below 80
    python cli.py fix --score-below 80
    ```

=== "Preview Changes"
    ```bash
    # See what would be fixed without applying
    python cli.py fix summer-dress-blue --dry-run
    ```

### Output

??? example "Fix Results"
    ```
    🔧 FIXING: summer-dress-blue
    
    📋 Issues identified:
    • Meta description too short (128 chars → target: 150+)
    • Missing alt text on 2 images
    • Schema missing review markup
    
    🤖 Generating fixes...
    ✅ Meta description expanded: 128 → 156 characters
    ✅ Alt text added to product images
    ✅ Review schema template added
    
    📊 Score improvement: 78 → 91 (+13 points)
    💾 Updated bundle saved to: output/bundles/summer-dress-blue/
    ```

---

## `export` - Data Export

Export optimized PDP data to various formats for use in other systems.

### Syntax
```bash
python cli.py export [options]
```

### Options
- `--format TEXT` - Export format: `csv`, `json`, `html`, `xml` (default: `csv`)
- `--output PATH` - Output file path
- `--products LIST` - Specific products to export
- `--fields LIST` - Fields to include in export
- `--template TEXT` - Export template to use

### Examples

=== "Export Catalog CSV"
    ```bash
    # Export all products to CSV
    python cli.py export --format csv --output optimized_catalog.csv
    ```

=== "Export Specific Products"
    ```bash
    # Export selected products
    python cli.py export --products summer-dress,winter-coat --format json
    ```

=== "Custom Fields"
    ```bash
    # Export only specific fields
    python cli.py export --fields handle,title,meta_description --format csv
    ```

=== "Shopify Import Format"
    ```bash
    # Export in Shopify-compatible format
    python cli.py export --template shopify --output shopify_import.csv
    ```

### Export Formats

=== "CSV"
    ```csv
    handle,title,description,meta_description,schema_markup,audit_score
    summer-dress,Summer Blue Dress,Light and airy...,Perfect summer dress...,{...},92
    winter-coat,Warm Winter Coat,Cozy winter coat...,Stay warm this winter...,{...},85
    ```

=== "JSON"
    ```json
    {
      "products": [
        {
          "handle": "summer-dress",
          "optimized_html": "<!DOCTYPE html>...",
          "metadata": {
            "title": "Summer Blue Dress...",
            "description": "Perfect summer dress..."
          },
          "schema": {...},
          "audit_score": 92
        }
      ],
      "export_info": {
        "generated_at": "2025-07-06T12:00:00Z",
        "total_products": 2
      }
    }
    ```

---

## `connect` - Data Import

Import product data from external sources using intelligent connectors.

### Syntax
```bash
python cli.py connect <connector> [options]
```

### Connectors
- `shopify` - Shopify CSV exports
- `generic` - Any CSV format with mapping
- `api` - REST API endpoints
- `webhook` - Webhook data

### Global Options
- `--analyze` - Analyze data structure without importing
- `--batch-size INTEGER` - Products per batch (default: 25)
- `--workers INTEGER` - Parallel workers (default: 2)

### Shopify Connector

```bash
python cli.py connect shopify [options]
```

#### Options
- `--csv PATH` - Shopify CSV export file
- `--store TEXT` - Store domain for API access
- `--token TEXT` - Admin API access token
- `--auto-map` - Use automatic field mapping

#### Examples

=== "Analyze Shopify CSV"
    ```bash
    # Analyze CSV structure and mapping
    python cli.py connect shopify --csv products.csv --analyze
    ```

=== "Import Shopify CSV"
    ```bash
    # Import with automatic mapping
    python cli.py connect shopify --csv products.csv --auto-map --batch-size 50
    ```

=== "Shopify API Import"
    ```bash
    # Import directly from Shopify API
    python cli.py connect shopify --store mystore.myshopify.com --token ACCESS_TOKEN
    ```

### Generic CSV Connector

```bash
python cli.py connect generic [options]
```

#### Options
- `--csv PATH` - CSV file to import
- `--mapping PATH` - Field mapping configuration file
- `--create-mapping` - Generate mapping template

#### Examples

=== "Analyze Generic CSV"
    ```bash
    # Intelligent field analysis
    python cli.py connect generic --csv products.csv --analyze
    ```

=== "Create Mapping Template"
    ```bash
    # Generate mapping file
    python cli.py connect generic --csv products.csv --create-mapping
    ```

=== "Import with Mapping"
    ```bash
    # Import using custom mapping
    python cli.py connect generic --csv products.csv --mapping mapping.json
    ```

### Mapping File Format

```json title="mapping.json"
{
  "field_mapping": {
    "handle": "product_id",
    "title": "product_name", 
    "description": "product_description",
    "price": "retail_price",
    "brand": "manufacturer"
  },
  "transformations": {
    "price": "float",
    "features": "split_comma"
  }
}
```

---

## `batch` - Job Management

Manage bulk operations and monitor job queues.

### Syntax
```bash
python cli.py batch <action> [options]
```

### Actions
- `generate` - Bulk PDP generation
- `audit` - Bulk quality analysis  
- `fix` - Bulk issue repair
- `status` - Job queue status
- `cancel` - Cancel running jobs
- `clear` - Clear completed jobs

### Examples

=== "Bulk Generation"
    ```bash
    # Generate PDPs for multiple products
    python cli.py batch generate --products products.json --workers 4
    ```

=== "Monitor Jobs"
    ```bash
    # Check job queue status
    python cli.py batch status
    ```

=== "Bulk Audit"
    ```bash
    # Audit all existing bundles
    python cli.py batch audit --export audit_results.csv
    ```

=== "Bulk Fix"
    ```bash
    # Fix all products below score threshold
    python cli.py batch fix --score-below 85 --issues meta_description,schema
    ```

### Job Status Output

??? example "Batch Status"
    ```
    📊 JOB QUEUE STATUS
    
    🔄 Active Jobs:
    ├── batch_gen_001: Generating PDPs (Progress: 45/100)
    └── batch_audit_002: Auditing catalog (Progress: 23/50)
    
    ✅ Completed (Last 24h): 5 jobs
    ❌ Failed: 0 jobs
    ⏳ Queued: 2 jobs
    
    📈 Performance:
    • Average generation time: 2.3 seconds/product
    • Success rate: 98.5%
    • Queue utilization: 75%
    ```

---

## Global Options

These options work with all commands:

- `--help` - Show command help
- `--verbose` - Detailed output
- `--quiet` - Minimal output
- `--config PATH` - Custom config file
- `--output-dir PATH` - Custom output directory
- `--log-level TEXT` - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`

### Examples

```bash
# Verbose output with custom config
python cli.py audit --verbose --config custom.yml

# Quiet mode with custom output directory
python cli.py enqueue product.json --quiet --output-dir /tmp/structr

# Debug logging
python cli.py batch generate --log-level DEBUG
```

---

## Configuration

Commands can be configured via:

1. **Command-line options** (highest priority)
2. **Config file** (`config.yml`)
3. **Environment variables**
4. **Default values** (lowest priority)

### Config File Example

```yaml title="config.yml"
# Global settings
output_dir: "output"
log_level: "INFO"

# LLM settings
llm:
  default_model: "mistral"
  timeout: 60
  max_retries: 3

# Batch processing
batch:
  default_workers: 2
  max_queue_size: 1000
  job_timeout: 300

# Connectors
connectors:
  shopify:
    batch_size: 25
    auto_mapping: true
  generic:
    confidence_threshold: 0.8
```

### Environment Variables

```bash
export STRUCTR_OUTPUT_DIR="/custom/output"
export STRUCTR_LLM_MODEL="llama2"
export STRUCTR_BATCH_WORKERS="4"
export STRUCTR_LOG_LEVEL="DEBUG"
```

---

## Tips & Tricks

!!! tip "Performance Optimization"

    === "Parallel Processing"
        Use multiple workers for large catalogs:
        ```bash
        python cli.py batch generate --workers 4
        ```

    === "Batch Size Tuning"
        Optimize batch size for your system:
        ```bash
        # Small batches for limited memory
        python cli.py connect shopify --batch-size 10
        
        # Large batches for powerful systems
        python cli.py connect shopify --batch-size 100
        ```

    === "Async Operations"
        Queue jobs and monitor separately:
        ```bash
        python cli.py enqueue products.json --async
        python cli.py batch status
        ```

!!! warning "Common Pitfalls"

    === "Large File Imports"
        For very large CSV files, use streaming:
        ```bash
        python cli.py connect generic --csv huge_file.csv --batch-size 10 --workers 1
        ```

    === "Memory Usage"
        Monitor memory with large catalogs:
        ```bash
        # Limit concurrent operations
        python cli.py batch generate --workers 2
        ```

    === "Disk Space"
        Clean up old bundles periodically:
        ```bash
        python cli.py batch clear --older-than 30d
        ```

---

Next: Explore the [Dashboard Usage](dashboard-usage.md) for visual management tools.