# Frequently Asked Questions

## Common Issues

### Installation and Setup

!!! question "ModuleNotFoundError: No module named 'bs4'"
    This error occurs when BeautifulSoup is not installed. Install missing dependencies:
    ```bash
    pip install beautifulsoup4 lxml html5lib
    # Or use the included installer
    python install_deps.py
    ```

!!! question "Ollama connection refused or not found"
    Make sure Ollama is running and accessible:
    ```bash
    # Install Ollama (macOS)
    brew install ollama
    brew services start ollama
    
    # Or start manually
    ollama serve
    
    # Pull the required model
    ollama pull mistral
    ```

!!! question "Redis connection errors"
    Start Redis server locally:
    ```bash
    # macOS
    brew install redis
    brew services start redis
    
    # Ubuntu/Debian
    sudo apt install redis-server
    sudo systemctl start redis
    ```

### CLI Usage

!!! question "How do I process multiple products at once?"
    Use the batch command for bulk operations:
    ```bash
    # Process CSV file
    python cli.py batch --input catalog.csv --output ./output --parallel 4
    
    # Monitor progress
    python cli.py batch --status
    ```

!!! question "What happens if generation fails?"
    Check the error logs and use the fix command:
    ```bash
    # Check audit results
    python cli.py audit --handle product-handle
    
    # Attempt automated fix
    python cli.py fix --handle product-handle --regenerate
    ```

!!! question "How to export optimized products?"
    Multiple export formats are available:
    ```bash
    # Export to normalized CSV
    python cli.py export --format csv --output catalog_optimized.csv
    
    # Export specific products
    python cli.py export --handles product-1,product-2 --format json
    ```

### Dashboard Issues

!!! question "Dashboard won't start or shows import errors"
    Ensure all dependencies are installed and run from project root:
    ```bash
    cd /path/to/structr
    python install_deps.py
    streamlit run dashboard_app.py
    ```

!!! question "Can't see generated bundles in dashboard"
    Check that bundles exist in the output directory:
    ```bash
    ls -la output/bundles/
    
    # If empty, generate some test products
    python demo_sprint1.py
    ```

### Data Connectors

!!! question "Shopify CSV import fails"
    Verify your CSV has required columns:
    ```bash
    # Required columns: handle, title, body_html, vendor, product_type
    # Check field mapping
    python cli.py connect shopify --analyze-csv your_export.csv
    ```

!!! question "Custom CSV format not recognized"
    Use the generic CSV mapper with field mapping:
    ```bash
    python cli.py connect generic --csv custom_products.csv --mapping mapping.json
    ```

## Troubleshooting

### Log File Locations

| Component | Log Location | Description |
|-----------|-------------|-------------|
| CLI Operations | `output/jobs/*.log` | Command execution logs |
| LLM Generation | `output/bundles/{handle}/sync.json` | Input/output traces |
| Audit Results | `output/bundles/{handle}/audit.json` | Quality scores |
| Dashboard | `dashboard.log` | Streamlit application logs |
| API Server | `api.log` | FastAPI request/response logs |
| Worker Queue | `worker.log` | Background job processing |

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# CLI debug mode
python cli.py --debug enqueue --product-data sample.json

# API debug mode
python cli.py api --debug --port 8000

# Dashboard debug mode
streamlit run dashboard_app.py --logger.level=debug
```

### Performance Tuning

!!! tip "Slow generation times"
    - Use local models (Mistral is faster than GPT-4)
    - Reduce batch size for memory-constrained systems
    - Enable parallel processing: `--parallel 2` for CLI or via dashboard settings

!!! tip "Memory usage"
    - Monitor with `htop` or `activity monitor`
    - Reduce worker count in `config/settings.py`
    - Clear old bundles: `rm -rf output/bundles/old-*`

## Configuration Variables

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | `None` | Fallback for OpenAI models |
| `REDIS_URL` | `redis://localhost:6379` | Job queue backend |
| `DATABASE_URL` | `sqlite:///structr.db` | Metadata storage |
| `OLLAMA_HOST` | `http://localhost:11434` | Local LLM service |
| `DEBUG` | `False` | Enable debug logging |
| `MAX_WORKERS` | `4` | Parallel processing limit |

### CLI Flags

| Flag | Command | Description |
|------|---------|-------------|
| `--debug` | All | Enable verbose logging |
| `--parallel N` | `batch` | Set worker count |
| `--regenerate` | `fix` | Force complete regeneration |
| `--format` | `export` | Output format (csv/json/html) |
| `--only handle` | `fix` | Process single product |
| `--dry-run` | All | Preview without changes |

## Best Practices

### Product Data Quality

!!! success "High-quality inputs lead to better outputs"
    - Provide complete product information (title, description, features)
    - Include pricing and availability data
    - Add high-resolution product images
    - Specify brand and category information

### Schema Optimization

!!! note "Google Rich Results compliance"
    Structr automatically generates valid JSON-LD Product schema, but you can improve results by:
    - Adding product reviews/ratings data
    - Including shipping and return policy information
    - Specifying product variants and options
    - Adding brand and manufacturer details

### Batch Processing

!!! tip "Efficient bulk operations"
    - Process products in batches of 10-50 for optimal performance
    - Monitor system resources during large batches
    - Use CSV format for bulk imports/exports
    - Schedule large operations during off-peak hours

## Getting Help

### Support Channels

- **GitHub Issues**: [github.com/structr/structr](https://github.com/structr/structr)
- **Documentation**: [structr.dev](https://structr.dev)
- **Community Discord**: [discord.gg/structr](https://discord.gg/structr)

### Reporting Bugs

When reporting issues, please include:

1. **Environment details**: OS, Python version, dependency versions
2. **Error messages**: Full stack traces and logs
3. **Reproduction steps**: Minimal example to reproduce the issue
4. **Expected vs actual behavior**: What you expected vs what happened
5. **Sample data**: Anonymized product data that causes the issue

### Feature Requests

We welcome feature requests! Please check existing issues first, then create a new issue with:

- **Use case description**: Why you need this feature
- **Proposed solution**: How you envision it working
- **Alternatives considered**: Other solutions you've tried
- **Implementation willingness**: Whether you'd like to contribute code

## Version History

### Current Version (MVP)

- ✅ Local LLM integration via Ollama
- ✅ CLI-based operations and auditing
- ✅ Streamlit dashboard for visual management
- ✅ Shopify CSV import/export
- ✅ Batch processing and parallel execution
- ✅ FastAPI for programmatic access

### Planned Features

- 🔜 Real-time sync with Shopify Admin API
- 🔜 Additional PIM/CMS connectors
- 🔜 Advanced audit reporting and analytics
- 🔜 Webhooks for external integrations
- 🔜 Multi-language content generation