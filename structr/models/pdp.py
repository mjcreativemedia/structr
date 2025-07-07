from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class ProductData(BaseModel):
    """Core product data structure"""
    handle: str
    title: str
    description: Optional[str] = None
    price: Optional[float] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    images: List[str] = []
    features: List[str] = []
    metafields: Dict[str, Any] = {}

class AuditResult(BaseModel):
    """Audit result for a PDP"""
    product_id: str
    score: float = Field(ge=0, le=100)
    missing_fields: List[str] = []
    flagged_issues: List[str] = []
    schema_errors: List[str] = []
    metadata_issues: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)

class PDPBundle(BaseModel):
    """Generated PDP bundle"""
    product_id: str
    html_content: str
    metadata: Dict[str, Any]
    schema_markup: Dict[str, Any]
    audit_result: AuditResult
    generation_time: float
    model_used: str
    timestamp: datetime = Field(default_factory=datetime.now)

class FixRequest(BaseModel):
    """Request to fix a broken PDP"""
    product_id: str
    target_issues: Optional[List[str]] = None  # If None, fix all flagged issues
    regenerate_html: bool = True
    update_metadata: bool = True
    update_schema: bool = True