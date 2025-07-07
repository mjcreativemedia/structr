# API Reference

Structr provides a comprehensive REST API for programmatic access to all platform features. The API is built with FastAPI and includes automatic OpenAPI documentation, authentication, and rate limiting.

## Base URL & Authentication

### API Base URL
```
Production:  https://api.structr.dev/v1
Development: http://localhost:8000/api
```

### Authentication

All API requests require authentication using API keys:

=== "Headers"
    ```http
    Authorization: Bearer your_api_key_here
    Content-Type: application/json
    ```

=== "cURL Example"
    ```bash
    curl -H "Authorization: Bearer sk_test_123..." \
         -H "Content-Type: application/json" \
         https://api.structr.dev/v1/health
    ```

=== "Python Example"
    ```python
    import requests
    
    headers = {
        'Authorization': 'Bearer sk_test_123...',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(
        'https://api.structr.dev/v1/health',
        headers=headers
    )
    ```

### API Key Management

Generate and manage API keys:

```bash
# Generate new API key
python cli.py api create-key --name "Production API" --permissions read,write

# List existing keys
python cli.py api list-keys

# Revoke API key
python cli.py api revoke-key sk_test_123...
```

---

## Connector Endpoints

Manage data import connectors and analyze external data sources.

### Analyze CSV Structure

Analyze CSV files for field mapping and data quality insights.

=== "Request"
    ```http
    POST /api/connectors/analyze
    Content-Type: multipart/form-data
    
    file: (binary CSV data)
    connector_type: shopify|generic
    ```

=== "cURL"
    ```bash
    curl -X POST \
      -H "Authorization: Bearer sk_test_123..." \
      -F "file=@products.csv" \
      -F "connector_type=shopify" \
      https://api.structr.dev/v1/connectors/analyze
    ```

=== "Python"
    ```python
    import requests
    
    with open('products.csv', 'rb') as f:
        files = {'file': f}
        data = {'connector_type': 'shopify'}
        
        response = requests.post(
            'https://api.structr.dev/v1/connectors/analyze',
            headers=headers,
            files=files,
            data=data
        )
    ```

=== "Response"
    ```json
    {
      "analysis_id": "analysis_20250706_123456",
      "file_info": {
        "filename": "products.csv",
        "size_mb": 2.4,
        "rows": 150,
        "columns": 12
      },
      "field_mapping": {
        "confidence": 0.96,
        "suggested_mappings": {
          "Handle": "id",
          "Title": "title",
          "Body (HTML)": "body_html",
          "Vendor": "vendor",
          "Variant Price": "price"
        }
      },
      "data_quality": {
        "overall_score": 88,
        "completeness": 94.5,
        "consistency": 82.1,
        "issues": [
          {
            "type": "missing_data",
            "field": "images", 
            "count": 16,
            "severity": "warning"
          }
        ]
      },
      "estimated_import_time": 45.2
    }
    ```

### Import Data

Import product data using a specific connector.

=== "Request"
    ```http
    POST /api/connectors/import
    Content-Type: multipart/form-data
    
    file: (binary CSV data)
    connector_type: shopify|generic|api
    batch_size: 25
    auto_fix: true
    field_mapping: {...}  # Optional custom mapping
    ```

=== "Python"
    ```python
    import requests
    import json
    
    # Custom field mapping
    field_mapping = {
        "product_name": "title",
        "description": "body_html",
        "retail_price": "price"
    }
    
    with open('products.csv', 'rb') as f:
        files = {'file': f}
        data = {
            'connector_type': 'generic',
            'batch_size': 50,
            'auto_fix': True,
            'field_mapping': json.dumps(field_mapping)
        }
        
        response = requests.post(
            'https://api.structr.dev/v1/connectors/import',
            headers=headers,
            files=files,
            data=data
        )
    ```

=== "Response"
    ```json
    {
      "import_id": "import_20250706_123456",
      "job_id": "job_abc123def456",
      "status": "queued",
      "estimated_completion": "2025-07-06T12:05:30Z",
      "products_to_import": 150,
      "batch_size": 25,
      "progress_url": "/api/batches/job_abc123def456"
    }
    ```

### Test Connection

Test API connector configurations.

=== "Request"
    ```http
    POST /api/connectors/test
    Content-Type: application/json
    
    {
      "connector_type": "api",
      "config": {
        "base_url": "https://api.example.com",
        "auth_type": "bearer",
        "auth_token": "your_token",
        "endpoint": "/products"
      }
    }
    ```

=== "Response"
    ```json
    {
      "connection_status": "success",
      "response_time_ms": 245,
      "api_version": "v2.1",
      "rate_limit": {
        "limit": 1000,
        "remaining": 987,
        "reset_at": "2025-07-06T13:00:00Z"
      },
      "sample_data": {
        "total_products": 1247,
        "sample_product": {
          "id": "prod_123",
          "name": "Sample Product"
        }
      }
    }
    ```

### Connector Status

Get status of all configured connectors.

=== "Request"
    ```http
    GET /api/connectors/status
    ```

=== "Response"
    ```json
    {
      "connectors": [
        {
          "type": "shopify_csv",
          "status": "ready",
          "last_import": "2025-07-06T10:30:00Z",
          "success_rate": 0.973,
          "total_imports": 1247
        },
        {
          "type": "contentful_api",
          "status": "rate_limited",
          "rate_limit_reset": "2025-07-06T12:45:00Z",
          "requests_remaining": 15
        }
      ],
      "overall_health": "good"
    }
    ```

---

## Batch Processing Endpoints

Manage bulk operations, job queues, and monitoring.

### Create Batch Generation Job

Generate PDPs for multiple products in parallel.

=== "Request"
    ```http
    POST /api/batches/generate
    Content-Type: application/json
    
    {
      "products": [
        {
          "handle": "summer-dress",
          "title": "Summer Blue Dress",
          "description": "Light and airy summer dress",
          "price": 89.99,
          "brand": "FashionCo"
        }
      ],
      "options": {
        "model": "mistral",
        "parallel_workers": 3,
        "template": "default",
        "auto_audit": true
      }
    }
    ```

=== "Python"
    ```python
    products = [
        {
            "handle": "product-1",
            "title": "Test Product 1",
            "description": "A great test product",
            "price": 29.99,
            "brand": "TestBrand"
        },
        {
            "handle": "product-2", 
            "title": "Test Product 2",
            "description": "Another test product",
            "price": 39.99,
            "brand": "TestBrand"
        }
    ]
    
    payload = {
        "products": products,
        "options": {
            "model": "mistral",
            "parallel_workers": 2,
            "auto_audit": True
        }
    }
    
    response = requests.post(
        'https://api.structr.dev/v1/batches/generate',
        headers=headers,
        json=payload
    )
    ```

=== "Response"
    ```json
    {
      "job_id": "batch_gen_20250706_123456",
      "status": "queued",
      "products_count": 2,
      "estimated_completion": "2025-07-06T12:08:30Z",
      "progress_url": "/api/batches/batch_gen_20250706_123456",
      "options": {
        "model": "mistral",
        "parallel_workers": 2,
        "template": "default"
      }
    }
    ```

### Create Batch Fix Job

Fix quality issues across multiple products.

=== "Request"
    ```http
    POST /api/batches/fix
    Content-Type: application/json
    
    {
      "product_ids": ["summer-dress", "winter-coat", "spring-shoes"],
      "options": {
        "target_issues": ["meta_description", "schema"],
        "min_score": 80,
        "dry_run": false,
        "backup": true
      }
    }
    ```

=== "Response"
    ```json
    {
      "job_id": "batch_fix_20250706_123457",
      "status": "queued",
      "products_count": 3,
      "issues_to_fix": ["meta_description", "schema"],
      "estimated_completion": "2025-07-06T12:03:15Z"
    }
    ```

### Get Job Status

Monitor the progress of batch operations.

=== "Request"
    ```http
    GET /api/batches/{job_id}
    ```

=== "Response"
    ```json
    {
      "job_id": "batch_gen_20250706_123456",
      "type": "batch_generation",
      "status": "in_progress",
      "progress": {
        "completed": 8,
        "total": 25,
        "percentage": 32.0,
        "estimated_remaining": "00:02:45"
      },
      "results": [
        {
          "product_id": "summer-dress",
          "status": "completed",
          "audit_score": 92,
          "issues": []
        },
        {
          "product_id": "winter-coat", 
          "status": "completed",
          "audit_score": 85,
          "issues": ["meta_description"]
        }
      ],
      "performance": {
        "start_time": "2025-07-06T12:00:00Z",
        "products_per_minute": 2.3,
        "success_rate": 0.96
      }
    }
    ```

### Cancel Job

Cancel a running batch operation.

=== "Request"
    ```http
    DELETE /api/batches/{job_id}
    ```

=== "Response"
    ```json
    {
      "job_id": "batch_gen_20250706_123456",
      "status": "cancelled",
      "products_completed": 8,
      "products_remaining": 17,
      "cancelled_at": "2025-07-06T12:05:30Z"
    }
    ```

### List Jobs

Get overview of all batch operations.

=== "Request"
    ```http
    GET /api/batches?status=all&limit=50&offset=0
    ```

=== "Response"
    ```json
    {
      "jobs": [
        {
          "job_id": "batch_gen_20250706_123456",
          "type": "batch_generation",
          "status": "completed",
          "created_at": "2025-07-06T12:00:00Z",
          "completed_at": "2025-07-06T12:08:30Z",
          "products_count": 25,
          "success_rate": 0.96
        }
      ],
      "pagination": {
        "total": 156,
        "limit": 50,
        "offset": 0,
        "has_more": true
      }
    }
    ```

---

## Monitoring & Health Endpoints

System health, metrics, and operational monitoring.

### Health Check

Basic system health and readiness check.

=== "Request"
    ```http
    GET /api/monitoring/health
    ```

=== "Response"
    ```json
    {
      "status": "healthy",
      "timestamp": "2025-07-06T12:00:00Z",
      "version": "1.0.0",
      "components": {
        "database": "healthy",
        "redis": "healthy", 
        "ollama": "healthy",
        "file_system": "healthy"
      },
      "uptime_seconds": 86400
    }
    ```

### System Metrics

Detailed performance and usage metrics.

=== "Request"
    ```http
    GET /api/monitoring/metrics?period=24h
    ```

=== "Response"
    ```json
    {
      "period": "24h",
      "generated_at": "2025-07-06T12:00:00Z",
      "performance": {
        "total_requests": 1247,
        "successful_requests": 1201,
        "error_rate": 0.037,
        "avg_response_time_ms": 245,
        "p95_response_time_ms": 890
      },
      "processing": {
        "products_generated": 156,
        "products_audited": 203,
        "products_fixed": 45,
        "avg_generation_time_s": 2.3,
        "success_rate": 0.965
      },
      "resources": {
        "cpu_usage_percent": 45.2,
        "memory_usage_mb": 1247,
        "disk_usage_gb": 15.6,
        "active_workers": 3
      },
      "queue": {
        "pending_jobs": 5,
        "active_jobs": 2,
        "completed_jobs_24h": 23,
        "failed_jobs_24h": 1
      }
    }
    ```

### Job Queue Overview

Current job queue status and statistics.

=== "Request"
    ```http
    GET /api/monitoring/jobs
    ```

=== "Response"
    ```json
    {
      "queue_status": {
        "pending": 5,
        "running": 2,
        "completed_today": 23,
        "failed_today": 1
      },
      "active_jobs": [
        {
          "job_id": "batch_gen_20250706_123456",
          "type": "batch_generation",
          "progress": 0.32,
          "eta_seconds": 165
        }
      ],
      "worker_status": {
        "total_workers": 4,
        "active_workers": 2,
        "idle_workers": 2
      },
      "performance": {
        "avg_job_duration_s": 127,
        "jobs_per_hour": 18.5,
        "success_rate_24h": 0.956
      }
    }
    ```

### System Alerts

Current system alerts and warnings.

=== "Request"
    ```http
    GET /api/monitoring/alerts?severity=warning,error
    ```

=== "Response"
    ```json
    {
      "alerts": [
        {
          "id": "alert_001",
          "severity": "warning",
          "type": "high_error_rate",
          "message": "Error rate above 5% threshold",
          "details": {
            "current_rate": 0.087,
            "threshold": 0.05,
            "affected_endpoint": "/api/connectors/import"
          },
          "created_at": "2025-07-06T11:45:00Z",
          "acknowledged": false
        }
      ],
      "summary": {
        "critical": 0,
        "warning": 1,
        "info": 3
      }
    }
    ```

---

## Webhook Endpoints

Handle real-time updates from external systems.

### Shopify Webhooks

Receive product updates from Shopify.

=== "Shopify Product Created"
    ```http
    POST /api/webhooks/shopify
    Content-Type: application/json
    X-Shopify-Topic: products/create
    X-Shopify-Hmac-Sha256: signature
    
    {
      "id": 123456789,
      "title": "New Product",
      "handle": "new-product",
      "body_html": "<p>Product description</p>",
      "vendor": "Brand Name",
      "product_type": "Apparel",
      "tags": "new, featured",
      "variants": [...]
    }
    ```

=== "Response"
    ```json
    {
      "status": "accepted",
      "job_id": "webhook_gen_20250706_123456",
      "message": "Product queued for PDP generation",
      "estimated_completion": "2025-07-06T12:02:30Z"
    }
    ```

### Contentful Webhooks

Handle content updates from Contentful CMS.

=== "Request"
    ```http
    POST /api/webhooks/contentful
    Content-Type: application/json
    X-Contentful-Topic: ContentManagement.Entry.publish
    
    {
      "sys": {
        "type": "Entry",
        "id": "entry_123",
        "contentType": {
          "sys": {"id": "product"}
        }
      },
      "fields": {
        "name": {"en-US": "Updated Product Name"},
        "description": {"en-US": "Updated description"},
        "price": {"en-US": 49.99}
      }
    }
    ```

### Generic Webhooks

Handle webhooks from any source.

=== "Request"
    ```http
    POST /api/webhooks/generic/{source}
    Content-Type: application/json
    X-Webhook-Source: your-system
    X-Webhook-Event: product.updated
    
    {
      "event": "product.updated",
      "data": {
        "product_id": "prod_123",
        "changes": ["title", "price"],
        "updated_at": "2025-07-06T12:00:00Z"
      }
    }
    ```

=== "Response"
    ```json
    {
      "status": "processed",
      "webhook_id": "webhook_20250706_123456", 
      "actions_taken": [
        "regenerated_pdp",
        "updated_metadata"
      ],
      "job_ids": ["regen_20250706_123456"]
    }
    ```

---

## Error Handling

### HTTP Status Codes

Standard HTTP status codes are used throughout the API:

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `201` | Created | Resource created successfully |
| `400` | Bad Request | Invalid request parameters |
| `401` | Unauthorized | Invalid or missing API key |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource not found |
| `422` | Unprocessable Entity | Validation error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |

### Error Response Format

All errors follow a consistent format:

=== "Validation Error"
    ```json
    {
      "error": {
        "type": "validation_error",
        "message": "Invalid request parameters",
        "details": [
          {
            "field": "products[0].price",
            "message": "Price must be a positive number",
            "code": "invalid_price"
          }
        ],
        "request_id": "req_20250706_123456"
      }
    }
    ```

=== "Authentication Error"
    ```json
    {
      "error": {
        "type": "authentication_error",
        "message": "Invalid API key",
        "code": "invalid_api_key",
        "request_id": "req_20250706_123456"
      }
    }
    ```

=== "Rate Limit Error"
    ```json
    {
      "error": {
        "type": "rate_limit_error",
        "message": "Too many requests",
        "retry_after": 60,
        "limit": 1000,
        "remaining": 0,
        "reset_at": "2025-07-06T13:00:00Z",
        "request_id": "req_20250706_123456"
      }
    }
    ```

---

## Rate Limiting

### Rate Limit Headers

All responses include rate limiting information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1625572800
X-RateLimit-Window: 3600
```

### Rate Limit Tiers

Different endpoints have different rate limits:

| Endpoint Category | Requests/Hour | Burst Limit |
|-------------------|---------------|-------------|
| Health & Status | 10,000 | 100/minute |
| Data Analysis | 1,000 | 20/minute |
| Batch Operations | 100 | 5/minute |
| Webhook Delivery | 5,000 | 50/minute |

### Handling Rate Limits

=== "Python with Backoff"
    ```python
    import requests
    import time
    
    def api_request_with_retry(url, headers, data=None, max_retries=3):
        for attempt in range(max_retries):
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
                
            return response
        
        raise Exception("Max retries exceeded")
    ```

---

## SDKs & Libraries

### Official Python SDK

```bash
pip install structr-python
```

```python
from structr import StructrClient

client = StructrClient(api_key="sk_test_123...")

# Analyze CSV
analysis = client.connectors.analyze_csv("products.csv", "shopify")

# Start batch generation
job = client.batches.generate(products, model="mistral", workers=3)

# Monitor progress
while job.status != "completed":
    time.sleep(5)
    job.refresh()
    print(f"Progress: {job.progress}%")
```

### JavaScript/Node.js SDK

```bash
npm install @structr/api
```

```javascript
import { StructrAPI } from '@structr/api';

const structr = new StructrAPI({
  apiKey: 'sk_test_123...'
});

// Analyze CSV
const analysis = await structr.connectors.analyzeCSV({
  file: csvBuffer,
  connectorType: 'shopify'
});

// Start batch job
const job = await structr.batches.generate({
  products: products,
  options: { model: 'mistral', workers: 3 }
});

// Monitor with WebSocket
job.onProgress(progress => {
  console.log(`Progress: ${progress.percentage}%`);
});
```

---

## OpenAPI Documentation

### Interactive Documentation

Access live API documentation at:

- **Swagger UI**: `/docs` 
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

### Schema Download

Download the complete OpenAPI schema:

```bash
curl https://api.structr.dev/v1/openapi.json > structr-openapi.json
```

Generate client libraries:

```bash
# Generate Python client
openapi-generator generate -i structr-openapi.json -g python -o structr-python-client

# Generate JavaScript client  
openapi-generator generate -i structr-openapi.json -g javascript -o structr-js-client
```

---

Next: Explore the [Developer Guide](developer-guide.md) for contributing and extending Structr.