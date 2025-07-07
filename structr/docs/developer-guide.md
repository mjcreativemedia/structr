# Developer Guide

Welcome to Structr development! This guide covers the project architecture, development setup, contribution guidelines, and how to extend Structr with custom features.

## Project Overview

Structr is built with modern Python practices and follows a modular architecture that makes it easy to understand, test, and extend.

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Core Engine** | Python 3.10+ | Main application logic |
| **Web Framework** | FastAPI | REST API endpoints |
| **Dashboard** | Streamlit | Visual interface |
| **Database** | SQLite/PostgreSQL | Data persistence |
| **Queue System** | Redis + RQ | Background job processing |
| **LLM Integration** | Ollama | Local language models |
| **Testing** | pytest | Unit and integration tests |
| **Documentation** | MkDocs Material | This documentation site |

### Architecture Principles

=== "Local-First"
    - All processing happens locally
    - No mandatory cloud dependencies
    - Privacy-focused design
    - Offline-capable operations

=== "Modular Design"
    - Clear separation of concerns
    - Pluggable components
    - Easy to test and maintain
    - Extensible architecture

=== "CLI-First"
    - Command-line interface is primary
    - Dashboard and API are complementary
    - Automation-friendly
    - CI/CD integration ready

## Project Structure

```
structr/
├── 📁 api/                    # FastAPI REST endpoints
│   ├── app.py                 # Main FastAPI application
│   ├── auth.py                # Authentication middleware
│   ├── middleware.py          # Logging and error handling
│   └── endpoints/             # API route definitions
│       ├── connectors.py      # Connector management
│       ├── batches.py         # Batch operations
│       ├── monitoring.py      # Health and metrics
│       └── webhooks.py        # Webhook handling
├── 📁 batch/                  # Batch processing engine
│   ├── queues/                # Job queue management
│   │   └── job_queue.py       # Thread-safe job queue
│   ├── processors/            # Processing coordination
│   │   ├── batch_manager.py   # High-level job orchestration
│   │   └── parallel_processor.py # Parallel execution
│   └── monitors/              # Progress tracking
│       └── progress_monitor.py # Real-time monitoring
├── 📁 connectors/             # Data source integrations
│   ├── base.py                # Base connector interface
│   ├── shopify/               # Shopify-specific integration
│   │   └── importer.py        # CSV import with mapping
│   ├── generic/               # Universal CSV processing
│   │   └── csv_mapper.py      # AI-powered field detection
│   └── pim/                   # PIM system integration
│       └── connector.py       # API-based PIM sync
├── 📁 dashboard/              # Streamlit web interface
│   ├── dashboard_app.py       # Main dashboard application
│   ├── pages/                 # Individual dashboard pages
│   │   ├── overview.py        # Metrics and insights
│   │   ├── bundle_explorer.py # PDP browsing and preview
│   │   ├── batch_processor.py # Bulk operations interface
│   │   ├── audit_manager.py   # Quality analysis tools
│   │   └── export_center.py   # Data export interface
│   └── utils/                 # Dashboard utilities
│       ├── session_state.py   # State management
│       └── navigation.py      # Navigation components
├── 📁 export/                 # Data export functionality
│   └── csv_exporter.py        # Normalized catalog export
├── 📁 llm_service/            # LLM integration layer
│   └── generator.py           # Ollama integration
├── 📁 models/                 # Data models and schemas
│   ├── pdp.py                 # Product and PDP models
│   └── audit.py               # Audit result models
├── 📁 schemas/                # Schema generation
│   └── schema_generator.py    # JSON-LD Product schema
├── 📁 tests/                  # Test suite
│   ├── test_sprint1.py        # Core functionality tests
│   ├── test_sprint2.py        # Dashboard tests  
│   ├── test_sprint3.py        # Connector and API tests
│   └── conftest.py            # Pytest configuration
├── 📁 examples/               # Example data and demos
│   └── sample_products.json   # Sample product data
├── cli.py                     # Command-line interface
├── fix_broken_pdp.py          # Self-healing module
├── requirements.txt           # Python dependencies
└── config.yml                 # Configuration settings
```

---

## Development Setup

### Prerequisites

Ensure you have the following installed:

- **Python 3.10+** with pip
- **Git** for version control
- **Redis** for job queuing (optional for basic development)
- **Ollama** for LLM integration (optional for full functionality)

### Installation

=== "Development Setup"
    ```bash
    # Clone the repository
    git clone https://github.com/your-org/structr.git
    cd structr
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Install development dependencies
    pip install -r requirements-dev.txt
    
    # Install pre-commit hooks
    pre-commit install
    ```

=== "Docker Development"
    ```bash
    # Build development container
    docker build -f Dockerfile.dev -t structr-dev .
    
    # Run with volume mounts
    docker run -it \
      -v $(pwd):/app \
      -p 8000:8000 \
      -p 8501:8501 \
      structr-dev bash
    ```

### Configuration

=== "Environment Variables"
    ```bash
    # Copy example environment file
    cp .env.example .env
    
    # Edit configuration
    export STRUCTR_OUTPUT_DIR="output"
    export STRUCTR_LOG_LEVEL="DEBUG"
    export STRUCTR_LLM_MODEL="mistral"
    export REDIS_URL="redis://localhost:6379"
    ```

=== "Config File"
    ```yaml title="config.yml"
    # Development configuration
    debug: true
    output_dir: "output"
    log_level: "DEBUG"
    
    # LLM settings
    llm:
      default_model: "mistral"
      base_url: "http://localhost:11434"
      timeout: 120
    
    # Database
    database:
      url: "sqlite:///structr_dev.db"
      
    # API settings
    api:
      host: "0.0.0.0"
      port: 8000
      reload: true
    ```

---

## Running Tests

Structr uses pytest for comprehensive testing across all components.

### Test Structure

```
tests/
├── test_sprint1.py           # Core engine tests
├── test_sprint2.py           # Dashboard tests
├── test_sprint3.py           # Connector and API tests
├── test_integration.py       # End-to-end tests
├── conftest.py               # Shared fixtures
└── fixtures/                 # Test data
    ├── sample_csv/           # Sample CSV files
    ├── sample_json/          # Sample JSON data
    └── expected_outputs/     # Expected test results
```

### Running Tests

=== "All Tests"
    ```bash
    # Run complete test suite
    python -m pytest
    
    # With coverage report
    python -m pytest --cov=. --cov-report=html
    
    # Verbose output
    python -m pytest -v
    ```

=== "Specific Test Categories"
    ```bash
    # Sprint 1 tests (core functionality)
    python -m pytest tests/test_sprint1.py -v
    
    # Sprint 2 tests (dashboard)
    python -m pytest tests/test_sprint2.py -v
    
    # Sprint 3 tests (connectors and API)
    python -m pytest tests/test_sprint3.py -v
    
    # Integration tests
    python -m pytest tests/test_integration.py -v
    ```

=== "Test Specific Components"
    ```bash
    # Test connectors only
    python -m pytest tests/test_sprint3.py::TestShopifyCSVImporter -v
    
    # Test API endpoints
    python -m pytest tests/test_sprint3.py::TestAPIIntegration -v
    
    # Test batch processing
    python -m pytest tests/test_sprint3.py::TestBatchManager -v
    ```

### Writing Tests

=== "Unit Test Example"
    ```python title="tests/test_new_feature.py"
    import pytest
    from unittest.mock import Mock, patch
    from pathlib import Path
    
    from your_module import YourClass
    
    class TestYourClass:
        """Test suite for YourClass"""
        
        def setup_method(self):
            """Setup run before each test method"""
            self.instance = YourClass()
        
        def test_basic_functionality(self):
            """Test basic functionality"""
            result = self.instance.process_data({'test': 'data'})
            assert result.success is True
            assert 'test' in result.data
        
        @patch('your_module.external_service')
        def test_with_mock(self, mock_service):
            """Test with mocked external dependency"""
            mock_service.return_value = {'status': 'success'}
            result = self.instance.call_external_service()
            assert result['status'] == 'success'
            mock_service.assert_called_once()
        
        @pytest.mark.asyncio
        async def test_async_function(self):
            """Test async functionality"""
            result = await self.instance.async_process()
            assert result is not None
    ```

=== "Integration Test Example"
    ```python title="tests/test_integration.py"
    import pytest
    import tempfile
    from pathlib import Path
    
    from cli import main
    from connectors.shopify.importer import ShopifyCSVImporter
    
    class TestEndToEndWorkflow:
        """End-to-end workflow tests"""
        
        @pytest.mark.integration
        def test_csv_import_to_generation(self, sample_csv):
            """Test complete CSV import to PDP generation"""
            
            # Import CSV
            importer = ShopifyCSVImporter()
            result = importer.import_data(sample_csv)
            assert result.success
            
            # Generate PDPs
            from cli import main
            exit_code = main(['enqueue', result.output_file])
            assert exit_code == 0
            
            # Verify output
            output_dir = Path('output/bundles')
            assert output_dir.exists()
            bundles = list(output_dir.glob('*/index.html'))
            assert len(bundles) > 0
    ```

### Test Fixtures

=== "Shared Fixtures"
    ```python title="tests/conftest.py"
    import pytest
    import tempfile
    import pandas as pd
    from pathlib import Path
    
    @pytest.fixture
    def sample_products():
        """Sample product data for testing"""
        return [
            {
                'handle': 'test-product-1',
                'title': 'Test Product 1',
                'description': 'A test product',
                'price': 29.99,
                'brand': 'TestBrand'
            },
            {
                'handle': 'test-product-2',
                'title': 'Test Product 2', 
                'description': 'Another test product',
                'price': 39.99,
                'brand': 'TestBrand'
            }
        ]
    
    @pytest.fixture
    def sample_csv(sample_products):
        """Sample CSV file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df = pd.DataFrame(sample_products)
            df.to_csv(f.name, index=False)
            yield Path(f.name)
        
        # Cleanup
        Path(f.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def temp_output_dir():
        """Temporary output directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    ```

---

## Code Style & Standards

### Python Code Style

Structr follows PEP 8 with additional conventions:

=== "Formatting"
    ```python
    # Use Black for code formatting
    black structr/ tests/
    
    # Import organization
    import os
    import sys
    from pathlib import Path
    from typing import Dict, List, Optional, Union
    
    import pandas as pd
    import requests
    from pydantic import BaseModel
    
    from .local_module import LocalClass
    ```

=== "Naming Conventions"
    ```python
    # Classes: PascalCase
    class PDPGenerator:
        pass
    
    # Functions and variables: snake_case
    def generate_pdp_content():
        product_data = {}
        return product_data
    
    # Constants: UPPER_SNAKE_CASE
    DEFAULT_BATCH_SIZE = 25
    MAX_RETRY_ATTEMPTS = 3
    
    # Private methods: leading underscore
    def _internal_helper_method():
        pass
    ```

=== "Documentation"
    ```python
    def analyze_csv_structure(
        csv_path: Path, 
        connector_type: str = "generic"
    ) -> Dict[str, Any]:
        """
        Analyze CSV structure for field mapping.
        
        Args:
            csv_path: Path to CSV file to analyze
            connector_type: Type of connector ('shopify', 'generic')
            
        Returns:
            Dictionary containing analysis results with keys:
            - field_mapping: Suggested field mappings
            - data_quality: Quality assessment scores
            - recommendations: Optimization suggestions
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If connector_type is unsupported
            
        Example:
            >>> analysis = analyze_csv_structure(Path("products.csv"))
            >>> print(analysis['data_quality']['overall_score'])
            88
        """
        # Implementation here
        pass
    ```

### Linting & Formatting

=== "Pre-commit Hooks"
    ```yaml title=".pre-commit-config.yaml"
    repos:
      - repo: https://github.com/psf/black
        rev: 22.3.0
        hooks:
          - id: black
            language_version: python3.10
      
      - repo: https://github.com/pycqa/isort
        rev: 5.10.1
        hooks:
          - id: isort
            args: ["--profile", "black"]
      
      - repo: https://github.com/pycqa/flake8
        rev: 4.0.1
        hooks:
          - id: flake8
            args: ["--max-line-length=88", "--extend-ignore=E203"]
      
      - repo: https://github.com/pre-commit/mirrors-mypy
        rev: v0.950
        hooks:
          - id: mypy
            additional_dependencies: [types-requests]
    ```

=== "Manual Formatting"
    ```bash
    # Format code
    black structr/ tests/
    
    # Sort imports
    isort structr/ tests/
    
    # Lint code
    flake8 structr/ tests/
    
    # Type checking
    mypy structr/
    ```

---

## Contributing Guidelines

### Contribution Workflow

=== "1. Setup Development Environment"
    ```bash
    # Fork the repository on GitHub
    git clone https://github.com/your-username/structr.git
    cd structr
    
    # Add upstream remote
    git remote add upstream https://github.com/original-org/structr.git
    
    # Create virtual environment and install dependencies
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

=== "2. Create Feature Branch"
    ```bash
    # Update main branch
    git checkout main
    git pull upstream main
    
    # Create feature branch
    git checkout -b feature/your-feature-name
    
    # Or for bug fixes
    git checkout -b fix/issue-description
    ```

=== "3. Make Changes"
    ```bash
    # Make your changes
    # Add tests for new functionality
    # Update documentation if needed
    
    # Run tests to ensure everything works
    python -m pytest
    
    # Format code
    black structr/ tests/
    isort structr/ tests/
    ```

=== "4. Commit Changes"
    ```bash
    # Add files
    git add .
    
    # Commit with descriptive message
    git commit -m "Add intelligent field mapping for BigCommerce CSV imports
    
    - Implement BigCommerce-specific field detection
    - Add confidence scoring for field mappings
    - Include tests for new functionality
    - Update documentation with usage examples"
    ```

=== "5. Submit Pull Request"
    ```bash
    # Push to your fork
    git push origin feature/your-feature-name
    
    # Create pull request on GitHub
    # Include description of changes
    # Reference any related issues
    ```

### Commit Message Format

Follow conventional commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(connectors): add BigCommerce CSV importer with AI field mapping

fix(api): resolve rate limiting issue in batch endpoints

docs(quickstart): add Docker setup instructions

test(sprint3): add integration tests for webhook functionality
```

### Pull Request Guidelines

=== "PR Requirements"
    - [ ] All tests pass
    - [ ] Code follows style guidelines
    - [ ] Documentation updated if needed
    - [ ] New features include tests
    - [ ] Breaking changes are clearly documented
    - [ ] PR description explains the changes

=== "PR Template"
    ```markdown
    ## Description
    Brief description of changes and why they're needed.
    
    ## Type of Change
    - [ ] Bug fix
    - [ ] New feature
    - [ ] Breaking change
    - [ ] Documentation update
    
    ## Testing
    - [ ] Unit tests pass
    - [ ] Integration tests pass
    - [ ] Manual testing completed
    
    ## Checklist
    - [ ] Code follows style guidelines
    - [ ] Self-review completed
    - [ ] Documentation updated
    - [ ] Tests added for new functionality
    ```

---

## Extending Structr

### Adding New Connectors

Create new data source connectors by extending the base connector:

=== "1. Create Connector Class"
    ```python title="connectors/bigcommerce/importer.py"
    from pathlib import Path
    from typing import Dict, List, Any
    
    from ..base import BaseConnector, ImportResult
    from models.pdp import ProductData
    
    class BigCommerceCSVImporter(BaseConnector):
        """BigCommerce CSV import with intelligent field mapping"""
        
        def __init__(self, config=None):
            super().__init__(config)
            self.field_map = {
                'ProductName': 'title',
                'ProductDescription': 'body_html',
                'Price': 'price',
                'Brand': 'vendor',
                'ProductUPC': 'sku'
            }
        
        def detect_csv_structure(self, csv_path: Path) -> Dict[str, Any]:
            """Analyze BigCommerce CSV structure"""
            # Implementation specific to BigCommerce format
            pass
        
        def import_data(self, source: Path) -> ImportResult:
            """Import BigCommerce product data"""
            # Implementation for data transformation
            pass
    ```

=== "2. Add Connector Tests"
    ```python title="tests/test_bigcommerce_connector.py"
    import pytest
    from pathlib import Path
    import tempfile
    import pandas as pd
    
    from connectors.bigcommerce.importer import BigCommerceCSVImporter
    
    class TestBigCommerceCSVImporter:
        
        def setup_method(self):
            self.importer = BigCommerceCSVImporter()
        
        def test_csv_analysis(self, bigcommerce_csv):
            analysis = self.importer.detect_csv_structure(bigcommerce_csv)
            assert analysis['confidence'] > 0.8
            assert 'ProductName' in analysis['columns']
        
        def test_data_import(self, bigcommerce_csv):
            result = self.importer.import_data(bigcommerce_csv)
            assert result.success
            assert result.total_processed > 0
    ```

=== "3. Register Connector"
    ```python title="connectors/__init__.py"
    from .shopify.importer import ShopifyCSVImporter
    from .generic.csv_mapper import GenericCSVMapper
    from .bigcommerce.importer import BigCommerceCSVImporter
    
    AVAILABLE_CONNECTORS = {
        'shopify': ShopifyCSVImporter,
        'generic': GenericCSVMapper,
        'bigcommerce': BigCommerceCSVImporter,
    }
    ```

### Adding New CLI Commands

Extend the CLI with new commands:

=== "1. Add Command Group"
    ```python title="cli.py"
    import click
    
    @cli.group()
    def analytics():
        """Analytics and reporting commands"""
        pass
    
    @analytics.command()
    @click.option('--period', default='7d', help='Analysis period')
    @click.option('--format', default='table', help='Output format')
    def performance(period, format):
        """Analyze performance metrics"""
        from analytics.performance import generate_performance_report
        
        report = generate_performance_report(period)
        
        if format == 'table':
            click.echo(report.to_table())
        elif format == 'json':
            click.echo(report.to_json())
    
    @analytics.command()
    @click.argument('product_ids', nargs=-1)
    def compare(product_ids):
        """Compare multiple products"""
        from analytics.comparison import compare_products
        
        comparison = compare_products(list(product_ids))
        click.echo(comparison.to_table())
    ```

=== "2. Add Implementation"
    ```python title="analytics/performance.py"
    from dataclasses import dataclass
    from typing import List, Dict
    from datetime import datetime, timedelta
    
    @dataclass
    class PerformanceReport:
        period: str
        metrics: Dict[str, float]
        trends: Dict[str, str]
        
        def to_table(self) -> str:
            """Format as table for CLI display"""
            # Implementation
            pass
        
        def to_json(self) -> str:
            """Format as JSON"""
            # Implementation
            pass
    
    def generate_performance_report(period: str) -> PerformanceReport:
        """Generate performance analysis"""
        # Implementation
        pass
    ```

### Adding Dashboard Pages

Create new dashboard pages for custom functionality:

=== "1. Create Page Module"
    ```python title="dashboard/pages/analytics.py"
    import streamlit as st
    import plotly.express as px
    import pandas as pd
    from datetime import datetime, timedelta
    
    def show():
        """Display analytics page"""
        st.header("📊 Analytics & Insights")
        
        # Time period selector
        period = st.selectbox(
            "Analysis Period",
            ["7 days", "30 days", "90 days", "1 year"]
        )
        
        # Load and display metrics
        metrics = load_performance_metrics(period)
        display_performance_charts(metrics)
        
        # Quality trends
        st.subheader("Quality Trends")
        quality_data = load_quality_trends(period)
        display_quality_trends(quality_data)
    
    def display_performance_charts(metrics):
        """Display performance visualization"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Products Generated",
                metrics['total_generated'],
                delta=metrics['generated_change']
            )
        
        with col2:
            st.metric(
                "Average Score",
                f"{metrics['avg_score']:.1f}",
                delta=f"{metrics['score_change']:+.1f}"
            )
        
        with col3:
            st.metric(
                "Success Rate",
                f"{metrics['success_rate']:.1%}",
                delta=f"{metrics['success_change']:+.1%}"
            )
    ```

=== "2. Add to Navigation"
    ```python title="dashboard/utils/navigation.py"
    def get_page_config():
        return {
            "📊 Overview": "pages.overview",
            "📦 Bundle Explorer": "pages.bundle_explorer", 
            "⚡ Batch Processor": "pages.batch_processor",
            "🔍 Audit Manager": "pages.audit_manager",
            "📤 Export Center": "pages.export_center",
            "📈 Analytics": "pages.analytics",  # New page
        }
    ```

### Creating Custom Templates

Add custom PDP generation templates:

=== "1. Template Structure"
    ```html title="templates/ecommerce_modern.html"
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ product.title }} - {{ product.brand }}</title>
        <meta name="description" content="{{ product.meta_description }}">
        
        <!-- Open Graph -->
        <meta property="og:title" content="{{ product.title }}">
        <meta property="og:description" content="{{ product.meta_description }}">
        <meta property="og:image" content="{{ product.featured_image }}">
        
        <!-- JSON-LD Schema -->
        <script type="application/ld+json">
        {{ product.schema_markup | safe }}
        </script>
        
        <style>
            /* Modern ecommerce styles */
            .product-container { /* ... */ }
            .product-gallery { /* ... */ }
            .product-details { /* ... */ }
        </style>
    </head>
    <body>
        <div class="product-container">
            <div class="product-gallery">
                {% for image in product.images %}
                <img src="{{ image.url }}" alt="{{ image.alt_text }}">
                {% endfor %}
            </div>
            
            <div class="product-details">
                <h1>{{ product.title }}</h1>
                <p class="brand">{{ product.brand }}</p>
                <div class="price">${{ product.price }}</div>
                <div class="description">{{ product.description | safe }}</div>
            </div>
        </div>
    </body>
    </html>
    ```

=== "2. Template Configuration"
    ```yaml title="templates/ecommerce_modern.yml"
    name: "Modern E-commerce"
    description: "Clean, modern template for product pages"
    version: "1.0.0"
    
    features:
      - responsive_design
      - schema_markup
      - social_sharing
      - image_gallery
    
    customization:
      colors:
        primary: "#007bff"
        secondary: "#6c757d"
        accent: "#28a745"
      
      typography:
        heading_font: "Helvetica Neue"
        body_font: "Arial"
      
      layout:
        sidebar: false
        breadcrumbs: true
        related_products: true
    ```

---

## Release Process

### Versioning

Structr follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality (backward compatible)
- **PATCH** version for bug fixes (backward compatible)

### Release Checklist

=== "Pre-release"
    - [ ] All tests pass
    - [ ] Documentation updated
    - [ ] CHANGELOG.md updated
    - [ ] Version bumped in `__version__.py`
    - [ ] Migration guides written (if needed)

=== "Release"
    - [ ] Create release branch
    - [ ] Final testing on release branch
    - [ ] Merge to main
    - [ ] Tag release
    - [ ] Build and publish packages
    - [ ] Update GitHub release notes

=== "Post-release"
    - [ ] Announce on communication channels
    - [ ] Update documentation site
    - [ ] Monitor for issues
    - [ ] Plan next release

### Automated Releases

```yaml title=".github/workflows/release.yml"
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install build twine
      
      - name: Build package
        run: python -m build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
```

---

## Getting Help

### Documentation

- **User Documentation**: This documentation site
- **API Reference**: Interactive OpenAPI docs at `/docs`
- **Code Documentation**: Inline docstrings and type hints
- **Examples**: Sample code in `examples/` directory

### Community Resources

- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: General questions and community support
- **Discord**: Real-time chat with developers and users
- **Stack Overflow**: Tag questions with `structr`

### Development Support

For development-specific questions:

1. Check existing issues and documentation
2. Ask in the development Discord channel
3. Create a GitHub issue with detailed information
4. Include code examples and error messages

---

**Ready to contribute?** Start by reading the [Quickstart Guide](quickstart.md) to get familiar with Structr, then dive into the codebase and pick an issue to work on!