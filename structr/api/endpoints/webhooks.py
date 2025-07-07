"""
Webhooks API Endpoints

REST endpoints for webhook integration and real-time data processing.
"""

from fastapi import APIRouter, HTTPException, Request, Header, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import time
import hashlib
import hmac
from datetime import datetime

from connectors.pim.connector import PIMConnector
from connectors.base import ConnectorConfig
from batch.processors.batch_manager import BatchManager
from models.pdp import ProductData

router = APIRouter()

# Initialize batch manager
batch_manager = BatchManager()

# Webhook event storage (in production, use a database)
webhook_events: List[Dict[str, Any]] = []
MAX_EVENTS = 1000


# Pydantic models
class WebhookConfig(BaseModel):
    name: str
    events: List[str] = Field(..., description="Events to listen for: product.created, product.updated, product.deleted")
    secret: Optional[str] = Field(None, description="Webhook secret for signature validation")
    field_mapping: Dict[str, str] = Field(default_factory=dict)
    auto_generate: bool = Field(default=True, description="Automatically generate PDPs for new/updated products")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filters for processing only specific products")


class WebhookEvent(BaseModel):
    event_type: str
    data: Dict[str, Any]
    source: Optional[str] = None
    timestamp: Optional[float] = None


class ShopifyWebhookEvent(BaseModel):
    """Shopify-specific webhook event structure"""
    id: int
    title: str
    body_html: Optional[str] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    created_at: str
    updated_at: str
    published_at: Optional[str] = None
    tags: Optional[str] = None
    status: str = "active"
    variants: List[Dict[str, Any]] = Field(default_factory=list)
    images: List[Dict[str, Any]] = Field(default_factory=list)


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature using HMAC"""
    if not secret or not signature:
        return True  # Skip verification if no secret configured
    
    try:
        # Handle different signature formats
        if signature.startswith('sha256='):
            expected_signature = 'sha256=' + hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
        elif signature.startswith('sha1='):
            expected_signature = 'sha1=' + hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha1
            ).hexdigest()
        else:
            # Try raw HMAC
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception:
        return False


def store_webhook_event(event_type: str, data: Dict[str, Any], source: str = "unknown") -> str:
    """Store webhook event for processing and audit"""
    event_id = f"webhook_{int(time.time())}_{len(webhook_events)}"
    
    event = {
        "id": event_id,
        "event_type": event_type,
        "data": data,
        "source": source,
        "timestamp": time.time(),
        "processed": False,
        "processing_result": None
    }
    
    webhook_events.append(event)
    
    # Limit stored events
    if len(webhook_events) > MAX_EVENTS:
        webhook_events.pop(0)
    
    return event_id


@router.get("/", summary="List webhook configurations")
async def list_webhook_configs():
    """List available webhook configurations and supported events"""
    
    return {
        "supported_sources": [
            {
                "name": "shopify",
                "description": "Shopify store webhooks",
                "events": ["products/create", "products/update", "products/delete"],
                "signature_header": "X-Shopify-Hmac-Sha256",
                "example_url": "/api/v1/webhooks/shopify/products"
            },
            {
                "name": "contentful",
                "description": "Contentful CMS webhooks", 
                "events": ["ContentManagement.Entry.publish", "ContentManagement.Entry.unpublish"],
                "signature_header": "X-Contentful-Webhook-Signature",
                "example_url": "/api/v1/webhooks/contentful/entries"
            },
            {
                "name": "generic",
                "description": "Generic webhook handler",
                "events": ["product.created", "product.updated", "product.deleted"],
                "signature_header": "X-Webhook-Signature",
                "example_url": "/api/v1/webhooks/generic"
            }
        ],
        "event_types": {
            "product.created": "New product created",
            "product.updated": "Existing product modified", 
            "product.deleted": "Product removed",
            "bulk.import": "Bulk import completed",
            "audit.completed": "Audit process finished"
        }
    }


@router.post("/shopify/products", summary="Shopify product webhook")
async def shopify_product_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_shopify_hmac_sha256: Optional[str] = Header(None),
    x_shopify_shop_domain: Optional[str] = Header(None),
    x_shopify_topic: Optional[str] = Header(None)
):
    """
    Handle Shopify product webhooks.
    Supports: products/create, products/update, products/delete
    """
    
    try:
        # Get raw payload
        body = await request.body()
        
        # Verify signature if configured
        webhook_secret = request.app.state.config.get('webhook_secret')
        if webhook_secret and x_shopify_hmac_sha256:
            if not verify_webhook_signature(body, x_shopify_hmac_sha256, webhook_secret):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse payload
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Store event
        event_id = store_webhook_event(
            event_type=x_shopify_topic or "products/unknown",
            data=payload,
            source=f"shopify:{x_shopify_shop_domain or 'unknown'}"
        )
        
        # Process based on event type
        if x_shopify_topic in ["products/create", "products/update"]:
            # Convert Shopify product to ProductData
            try:
                product_data = convert_shopify_product(payload)
                
                # Submit generation job
                batch_id = batch_manager.generate_batch(
                    products=[product_data],
                    priority=1  # High priority for real-time webhooks
                )
                
                # Update event with processing result
                for event in webhook_events:
                    if event["id"] == event_id:
                        event["processed"] = True
                        event["processing_result"] = {
                            "success": True,
                            "batch_id": batch_id,
                            "action": "generate_pdp"
                        }
                        break
                
                return {
                    "success": True,
                    "event_id": event_id,
                    "event_type": x_shopify_topic,
                    "product_id": payload.get("id"),
                    "batch_id": batch_id,
                    "message": "Product processing started"
                }
                
            except Exception as e:
                # Update event with error
                for event in webhook_events:
                    if event["id"] == event_id:
                        event["processed"] = True
                        event["processing_result"] = {
                            "success": False,
                            "error": str(e)
                        }
                        break
                
                raise HTTPException(status_code=500, detail=f"Product processing failed: {str(e)}")
        
        elif x_shopify_topic == "products/delete":
            # Handle product deletion
            product_id = str(payload.get("id", ""))
            
            # Mark event as processed
            for event in webhook_events:
                if event["id"] == event_id:
                    event["processed"] = True
                    event["processing_result"] = {
                        "success": True,
                        "action": "delete_acknowledged",
                        "product_id": product_id
                    }
                    break
            
            return {
                "success": True,
                "event_id": event_id,
                "event_type": x_shopify_topic,
                "product_id": product_id,
                "message": "Product deletion acknowledged"
            }
        
        else:
            return {
                "success": True,
                "event_id": event_id,
                "message": f"Event {x_shopify_topic} received but not processed"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.post("/contentful/entries", summary="Contentful entry webhook")
async def contentful_entry_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_contentful_webhook_signature: Optional[str] = Header(None),
    x_contentful_topic: Optional[str] = Header(None)
):
    """
    Handle Contentful entry webhooks.
    Supports: ContentManagement.Entry.publish, ContentManagement.Entry.unpublish
    """
    
    try:
        # Get raw payload
        body = await request.body()
        
        # Verify signature if configured
        webhook_secret = request.app.state.config.get('webhook_secret')
        if webhook_secret and x_contentful_webhook_signature:
            if not verify_webhook_signature(body, x_contentful_webhook_signature, webhook_secret):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse payload
        payload = json.loads(body.decode('utf-8'))
        
        # Store event
        event_id = store_webhook_event(
            event_type=x_contentful_topic or "entry.unknown",
            data=payload,
            source="contentful"
        )
        
        # Check if this is a product entry
        content_type = payload.get("sys", {}).get("contentType", {}).get("sys", {}).get("id")
        
        if content_type == "product":  # Adjust based on your Contentful content type
            try:
                product_data = convert_contentful_entry(payload)
                
                if x_contentful_topic == "ContentManagement.Entry.publish":
                    # Generate PDP for published product
                    batch_id = batch_manager.generate_batch(
                        products=[product_data],
                        priority=1
                    )
                    
                    # Update event
                    for event in webhook_events:
                        if event["id"] == event_id:
                            event["processed"] = True
                            event["processing_result"] = {
                                "success": True,
                                "batch_id": batch_id,
                                "action": "generate_pdp"
                            }
                            break
                    
                    return {
                        "success": True,
                        "event_id": event_id,
                        "event_type": x_contentful_topic,
                        "entry_id": payload.get("sys", {}).get("id"),
                        "batch_id": batch_id,
                        "message": "Product PDP generation started"
                    }
                
                else:
                    # Handle unpublish or other events
                    return {
                        "success": True,
                        "event_id": event_id,
                        "event_type": x_contentful_topic,
                        "message": "Entry event acknowledged"
                    }
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Contentful entry processing failed: {str(e)}")
        
        else:
            return {
                "success": True,
                "event_id": event_id,
                "message": f"Non-product entry ignored: {content_type}"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Contentful webhook processing failed: {str(e)}")


@router.post("/generic", summary="Generic webhook handler")
async def generic_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    event: WebhookEvent,
    x_webhook_signature: Optional[str] = Header(None),
    x_webhook_source: Optional[str] = Header(None)
):
    """
    Generic webhook handler for custom integrations.
    Accepts standardized webhook events.
    """
    
    try:
        # Get raw payload for signature verification
        body = await request.body()
        
        # Verify signature if configured
        webhook_secret = request.app.state.config.get('webhook_secret')
        if webhook_secret and x_webhook_signature:
            if not verify_webhook_signature(body, x_webhook_signature, webhook_secret):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Store event
        event_id = store_webhook_event(
            event_type=event.event_type,
            data=event.data,
            source=x_webhook_source or event.source or "generic"
        )
        
        # Process based on event type
        if event.event_type in ["product.created", "product.updated"]:
            try:
                # Try to convert generic data to ProductData
                product_data = ProductData(**event.data)
                
                # Generate PDP
                batch_id = batch_manager.generate_batch(
                    products=[product_data],
                    priority=1
                )
                
                # Update event
                for stored_event in webhook_events:
                    if stored_event["id"] == event_id:
                        stored_event["processed"] = True
                        stored_event["processing_result"] = {
                            "success": True,
                            "batch_id": batch_id,
                            "action": "generate_pdp"
                        }
                        break
                
                return {
                    "success": True,
                    "event_id": event_id,
                    "event_type": event.event_type,
                    "batch_id": batch_id,
                    "message": "Product processing started"
                }
                
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid product data: {str(e)}")
        
        elif event.event_type == "product.deleted":
            return {
                "success": True,
                "event_id": event_id,
                "event_type": event.event_type,
                "message": "Product deletion acknowledged"
            }
        
        else:
            return {
                "success": True,
                "event_id": event_id,
                "message": f"Event {event.event_type} received but not processed"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generic webhook processing failed: {str(e)}")


@router.get("/events", summary="List recent webhook events")
async def list_webhook_events(
    limit: int = 50,
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    processed: Optional[bool] = None
):
    """List recent webhook events with optional filtering"""
    
    try:
        filtered_events = webhook_events.copy()
        
        # Apply filters
        if source:
            filtered_events = [e for e in filtered_events if source in e.get("source", "")]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.get("event_type") == event_type]
        
        if processed is not None:
            filtered_events = [e for e in filtered_events if e.get("processed") == processed]
        
        # Sort by timestamp (newest first) and limit
        filtered_events.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        filtered_events = filtered_events[:limit]
        
        return {
            "events": filtered_events,
            "total_count": len(webhook_events),
            "filtered_count": len(filtered_events),
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list webhook events: {str(e)}")


@router.get("/events/{event_id}", summary="Get webhook event details")
async def get_webhook_event(event_id: str):
    """Get details for specific webhook event"""
    
    try:
        event = next((e for e in webhook_events if e["id"] == event_id), None)
        
        if not event:
            raise HTTPException(status_code=404, detail=f"Webhook event {event_id} not found")
        
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get webhook event: {str(e)}")


@router.post("/events/{event_id}/replay", summary="Replay webhook event")
async def replay_webhook_event(
    event_id: str,
    background_tasks: BackgroundTasks
):
    """Replay a stored webhook event for reprocessing"""
    
    try:
        event = next((e for e in webhook_events if e["id"] == event_id), None)
        
        if not event:
            raise HTTPException(status_code=404, detail=f"Webhook event {event_id} not found")
        
        # Create new event ID for replay
        replay_event_id = f"replay_{event_id}_{int(time.time())}"
        
        # Store replay event
        replay_event = {
            "id": replay_event_id,
            "event_type": event["event_type"],
            "data": event["data"],
            "source": f"replay:{event['source']}",
            "timestamp": time.time(),
            "processed": False,
            "processing_result": None,
            "original_event_id": event_id
        }
        
        webhook_events.append(replay_event)
        
        # Process based on event type
        if event["event_type"] in ["product.created", "product.updated", "products/create", "products/update"]:
            try:
                # Convert data to ProductData
                if "shopify" in event["source"]:
                    product_data = convert_shopify_product(event["data"])
                else:
                    product_data = ProductData(**event["data"])
                
                # Generate PDP
                batch_id = batch_manager.generate_batch(
                    products=[product_data],
                    priority=1
                )
                
                # Update replay event
                replay_event["processed"] = True
                replay_event["processing_result"] = {
                    "success": True,
                    "batch_id": batch_id,
                    "action": "generate_pdp"
                }
                
                return {
                    "success": True,
                    "replay_event_id": replay_event_id,
                    "original_event_id": event_id,
                    "batch_id": batch_id,
                    "message": "Event replayed successfully"
                }
                
            except Exception as e:
                replay_event["processed"] = True
                replay_event["processing_result"] = {
                    "success": False,
                    "error": str(e)
                }
                raise HTTPException(status_code=500, detail=f"Replay processing failed: {str(e)}")
        
        else:
            return {
                "success": True,
                "replay_event_id": replay_event_id,
                "message": f"Event {event['event_type']} replayed but not processed"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to replay webhook event: {str(e)}")


def convert_shopify_product(shopify_data: Dict[str, Any]) -> ProductData:
    """Convert Shopify webhook product data to ProductData"""
    
    # Extract images
    images = []
    for img in shopify_data.get("images", []):
        if img.get("src"):
            images.append(img["src"])
    
    # Extract variants
    variants = []
    for variant in shopify_data.get("variants", []):
        variants.append({
            "sku": variant.get("sku", ""),
            "price": float(variant.get("price", 0)),
            "inventory_quantity": variant.get("inventory_quantity", 0),
            "barcode": variant.get("barcode", ""),
            "weight": float(variant.get("grams", 0)) / 1000 if variant.get("grams") else 0  # Convert grams to kg
        })
    
    # Get main variant (first one) for main product fields
    main_variant = variants[0] if variants else {}
    
    return ProductData(
        id=str(shopify_data["id"]),
        title=shopify_data.get("title", ""),
        body_html=shopify_data.get("body_html", ""),
        vendor=shopify_data.get("vendor", ""),
        product_type=shopify_data.get("product_type", ""),
        price=main_variant.get("price", 0),
        sku=main_variant.get("sku", ""),
        barcode=main_variant.get("barcode", ""),
        weight=main_variant.get("weight", 0),
        inventory_quantity=main_variant.get("inventory_quantity", 0),
        tags=shopify_data.get("tags", "").split(", ") if shopify_data.get("tags") else [],
        images=images,
        variants=variants,
        status=shopify_data.get("status", "active"),
        published=shopify_data.get("published_at") is not None
    )


def convert_contentful_entry(contentful_data: Dict[str, Any]) -> ProductData:
    """Convert Contentful entry data to ProductData"""
    
    fields = contentful_data.get("fields", {})
    
    # Extract images from Contentful assets
    images = []
    if "images" in fields:
        for img in fields["images"]:
            if isinstance(img, dict) and "fields" in img:
                file_data = img["fields"].get("file", {})
                if "url" in file_data:
                    images.append(f"https:{file_data['url']}")
    
    return ProductData(
        id=contentful_data.get("sys", {}).get("id", ""),
        title=fields.get("title", ""),
        body_html=fields.get("description", ""),
        vendor=fields.get("brand", ""),
        product_type=fields.get("category", ""),
        price=float(fields.get("price", 0)),
        sku=fields.get("sku", ""),
        tags=fields.get("tags", []) if isinstance(fields.get("tags"), list) else [],
        images=images,
        status="active",
        published=contentful_data.get("sys", {}).get("publishedAt") is not None
    )