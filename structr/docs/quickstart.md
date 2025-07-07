# Quickstart Guide

Get Structr running with sample data in under 5 minutes. This guide will take you from installation to your first optimized PDP.

## Prerequisites

Before starting, ensure you have:

- **Python 3.10+** installed
- **Git** for cloning the repository  
- **Ollama** for local LLM processing (optional for initial demo)

## Step 1: Installation

=== "Git Clone"
    ```bash
    # Clone the repository
    git clone https://github.com/your-org/structr.git
    cd structr
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    
    # Install dependencies
    pip install -r requirements.txt
    ```

=== "Direct Download"
    ```bash
    # Download and extract
    curl -LO https://github.com/your-org/structr/archive/main.zip
    unzip structr-main.zip
    cd structr-main
    
    # Setup environment
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

## Step 2: Quick Demo (No LLM Required)

Let's start with a demo using pre-generated sample data:

```bash
# Run the built-in demo
python demo_sprint1.py
```

??? example "Expected Output"
    ```
    🎯 STRUCTR SPRINT 1 DEMO
    ========================
    ✅ Created sample products
    ✅ Generated 3 PDP bundles
    ✅ Audit results:
       • aiden-1: Score 85/100 (Good)
       • becca-2: Score 92/100 (Excellent) 
       • charlie-3: Score 78/100 (Fair)
    
    📂 Check output/bundles/ for generated files
    ```

## Step 3: Inspect Generated Files

Explore the output directory to see what Structr created:

```bash
# List generated bundles
ls -la output/bundles/

# View a complete bundle
tree output/bundles/aiden-1/
```

??? info "Bundle Structure"
    ```
    output/bundles/aiden-1/
    ├── index.html          # Optimized PDP HTML
    ├── sync.json          # Input data trace
    └── audit.json         # Quality assessment
    ```

View the generated PDP:

```bash
# Open the HTML file
open output/bundles/aiden-1/index.html  # macOS
# OR
xdg-open output/bundles/aiden-1/index.html  # Linux
```

## Step 4: Run CLI Commands

Try some basic CLI operations:

### Audit Existing Bundles
```bash
# Audit all generated bundles
python cli.py audit

# Audit specific product
python cli.py audit aiden-1 --verbose
```

??? example "Audit Output"
    ```
    📊 AUDIT RESULTS
    
    Bundle: aiden-1
    ├── Overall Score: 85/100 (Good)
    ├── Title: ✅ Present (optimal length)
    ├── Meta Description: ⚠️  Too short (recommend 150+ chars)
    ├── Schema: ✅ Valid JSON-LD Product schema
    └── Images: ✅ All images have alt text
    
    💡 Recommendations:
    • Expand meta description for better SEO
    • Add product review schema for rich results
    ```

### Export Optimized Data
```bash
# Export all bundles to CSV
python cli.py export --format csv --output catalog_optimized.csv

# View exported data
head -5 catalog_optimized.csv
```

### Fix Identified Issues
```bash
# Fix issues in a specific product
python cli.py fix aiden-1 --issues meta_description

# Bulk fix all products with low scores
python cli.py fix --score-below 80
```

## Step 5: Launch the Dashboard

Experience the visual interface:

```bash
# Start the Streamlit dashboard
python start_dashboard.py
```

The dashboard will open at `http://localhost:8501` and show:

- 📊 **Overview**: Catalog metrics and quality scores
- 📦 **Bundle Explorer**: Browse and preview generated PDPs  
- ⚡ **Batch Processor**: Upload CSVs and run bulk operations
- 🔍 **Audit Manager**: Detailed quality analysis and reports

![Dashboard Screenshot](assets/dashboard-overview.png)

## Step 6: Import Your Own Data

### Option A: Use Sample CSV

Create a simple product CSV:

```csv title="my_products.csv"
handle,title,description,price,brand
test-product,My Test Product,A great product for testing Structr,29.99,TestBrand
another-item,Another Product,This is another sample product,19.99,TestBrand
```

Import via CLI:
```bash
python cli.py batch generate --csv my_products.csv --workers 2
```

### Option B: Connect Shopify

If you have a Shopify store, export your products and import:

```bash
# Analyze your Shopify CSV
python cli.py connect shopify --csv shopify_products.csv --analyze

# Import and generate PDPs
python cli.py connect shopify --csv shopify_products.csv --batch-size 25
```

## Step 7: Optional - Setup Local LLM

For full functionality, install Ollama for local LLM processing:

=== "macOS"
    ```bash
    # Install Ollama
    brew install ollama
    
    # Start service
    brew services start ollama
    
    # Download model
    ollama pull mistral
    ```

=== "Linux"
    ```bash
    # Install Ollama
    curl -fsSL https://ollama.ai/install.sh | sh
    
    # Start service
    ollama serve &
    
    # Download model  
    ollama pull mistral
    ```

=== "Windows"
    ```powershell
    # Download from https://ollama.ai
    # Run installer and follow prompts
    
    # Pull model
    ollama pull mistral
    ```

Test LLM integration:
```bash
# Generate fresh content with LLM
python cli.py enqueue examples/sample_products.json --model mistral

# Monitor generation progress
python cli.py batch status
```

## Next Steps

Congratulations! You now have Structr running. Here's what to explore next:

<div class="grid cards" markdown>

-   :material-console-line:{ .lg .middle } **Master the CLI**

    ---

    Learn all available commands for advanced workflows

    [:octicons-arrow-right-24: CLI Commands](cli-commands.md)

-   :material-view-dashboard:{ .lg .middle } **Explore the Dashboard**

    ---

    Discover visual tools for managing large catalogs

    [:octicons-arrow-right-24: Dashboard Usage](dashboard-usage.md)

-   :material-connection:{ .lg .middle } **Setup Connectors**

    ---

    Import from Shopify, APIs, and custom data sources

    [:octicons-arrow-right-24: Connectors Guide](connectors-guide.md)

-   :material-api:{ .lg .middle } **API Integration**

    ---

    Integrate Structr with your existing systems

    [:octicons-arrow-right-24: API Reference](api-reference.md)

</div>

## Troubleshooting

!!! bug "Common Issues"

    === "Import Errors"
        **Problem**: `ImportError: No module named 'structr'`
        
        **Solution**: Ensure virtual environment is activated:
        ```bash
        source venv/bin/activate  # Linux/macOS
        # OR
        venv\Scripts\activate     # Windows
        ```

    === "Port Already in Use"
        **Problem**: Dashboard won't start, port 8501 in use
        
        **Solution**: Use a different port:
        ```bash
        streamlit run dashboard_app.py --server.port 8502
        ```

    === "Ollama Connection Failed"
        **Problem**: LLM generation fails with connection error
        
        **Solution**: Check Ollama is running:
        ```bash
        ollama list  # Should show installed models
        ollama serve # Start if not running
        ```

    === "Permission Denied"
        **Problem**: Can't write to output directory
        
        **Solution**: Check permissions:
        ```bash
        mkdir -p output/bundles
        chmod 755 output/bundles
        ```

Need more help? Check our [FAQ](faq.md) or [Developer Guide](developer-guide.md).

---

🎉 **You're ready!** Structr is now generating SEO-optimized PDPs. Start with your product catalog and watch your content quality improve automatically.