"""
Batches API Endpoints

REST endpoints for managing batch processing operations.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import time
from pathlib import Path

from batch.processors.batch_manager import BatchManager
from batch.queues.job_queue import get_job_queue, JobStatus, JobType
from models.pdp import ProductData
from api.auth import APIKeyAuth

router = APIRouter()

# Initialize components
batch_manager = BatchManager()
job_queue = get_job_queue()


# Pydantic models
class BatchGenerateRequest(BaseModel):
    products: List[Dict[str, Any]] = Field(..., description="List of product data")
    priority: int = Field(default=0, description="Job priority")
    output_format: str = Field(default="html", description="Output format: html, json")


class BatchAuditRequest(BaseModel):
    product_ids: List[str] = Field(..., description="Product IDs to audit")
    priority: int = Field(default=0, description="Job priority")
    audit_options: Dict[str, Any] = Field(default_factory=dict, description="Audit configuration")


class BatchFixRequest(BaseModel):
    product_ids: List[str] = Field(..., description="Product IDs to fix")
    priority: int = Field(default=0, description="Job priority")
    fix_options: Dict[str, Any] = Field(default_factory=dict, description="Fix configuration")


class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    total_products: int
    processed_products: int
    completion_percentage: float
    created_at: str
    estimated_remaining_time: Optional[float]
    job_status: str
    job_details: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]


@router.get("/", summary="List all batches")
async def list_batches(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of batches to return")
):
    """List all batch operations with optional filtering"""
    
    try:
        # Get active batches from batch manager
        active_batches = batch_manager.get_active_batches()
        
        # Filter by status if provided
        if status:
            active_batches = [b for b in active_batches if b and b.get('status') == status]
        
        # Limit results
        active_batches = active_batches[:limit]
        
        # Get job queue statistics
        job_stats = job_queue.get_job_stats()
        
        return {
            "batches": active_batches,
            "total_count": len(active_batches),
            "job_queue_stats": job_stats,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list batches: {str(e)}")


@router.post("/generate", summary="Start batch PDP generation")
async def start_batch_generation(
    request: BatchGenerateRequest,
    background_tasks: BackgroundTasks
):
    """Start batch generation of PDPs for multiple products"""
    
    try:
        # Validate products data
        if not request.products:
            raise HTTPException(status_code=400, detail="No products provided")
        
        if len(request.products) > 10000:
            raise HTTPException(status_code=400, detail="Maximum 10,000 products per batch")
        
        # Convert to ProductData objects
        products = []
        for i, product_data in enumerate(request.products):
            try:
                product = ProductData(**product_data)
                products.append(product)
            except Exception as e:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid product data at index {i}: {str(e)}"
                )
        
        # Start batch generation
        batch_id = batch_manager.generate_batch(
            products=products,
            priority=request.priority
        )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "message": "Batch generation started",
            "product_count": len(products),
            "priority": request.priority,
            "status_url": f"/api/v1/batches/{batch_id}/status",
            "estimated_duration": len(products) * 2  # Rough estimate: 2 seconds per product
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch generation failed: {str(e)}")


@router.post("/audit", summary="Start batch audit")
async def start_batch_audit(
    request: BatchAuditRequest,
    background_tasks: BackgroundTasks
):
    """Start batch audit of existing PDP bundles"""
    
    try:
        if not request.product_ids:
            raise HTTPException(status_code=400, detail="No product IDs provided")
        
        if len(request.product_ids) > 10000:
            raise HTTPException(status_code=400, detail="Maximum 10,000 products per batch")
        
        # Verify products exist
        bundle_dir = Path("output/bundles")
        missing_products = []
        
        for product_id in request.product_ids[:10]:  # Check first 10 only for performance
            if not (bundle_dir / product_id / "index.html").exists():
                missing_products.append(product_id)
        
        if missing_products:
            return {
                "success": False,
                "error": "Some products not found",
                "missing_products": missing_products,
                "suggestion": "Generate PDPs first using /batches/generate"
            }
        
        # Start batch audit
        batch_id = batch_manager.audit_batch(
            product_ids=request.product_ids,
            priority=request.priority
        )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "message": "Batch audit started",
            "product_count": len(request.product_ids),
            "priority": request.priority,
            "status_url": f"/api/v1/batches/{batch_id}/status",
            "estimated_duration": len(request.product_ids) * 0.5  # Rough estimate: 0.5 seconds per product
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch audit failed: {str(e)}")


@router.post("/fix", summary="Start batch fix")
async def start_batch_fix(
    request: BatchFixRequest,
    background_tasks: BackgroundTasks
):
    """Start batch fixing of flagged PDP bundles"""
    
    try:
        if not request.product_ids:
            raise HTTPException(status_code=400, detail="No product IDs provided")
        
        if len(request.product_ids) > 1000:  # Lower limit for fixes due to LLM usage
            raise HTTPException(status_code=400, detail="Maximum 1,000 products per fix batch")
        
        # Verify products exist and have audit data
        bundle_dir = Path("output/bundles")
        missing_audits = []
        
        for product_id in request.product_ids[:10]:  # Check first 10 only
            audit_file = bundle_dir / product_id / "audit.json"
            if not audit_file.exists():
                missing_audits.append(product_id)
        
        if missing_audits:
            return {
                "success": False,
                "error": "Some products missing audit data",
                "missing_audits": missing_audits,
                "suggestion": "Run audit first using /batches/audit"
            }
        
        # Start batch fix
        batch_id = batch_manager.fix_batch(
            product_ids=request.product_ids,
            priority=request.priority
        )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "message": "Batch fix started",
            "product_count": len(request.product_ids),
            "priority": request.priority,
            "status_url": f"/api/v1/batches/{batch_id}/status",
            "estimated_duration": len(request.product_ids) * 10  # Rough estimate: 10 seconds per product (LLM processing)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch fix failed: {str(e)}")


@router.get("/{batch_id}/status", response_model=BatchStatusResponse, summary="Get batch status")
async def get_batch_status(batch_id: str):
    """Get current status and progress of a batch operation"""
    
    try:
        status = batch_manager.get_batch_status(batch_id)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        return BatchStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")


@router.delete("/{batch_id}", summary="Cancel batch operation")
async def cancel_batch(batch_id: str):
    """Cancel a running batch operation"""
    
    try:
        success = batch_manager.cancel_batch(batch_id)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Batch {batch_id} not found or cannot be cancelled"
            )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "message": "Batch cancelled successfully",
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel batch: {str(e)}")


@router.get("/{batch_id}/results", summary="Get batch results")
async def get_batch_results(
    batch_id: str,
    include_details: bool = Query(False, description="Include detailed results for each product")
):
    """Get results and artifacts from completed batch operation"""
    
    try:
        # Get batch status first
        status = batch_manager.get_batch_status(batch_id)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        if status['status'] not in ['completed', 'failed', 'completed_with_issues']:
            return {
                "batch_id": batch_id,
                "status": status['status'],
                "message": "Batch not yet completed",
                "completion_percentage": status['completion_percentage']
            }
        
        # Get job results
        job_id = None
        if 'job_id' in status.get('job_details', {}):
            job_id = status['job_details']['job_id']
        
        job = job_queue.get_job(job_id) if job_id else None
        
        results = {
            "batch_id": batch_id,
            "status": status['status'],
            "total_products": status['total_products'],
            "processed_products": status['processed_products'],
            "completion_percentage": status['completion_percentage'],
            "processing_time": None,
            "results_summary": {},
            "artifacts": []
        }
        
        if job and job.result:
            results.update({
                "processing_time": job.result.processing_time,
                "results_summary": job.result.data or {},
                "errors": job.result.error,
                "warnings": job.result.warnings
            })
            
            # List output artifacts
            artifacts = []
            output_dir = Path("output")
            
            # Look for batch-specific files
            for pattern in [f"{batch_id}*", f"*{batch_id}*"]:
                for file_path in output_dir.rglob(pattern):
                    if file_path.is_file():
                        artifacts.append({
                            "type": "file",
                            "name": file_path.name,
                            "path": str(file_path.relative_to(output_dir)),
                            "size": file_path.stat().st_size,
                            "download_url": f"/api/v1/batches/{batch_id}/download/{file_path.name}"
                        })
            
            results["artifacts"] = artifacts
        
        # Include detailed product results if requested
        if include_details and job and job.result:
            # This could be large, so limit and paginate in production
            detailed_results = job.result.data.get('detailed_results', [])
            results["detailed_results"] = detailed_results[:100]  # Limit to first 100
            
            if len(detailed_results) > 100:
                results["detailed_results_truncated"] = True
                results["total_detailed_results"] = len(detailed_results)
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get batch results: {str(e)}")


@router.get("/{batch_id}/download/{filename}", summary="Download batch artifact")
async def download_batch_artifact(batch_id: str, filename: str):
    """Download files generated by batch operation"""
    
    try:
        # Security: only allow downloading files from batch output
        output_dir = Path("output")
        
        # Look for file in various locations
        possible_paths = [
            output_dir / filename,
            output_dir / f"{batch_id}_{filename}",
            output_dir / "exports" / filename,
            output_dir / "bundles" / filename
        ]
        
        file_path = None
        for path in possible_paths:
            if path.exists() and path.is_file():
                file_path = path
                break
        
        if not file_path:
            raise HTTPException(status_code=404, detail=f"File {filename} not found for batch {batch_id}")
        
        # Security check: ensure file is within output directory
        try:
            file_path.resolve().relative_to(output_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/cleanup", summary="Clean up completed batches")
async def cleanup_batches(
    older_than_hours: int = Query(24, ge=1, le=168, description="Clean batches older than N hours")
):
    """Clean up completed batch data older than specified time"""
    
    try:
        cleaned_count = batch_manager.cleanup_completed_batches(older_than_hours)
        
        return {
            "success": True,
            "cleaned_batches": cleaned_count,
            "older_than_hours": older_than_hours,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.get("/stats", summary="Get batch processing statistics")
async def get_batch_stats():
    """Get overall batch processing statistics and performance metrics"""
    
    try:
        # Get performance metrics
        metrics = batch_manager.get_performance_metrics()
        
        # Get job queue stats
        job_stats = job_queue.get_job_stats()
        
        # Calculate additional stats
        total_jobs = sum(job_stats.values()) - job_stats.get('total', 0)  # Exclude total from sum
        
        stats = {
            "batch_metrics": metrics,
            "job_queue": job_stats,
            "performance": {
                "total_jobs_processed": total_jobs,
                "success_rate": (job_stats.get('completed', 0) / max(1, total_jobs)) * 100,
                "current_queue_size": job_stats.get('pending', 0) + job_stats.get('running', 0)
            },
            "system_info": {
                "output_directory": str(metrics.get('output_directory', 'output')),
                "timestamp": time.time()
            }
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/queue", summary="Get job queue status")
async def get_queue_status():
    """Get detailed job queue status and running jobs"""
    
    try:
        # Get jobs by status
        pending_jobs = job_queue.get_jobs_by_status(JobStatus.PENDING)
        running_jobs = job_queue.get_jobs_by_status(JobStatus.RUNNING)
        completed_jobs = job_queue.get_jobs_by_status(JobStatus.COMPLETED)
        failed_jobs = job_queue.get_jobs_by_status(JobStatus.FAILED)
        
        # Format job info (limit details for API response)
        def format_job(job):
            return {
                "id": job.id,
                "type": job.job_type.value,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "duration": job.duration,
                "retry_count": job.retry_count,
                "priority": job.priority
            }
        
        return {
            "queue_status": {
                "pending": [format_job(job) for job in pending_jobs[:10]],  # Limit to 10
                "running": [format_job(job) for job in running_jobs],
                "recent_completed": [format_job(job) for job in completed_jobs[-5:]],  # Last 5
                "recent_failed": [format_job(job) for job in failed_jobs[-5:]]  # Last 5
            },
            "counts": {
                "pending": len(pending_jobs),
                "running": len(running_jobs),
                "completed": len(completed_jobs),
                "failed": len(failed_jobs)
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")


from fastapi.responses import FileResponse