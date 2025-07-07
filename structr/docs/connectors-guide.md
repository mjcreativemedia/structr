# Connectors Guide

Structr's connector system enables seamless data import from various e-commerce platforms, APIs, and data sources. Each connector provides intelligent field mapping, data validation, and automated transformation to Structr's internal format.

## Connector Overview

| Connector | Purpose | Accuracy | Use Cases |
|-----------|---------|----------|-----------|
| [Shopify CSV](#shopify-csv-connector) | Import Shopify exports | 95%+ | Store migrations, bulk updates |
| [Generic CSV](#generic-csv-connector) | Any CSV format | 85%+ | Custom catalogs, PIM exports |
| [PIM API](#pim-api-connector) | Real-time PIM sync | 90%+ | Live inventory, content updates |
| [REST API](#rest-api-connector) | Custom endpoints | Varies | Headless commerce, custom systems |
| [Webhooks](#webhook-connector) | Event-driven updates | 100% | Real-time sync, automated workflows |

---

## Shopify CSV Connector

Import product data from Shopify CSV exports with automatic field detection and intelligent mapping.

### Quick Start

=== "CLI Usage"
    ```bash
    # Analyze Shopify CSV structure
    python cli.py connect shopify --csv products.csv --analyze
    
    # Import with automatic mapping
    python cli.py connect shopify --csv products.csv --batch-size 50
    ```

=== "Dashboard Usage"
    1. Navigate to **Batch Processor** → **Connectors** tab
    2. Select **Shopify CSV Importer**
    3. Upload your Shopify product export
    4. Review field mapping and confidence scores
    5. Configure import options and start processing

### Supported Shopify Fields

The connector automatically maps Shopify fields to Structr's format:

| Shopify Field | Structr Field | Confidence | Notes |
|---------------|---------------|------------|-------|
| `Handle` | `id` | 100% | Primary identifier |
| `Title` | `title` | 100% | Product name |
| `Body (HTML)` | `body_html` | 100% | Description content |
| `Vendor` | `vendor` | 100% | Brand/manufacturer |
| `Type` | `product_type` | 95% | Category classification |
| `Tags` | `tags` | 90% | Comma-separated keywords |
| `Variant Price` | `price` | 100% | Primary price |
| `Variant SKU` | `sku` | 95% | Stock keeping unit |
| `Image Src` | `images` | 85% | Product images |

### CSV Analysis

Before importing, analyze your CSV structure:

??? example "Analysis Results"
    ```
    📊 SHOPIFY CSV ANALYSIS
    
    📁 File: shopify_products_export.csv
    📝 Products: 150
    🏷️  Columns: 25 detected
    🎯 Confidence: 96% (Excellent)
    ⏱️  Estimated Import Time: 2m 30s
    
    🔗 INTELLIGENT FIELD MAPPING:
    
    Required Fields (100% mapped):
    ✅ Handle          → id
    ✅ Title           → title  
    ✅ Body (HTML)     → body_html
    ✅ Vendor          → vendor
    ✅ Variant Price   → price
    
    Optional Fields (85% mapped):
    ✅ Tags            → tags
    ✅ Type            → product_type
    ✅ Image Src       → images
    ⚠️  Custom fields  → metafields (requires review)
    
    📊 DATA QUALITY ASSESSMENT:
    
    Completeness:
    ├── Title: 100% (150/150)
    ├── Description: 98% (147/150)
    ├── Price: 100% (150/150)
    ├── Images: 89% (134/150)
    └── Vendor: 95% (143/150)
    
    Consistency:
    ├── Price format: ✅ Consistent currency
    ├── Handle format: ✅ URL-safe handles
    ├── Image URLs: ⚠️  3 invalid URLs detected
    └── HTML content: ✅ Well-formed markup
    ```

### Advanced Configuration

Customize the import process with detailed options:

=== "Field Mapping Override"
    ```json title="shopify_mapping.json"
    {
      "field_mapping": {
        "Handle": "id",
        "Title": "title",
        "Body (HTML)": "body_html",
        "Custom Field 1": "features",
        "Custom Field 2": "specifications"
      },
      "transformations": {
        "price": "float",
        "tags": "split_comma",
        "custom_fields": "json_parse"
      },
      "validation": {
        "required_fields": ["Handle", "Title", "Variant Price"],
        "price_min": 0.01,
        "handle_format": "^[a-z0-9-]+$"
      }
    }
    ```

=== "Import Options"
    ```bash
    python cli.py connect shopify \
        --csv products.csv \
        --mapping shopify_mapping.json \
        --batch-size 25 \
        --workers 3 \
        --validate-strict \
        --auto-fix-enabled \
        --skip-duplicates
    ```

### Variant Handling

Shopify's variant system is automatically processed:

??? info "Variant Processing Logic"
    ```
    🔄 VARIANT PROCESSING
    
    Product: "T-Shirt" (Handle: basic-tshirt)
    ├── Variant 1: Size=S, Color=Red  → SKU: TSHIRT-S-RED
    ├── Variant 2: Size=M, Color=Red  → SKU: TSHIRT-M-RED  
    ├── Variant 3: Size=L, Color=Blue → SKU: TSHIRT-L-BLUE
    └── Variant 4: Size=S, Color=Blue → SKU: TSHIRT-S-BLUE
    
    Structr Output:
    ├── Primary Product: basic-tshirt
    │   ├── Title: "T-Shirt"
    │   ├── Price: $19.99 (lowest variant)
    │   ├── Images: [red_tshirt.jpg, blue_tshirt.jpg]
    │   └── Variants: 4 variations
    └── Metafields:
        ├── sizes: ["S", "M", "L"]
        ├── colors: ["Red", "Blue"]
        └── price_range: "$19.99 - $24.99"
    ```

---

## Generic CSV Connector

Import any CSV format using AI-powered field detection and intelligent mapping suggestions.

### How It Works

The Generic CSV Connector uses machine learning to analyze your CSV structure and suggest optimal field mappings:

```mermaid
graph LR
    A[Upload CSV] --> B[Structure Analysis]
    B --> C[AI Field Detection]
    C --> D[Confidence Scoring]
    D --> E[Mapping Suggestions]
    E --> F[User Review]
    F --> G[Data Transformation]
    G --> H[Import to Structr]
```

### Supported CSV Formats

The connector works with any CSV containing product data:

=== "E-commerce Platforms"
    - BigCommerce exports
    - WooCommerce data
    - Magento catalogs
    - Custom marketplace formats

=== "PIM Systems"
    - Akeneo exports
    - Contentful data
    - Sanity product data
    - Custom PIM formats

=== "Inventory Systems"
    - ERP system exports
    - Warehouse management data
    - Supplier catalogs
    - Legacy system data

### AI-Powered Field Detection

The system analyzes column names, data patterns, and content to suggest mappings:

??? example "Field Detection Examples"
    ```
    🤖 AI FIELD ANALYSIS
    
    Column: "product_name"
    ├── Similarity to "title": 95%
    ├── Content pattern: Text (avg 45 chars)
    ├── Uniqueness: 100% unique values
    └── Suggestion: title (High confidence)
    
    Column: "item_description"  
    ├── Similarity to "description": 89%
    ├── Content pattern: Long text (avg 200 chars)
    ├── HTML detection: 15% contain HTML tags
    └── Suggestion: body_html (High confidence)
    
    Column: "retail_cost"
    ├── Similarity to "price": 78%
    ├── Content pattern: Numeric (currency format)
    ├── Range: $5.99 - $299.99
    └── Suggestion: price (Medium confidence)
    
    Column: "manufacturer_name"
    ├── Similarity to "brand": 92%
    ├── Content pattern: Brand names
    ├── Unique values: 25 distinct brands
    └── Suggestion: vendor (High confidence)
    ```

### Usage Examples

=== "Simple Analysis"
    ```bash
    # Quick analysis of any CSV
    python cli.py connect generic --csv products.csv --analyze
    ```

=== "Guided Mapping"
    ```bash
    # Generate mapping template
    python cli.py connect generic --csv products.csv --create-mapping
    
    # Review and edit generated mapping.json
    # Then import with custom mapping
    python cli.py connect generic --csv products.csv --mapping mapping.json
    ```

=== "Dashboard Import"
    1. Upload CSV in **Generic CSV Importer** tab
    2. Review AI-suggested mappings
    3. Adjust mappings as needed
    4. Preview transformation results
    5. Configure validation and import

### Data Quality Assessment

The connector evaluates data quality across multiple dimensions:

=== "Completeness Analysis"
    ```
    📊 DATA COMPLETENESS
    
    Field           | Coverage | Quality
    ----------------|----------|--------
    product_name    |   100%   | ✅ Excellent
    description     |    94%   | ✅ Good
    price          |   100%   | ✅ Excellent
    brand          |    87%   | ⚠️  Fair
    images         |    76%   | ⚠️  Needs improvement
    sku            |   100%   | ✅ Excellent
    
    Overall Score: 88/100 (Good)
    ```

=== "Consistency Checks"
    ```
    🔍 CONSISTENCY ANALYSIS
    
    Price Format:
    ✅ 95% follow currency format ($XX.XX)
    ⚠️  5% missing currency symbol
    
    Product Names:
    ✅ 89% follow title case
    ⚠️  11% all uppercase (auto-fix available)
    
    Image URLs:
    ✅ 92% valid HTTP/HTTPS URLs
    ❌ 8% invalid or broken links
    
    SKU Pattern:
    ✅ 78% follow standard format
    ⚠️  22% inconsistent patterns
    ```

### Advanced Mapping Features

=== "Field Transformations"
    ```json title="advanced_mapping.json"
    {
      "field_mapping": {
        "product_title": "title",
        "long_description": "body_html",
        "price_usd": "price",
        "brand_name": "vendor"
      },
      "transformations": {
        "title": {
          "type": "text_transform",
          "operations": ["trim", "title_case", "remove_html"]
        },
        "price": {
          "type": "currency",
          "currency": "USD",
          "validate_range": [0.01, 10000]
        },
        "features": {
          "type": "split",
          "delimiter": "|",
          "cleanup": true
        }
      },
      "validation": {
        "required_fields": ["title", "price"],
        "unique_fields": ["sku"],
        "format_rules": {
          "email": "^[\\w\\.-]+@[\\w\\.-]+\\.[a-zA-Z]{2,}$",
          "url": "^https?://.*"
        }
      }
    }
    ```

=== "Data Enrichment"
    ```json title="enrichment_rules.json"
    {
      "enrichment": {
        "auto_generate": {
          "handle": {
            "source": "title",
            "transform": "slugify"
          },
          "meta_title": {
            "template": "{title} - {brand} | Your Store"
          },
          "meta_description": {
            "template": "Shop {title} by {brand}. {description|truncate:120}"
          }
        },
        "categorization": {
          "auto_detect": true,
          "rules": [
            {
              "condition": "title contains 'shirt'",
              "category": "Apparel > Shirts"
            },
            {
              "condition": "brand = 'Nike'",
              "category": "Sports > Athletic"
            }
          ]
        }
      }
    }
    ```

---

## PIM API Connector

Connect to Product Information Management (PIM) systems for real-time data synchronization.

### Supported PIM Systems

=== "Popular PIMs"
    - **Akeneo**: Open-source PIM platform
    - **Contentful**: Headless CMS with product management
    - **Sanity**: Structured content platform
    - **Pimcore**: Enterprise PIM/MDM solution
    - **inRiver**: Cloud-based PIM platform

=== "Commerce Platforms"
    - **Shopify Plus**: Advanced Shopify features
    - **BigCommerce Enterprise**: API-driven commerce
    - **Magento Commerce**: Adobe's enterprise solution
    - **Salesforce Commerce**: B2B/B2C commerce platform

### Configuration

Set up PIM connections with API credentials:

=== "Contentful Setup"
    ```yaml title="connectors/pim_config.yml"
    contentful:
      space_id: "your_space_id"
      access_token: "your_access_token"
      environment: "master"
      content_type: "product"
      
      field_mapping:
        title: "name"
        description: "description"
        price: "price"
        images: "gallery"
        brand: "brand.name"
        
      sync_options:
        batch_size: 50
        rate_limit: 10  # requests per second
        include_drafts: false
        webhook_enabled: true
    ```

=== "Custom API Setup"
    ```yaml title="connectors/api_config.yml"
    custom_api:
      base_url: "https://api.yourpim.com/v1"
      authentication:
        type: "bearer_token"
        token: "your_api_token"
        
      endpoints:
        products: "/products"
        categories: "/categories"
        brands: "/brands"
        
      field_mapping:
        id: "product_id"
        title: "product_name"
        description: "long_description"
        price: "retail_price"
        
      pagination:
        type: "offset"
        page_size: 100
        max_pages: 50
    ```

### Real-time Synchronization

Enable continuous sync with webhook support:

=== "Webhook Configuration"
    ```python
    # Configure webhook endpoint
    python cli.py connect pim --setup-webhook \
        --endpoint https://yourpim.com/webhooks \
        --events product.created,product.updated \
        --secret your_webhook_secret
    ```

=== "Scheduled Sync"
    ```bash
    # Setup recurring sync
    python cli.py connect pim --schedule \
        --interval 1h \
        --batch-size 100 \
        --incremental-only
    ```

### Data Flow Management

Control how data flows between systems:

??? example "Bi-directional Sync"
    ```
    🔄 BI-DIRECTIONAL SYNC FLOW
    
    PIM System ↔ Structr ↔ E-commerce Platform
    
    From PIM to Structr:
    ├── Product data updates
    ├── New product creation
    ├── Inventory changes
    └── Category modifications
    
    From Structr to PIM:
    ├── Optimized descriptions
    ├── SEO metadata
    ├── Quality scores
    └── Audit findings
    
    From Structr to Commerce:
    ├── Optimized content
    ├── Schema markup
    ├── Meta descriptions
    └── Image optimizations
    ```

---

## REST API Connector

Connect to any REST API endpoint with flexible configuration options.

### Configuration Options

=== "Authentication Methods"
    ```yaml title="api_connector.yml"
    # API Key authentication
    api_key:
      type: "api_key"
      key: "your_api_key"
      header: "X-API-Key"
      
    # Bearer token
    bearer_token:
      type: "bearer"
      token: "your_bearer_token"
      
    # Basic authentication
    basic_auth:
      type: "basic"
      username: "your_username"
      password: "your_password"
      
    # OAuth 2.0
    oauth2:
      type: "oauth2"
      client_id: "your_client_id"
      client_secret: "your_client_secret"
      token_url: "https://api.example.com/oauth/token"
    ```

=== "Endpoint Configuration"
    ```yaml
    endpoints:
      products:
        url: "/products"
        method: "GET"
        pagination:
          type: "cursor"
          cursor_param: "next_cursor"
          limit_param: "limit"
          limit_value: 100
          
      single_product:
        url: "/products/{id}"
        method: "GET"
        parameters:
          include: "variants,images,metadata"
          
      create_product:
        url: "/products"
        method: "POST"
        headers:
          Content-Type: "application/json"
    ```

### Usage Examples

=== "Fetch Products"
    ```bash
    # Connect to API and fetch products
    python cli.py connect api \
        --endpoint https://api.example.com/products \
        --auth-type bearer \
        --token your_token \
        --batch-size 50
    ```

=== "Real-time Updates"
    ```python
    # Setup API polling for changes
    from connectors.api.rest_connector import RestAPIConnector
    
    connector = RestAPIConnector({
        'base_url': 'https://api.example.com',
        'auth': {'type': 'api_key', 'key': 'your_key'},
        'polling_interval': 300  # 5 minutes
    })
    
    connector.start_polling()
    ```

### Response Processing

Handle various API response formats:

=== "JSON Response Processing"
    ```json title="sample_api_response.json"
    {
      "data": [
        {
          "id": "prod_123",
          "attributes": {
            "name": "Sample Product",
            "description": "Product description",
            "price": 29.99,
            "brand": {
              "name": "Sample Brand"
            },
            "images": [
              {"url": "https://example.com/image1.jpg"},
              {"url": "https://example.com/image2.jpg"}
            ]
          }
        }
      ],
      "meta": {
        "total": 150,
        "page": 1,
        "per_page": 25
      }
    }
    ```

=== "Response Mapping"
    ```yaml title="response_mapping.yml"
    response_mapping:
      data_path: "data"
      fields:
        id: "id"
        title: "attributes.name"
        description: "attributes.description"
        price: "attributes.price"
        brand: "attributes.brand.name"
        images: "attributes.images[*].url"
        
      transformations:
        price:
          type: "float"
          default: 0.0
        images:
          type: "array"
          join_with: ","
    ```

---

## Webhook Connector

Handle real-time updates through webhook events for immediate data synchronization.

### Webhook Setup

=== "Endpoint Configuration"
    ```bash
    # Start webhook server
    python cli.py connect webhook --start-server --port 8080
    
    # Configure specific webhook
    python cli.py connect webhook --setup \
        --source shopify \
        --events product/create,product/update \
        --secret your_webhook_secret
    ```

=== "Webhook URLs"
    ```
    🔗 WEBHOOK ENDPOINTS
    
    General webhook:    /webhooks/generic
    Shopify webhooks:   /webhooks/shopify  
    Contentful:         /webhooks/contentful
    Custom webhooks:    /webhooks/custom/{source}
    
    Full URLs (if running on localhost:8080):
    https://yourserver.com:8080/webhooks/shopify
    ```

### Event Processing

Handle different types of webhook events:

=== "Shopify Webhooks"
    ```python title="webhook_handlers.py"
    from connectors.webhook.handlers import ShopifyWebhookHandler
    
    @webhook_handler('shopify')
    class ShopifyHandler(ShopifyWebhookHandler):
        
        def handle_product_create(self, payload):
            """Handle new product creation"""
            product_data = self.transform_shopify_product(payload)
            self.enqueue_generation(product_data)
            
        def handle_product_update(self, payload):
            """Handle product updates"""
            if self.should_regenerate(payload):
                product_data = self.transform_shopify_product(payload)
                self.enqueue_generation(product_data, priority='high')
                
        def handle_product_delete(self, payload):
            """Handle product deletion"""
            product_id = payload.get('id')
            self.cleanup_bundles(product_id)
    ```

=== "Generic Webhooks"
    ```python
    @webhook_handler('generic')
    class GenericWebhookHandler:
        
        def process_webhook(self, headers, payload):
            """Process any webhook format"""
            
            # Verify webhook signature
            if not self.verify_signature(headers, payload):
                raise WebhookVerificationError()
                
            # Extract event type
            event_type = self.extract_event_type(headers, payload)
            
            # Route to appropriate handler
            handler_method = f"handle_{event_type}"
            if hasattr(self, handler_method):
                getattr(self, handler_method)(payload)
            else:
                self.handle_unknown_event(event_type, payload)
    ```

### Security & Verification

Ensure webhook security with proper verification:

=== "Signature Verification"
    ```python
    import hmac
    import hashlib
    
    def verify_shopify_webhook(payload, signature, secret):
        """Verify Shopify webhook signature"""
        computed_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        expected_signature = f"sha256={computed_signature}"
        return hmac.compare_digest(expected_signature, signature)
    ```

=== "Rate Limiting"
    ```yaml title="webhook_config.yml"
    security:
      rate_limiting:
        enabled: true
        max_requests: 100
        window_seconds: 60
        
      ip_whitelist:
        - "23.227.38.0/24"  # Shopify
        - "192.30.252.0/22" # GitHub
        
      verification:
        require_signature: true
        allowed_sources: ["shopify", "contentful"]
        
      logging:
        log_all_webhooks: true
        log_failed_verification: true
    ```

---

## Connector Management

### Monitoring & Status

Track connector health and performance:

=== "Status Dashboard"
    ```
    📊 CONNECTOR STATUS
    
    Shopify CSV:      ✅ Ready (Last import: 2h ago)
    Generic CSV:      ✅ Ready  
    Contentful API:   🟡 Rate limited (Resume in 15m)
    Custom API:       ❌ Authentication failed
    Webhooks:         ✅ Active (3 events today)
    
    📈 Performance (24h):
    ├── Products imported: 1,247
    ├── Success rate: 97.3%
    ├── Avg import time: 1.8s/product
    └── Total data processed: 45.2MB
    ```

=== "Error Monitoring"
    ```
    🚨 CONNECTOR ALERTS
    
    ⚠️  High Error Rate: Custom API (15% failures)
    └── Cause: Timeout errors (>30s response)
    └── Recommendation: Increase timeout or reduce batch size
    
    ⚠️  Rate Limit Approaching: Contentful (85% of limit)
    └── Requests: 850/1000 per hour
    └── Recommendation: Reduce polling frequency
    
    ✅ All other connectors operating normally
    ```

### Troubleshooting

Common connector issues and solutions:

!!! bug "Troubleshooting Guide"

    === "Import Failures"
        **Problem**: CSV import fails with mapping errors
        
        **Solutions**:
        - Verify CSV encoding (UTF-8 recommended)
        - Check for special characters in headers
        - Validate data types match expected formats
        - Use `--analyze` flag to preview mapping

    === "API Connection Issues"
        **Problem**: API connector authentication fails
        
        **Solutions**:
        ```bash
        # Test API connection
        python cli.py connect api --test-connection \
            --endpoint https://api.example.com \
            --auth-type bearer --token your_token
            
        # Check API credentials
        python cli.py connect api --validate-auth
        ```

    === "Webhook Not Receiving Events"
        **Problem**: Webhook endpoint not receiving events
        
        **Solutions**:
        - Verify webhook URL is publicly accessible
        - Check firewall and port configuration
        - Validate webhook secret matches
        - Review webhook source configuration

---

Next: Explore the [API Reference](api-reference.md) for programmatic integration options.