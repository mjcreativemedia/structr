"""
Connectors API Endpoints

REST endpoints for managing data connectors and imports.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json
import tempfile
import time

from connectors import ShopifyCSVImporter, PIMConnector, GenericCSVMapper
from connectors.base import ConnectorConfig, ImportResult, ExportResult
from models.pdp import ProductData
from batch.processors.batch_manager import BatchManager
from api.auth import APIKeyAuth

router = APIRouter()

# Initialize batch manager
batch_manager = BatchManager()


# Pydantic models for API
class ConnectorConfigModel(BaseModel):
    name: str
    source_type: str = Field(..., description="Type of source: csv, api, webhook, file")
    credentials: Dict[str, Any] = Field(default_factory=dict)
    field_mapping: Dict[str, str] = Field(default_factory=dict)
    batch_size: int = Field(default=100, ge=1, le=10000)
    timeout: int = Field(default=30, ge=1, le=300)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    filters: Dict[str, Any] = Field(default_factory=dict)


class ImportRequest(BaseModel):
    connector_config: ConnectorConfigModel
    source_data: Optional[Dict[str, Any]] = None
    generate_pdps: bool = Field(default=True, description="Generate PDPs after import")
    priority: int = Field(default=0, description="Job priority (higher = more priority)")


class CSVAnalysisRequest(BaseModel):
    connector_type: str = Field(default="generic", description="Connector type: shopify, generic")
    sample_size: int = Field(default=1000, ge=10, le=10000)


class FieldMappingRequest(BaseModel):
    connector_type: str
    custom_mapping: Dict[str, str]


class ExportRequest(BaseModel):
    product_ids: List[str]
    connector_config: ConnectorConfigModel
    destination: str
    format: str = Field(default="csv", description="Export format")


@router.get("/", summary="List available connectors")
async def list_connectors():
    """List all available connector types and their capabilities"""
    return {
        "connectors": [
            {
                "name": "shopify_csv",
                "description": "Shopify CSV import/export with automatic field mapping",
                "source_types": ["csv"],
                "features": ["auto_mapping", "variant_support", "bulk_operations"],
                "required_fields": ["Handle", "Title"],
                "example_config": {
                    "name": "my_shopify_import",
                    "source_type": "csv",
                    "batch_size": 500
                }
            },
            {
                "name": "pim_connector", 
                "description": "Generic PIM system connector for REST APIs",
                "source_types": ["api", "webhook", "file"],
                "features": ["rest_api", "pagination", "authentication", "webhooks"],
                "required_fields": ["base_url"],
                "example_config": {
                    "name": "contentful_import",
                    "source_type": "api",
                    "credentials": {
                        "base_url": "https://api.contentful.com",
                        "api_key": "your-api-key"
                    }
                }
            },
            {
                "name": "generic_csv",
                "description": "Intelligent CSV mapper for any product catalog format",
                "source_types": ["csv"],
                "features": ["intelligent_mapping", "data_quality_analysis", "custom_validation"],
                "required_fields": [],
                "example_config": {
                    "name": "custom_catalog_import",
                    "source_type": "csv",
                    "batch_size": 1000
                }
            }
        ]
    }


@router.post("/shopify/analyze", summary="Analyze Shopify CSV structure")
async def analyze_shopify_csv(
    file: UploadFile = File(..., description="CSV file to analyze"),
    request: CSVAnalysisRequest = Depends()
):
    """
    Analyze CSV file structure and suggest field mappings.
    Supports both Shopify exports and custom CSV formats.
    """
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)
        
        # Initialize appropriate connector
        if request.connector_type == "shopify":
            connector = ShopifyCSVImporter()
            analysis = connector.detect_csv_structure(tmp_path)
            # Add Shopify-specific validation
            validation = connector.validate_csv_format(tmp_path)
            analysis['shopify_validation'] = validation
        else:
            connector = GenericCSVMapper()
            analysis = connector.analyze_csv_structure(tmp_path, request.sample_size)
        
        # Cleanup temp file
        tmp_path.unlink()
        
        return {
            "analysis": analysis,
            "connector_type": request.connector_type,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/csv/validate-mapping", summary="Validate custom field mapping")
async def validate_field_mapping(
    file: UploadFile = File(..., description="CSV file to validate mapping against"),
    request: FieldMappingRequest = Depends()
):
    """Validate custom field mapping against CSV structure"""
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)
        
        # Initialize connector and validate mapping
        if request.connector_type == "generic":
            connector = GenericCSVMapper()
            validation_result = connector.create_custom_mapping(tmp_path, request.custom_mapping)
        else:
            raise HTTPException(status_code=400, detail=f"Mapping validation not supported for {request.connector_type}")
        
        # Cleanup temp file
        tmp_path.unlink()
        
        return validation_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mapping validation failed: {str(e)}")


@router.post("/import", summary="Import products from data source")
async def import_products(
    background_tasks: BackgroundTasks,
    request: ImportRequest,
    file: Optional[UploadFile] = File(None, description="CSV file to import (for file-based connectors)")
):
    """
    Import products from various data sources.
    Supports CSV files, API endpoints, and webhook data.
    """
    
    try:
        # Create connector based on config
        connector_config = ConnectorConfig(**request.connector_config.dict())
        
        if request.connector_config.source_type == "csv":
            if not file:
                raise HTTPException(status_code=400, detail="CSV file required for file-based import")
            
            # Save uploaded file
            upload_dir = Path("output/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / f"{int(time.time())}_{file.filename}"
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Determine connector type
            if "shopify" in request.connector_config.name.lower():
                connector = ShopifyCSVImporter(connector_config)
            else:
                connector = GenericCSVMapper(connector_config)
            
            source = str(file_path)
            
        elif request.connector_config.source_type == "api":
            connector = PIMConnector(connector_config)
            source = request.source_data.get('endpoint', '/products') if request.source_data else '/products'
            
        elif request.connector_config.source_type == "webhook":
            connector = PIMConnector(connector_config)
            source = request.source_data or {}
            
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported source type: {request.connector_config.source_type}"
            )
        
        # Submit import and generation job
        if request.generate_pdps:
            batch_id = batch_manager.import_and_generate(
                connector=connector,
                source=source,
                priority=request.priority
            )
            
            return {
                "success": True,
                "batch_id": batch_id,
                "message": "Import and generation job submitted",
                "generate_pdps": True,
                "status_url": f"/api/v1/batches/{batch_id}/status"
            }
        else:
            # Direct import only
            import_result = connector.import_data(source)
            
            return {
                "success": import_result.success,
                "imported_count": import_result.processed_records,
                "failed_count": import_result.failed_records,
                "errors": import_result.errors[:10],  # Limit errors
                "warnings": import_result.warnings[:10],
                "processing_time": import_result.processing_time,
                "generate_pdps": False
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/export", summary="Export products using connector")
async def export_products(
    background_tasks: BackgroundTasks,
    request: ExportRequest
):
    """Export products to external system using connector"""
    
    try:
        # Create connector
        connector_config = ConnectorConfig(**request.connector_config.dict())
        
        if request.connector_config.source_type == "csv":
            if "shopify" in request.connector_config.name.lower():
                connector = ShopifyCSVImporter(connector_config)
            else:
                connector = GenericCSVMapper(connector_config)
        elif request.connector_config.source_type in ["api", "file"]:
            connector = PIMConnector(connector_config)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Export not supported for source type: {request.connector_config.source_type}"
            )
        
        # Submit export job
        batch_id = batch_manager.export_batch(
            product_ids=request.product_ids,
            connector=connector,
            destination=request.destination
        )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "message": "Export job submitted",
            "product_count": len(request.product_ids),
            "destination": request.destination,
            "status_url": f"/api/v1/batches/{batch_id}/status"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/pim/test-connection", summary="Test PIM system connection")
async def test_pim_connection(
    base_url: str,
    api_key: Optional[str] = None,
    headers: Optional[str] = None
):
    """Test connection to PIM system or API endpoint"""
    
    try:
        # Create test connector
        credentials = {"base_url": base_url}
        if api_key:
            credentials["api_key"] = api_key
        if headers:
            try:
                credentials["headers"] = json.loads(headers)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid headers JSON")
        
        config = ConnectorConfig(
            name="test_connection",
            source_type="api",
            credentials=credentials
        )
        
        connector = PIMConnector(config)
        
        # Test connection
        is_connected = connector.test_connection()
        
        # Try to get available fields if connected
        available_fields = []
        if is_connected:
            try:
                available_fields = connector.get_available_fields()
            except:
                pass  # Field discovery is optional
        
        return {
            "connected": is_connected,
            "base_url": base_url,
            "available_fields": available_fields,
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "timestamp": time.time()
        }


@router.post("/pim/webhook", summary="Register webhook handler")
async def register_webhook(
    base_url: str,
    api_key: str,
    callback_url: str
):
    """Register webhook handler with PIM system"""
    
    try:
        config = ConnectorConfig(
            name="webhook_registration",
            source_type="api",
            credentials={
                "base_url": base_url,
                "api_key": api_key
            }
        )
        
        connector = PIMConnector(config)
        result = connector.create_webhook_handler(callback_url)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook registration failed: {str(e)}")


@router.get("/field-mappings", summary="Get standard field mappings")
async def get_field_mappings(connector_type: str = "generic"):
    """Get standard field mappings for connector type"""
    
    try:
        if connector_type == "shopify":
            connector = ShopifyCSVImporter()
            mappings = connector._default_field_mapping()
            available_fields = connector.get_available_fields()
        elif connector_type == "generic":
            connector = GenericCSVMapper()
            mappings = connector._default_field_mapping()
            available_fields = list(mappings.keys())
        elif connector_type == "pim":
            connector = PIMConnector(ConnectorConfig(name="test", source_type="api"))
            mappings = connector._default_field_mapping()
            available_fields = list(mappings.keys())
        else:
            raise HTTPException(status_code=400, detail=f"Unknown connector type: {connector_type}")
        
        return {
            "connector_type": connector_type,
            "default_mappings": mappings,
            "available_source_fields": available_fields,
            "structr_fields": list(set(mappings.values())),
            "mapping_info": {
                "source_field": "Field name in source data",
                "structr_field": "Standardized field name in Structr",
                "description": "Field mappings convert source data to Structr's standard format"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get field mappings: {str(e)}")


@router.get("/examples", summary="Get configuration examples")
async def get_configuration_examples():
    """Get example configurations for different connector types"""
    
    return {
        "shopify_csv": {
            "description": "Standard Shopify product export",
            "config": {
                "name": "shopify_products",
                "source_type": "csv",
                "batch_size": 500,
                "field_mapping": {
                    "Handle": "id",
                    "Title": "title",
                    "Body (HTML)": "body_html",
                    "Vendor": "vendor",
                    "Type": "product_type",
                    "Variant Price": "price"
                }
            },
            "usage": "Upload Shopify product export CSV file"
        },
        "contentful_api": {
            "description": "Contentful CMS product import",
            "config": {
                "name": "contentful_products",
                "source_type": "api",
                "credentials": {
                    "base_url": "https://api.contentful.com/spaces/YOUR_SPACE_ID",
                    "api_key": "YOUR_ACCESS_TOKEN"
                },
                "field_mapping": {
                    "sys.id": "id",
                    "fields.title": "title",
                    "fields.description": "body_html",
                    "fields.price": "price"
                }
            },
            "usage": "Connect to Contentful API endpoint"
        },
        "generic_csv": {
            "description": "Any custom CSV product catalog",
            "config": {
                "name": "custom_catalog",
                "source_type": "csv",
                "batch_size": 1000,
                "field_mapping": {
                    "product_id": "id",
                    "product_name": "title",
                    "description": "body_html",
                    "brand": "vendor",
                    "category": "product_type",
                    "price": "price"
                }
            },
            "usage": "Upload custom CSV with manual field mapping"
        },
        "webhook": {
            "description": "Real-time webhook data processing",
            "config": {
                "name": "product_webhook",
                "source_type": "webhook",
                "credentials": {
                    "webhook_secret": "your-secret-key"
                },
                "field_mapping": {
                    "id": "id",
                    "name": "title",
                    "description": "body_html"
                }
            },
            "usage": "Receive product data via webhook POST"
        }
    }