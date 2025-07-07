"""
Monitoring API Endpoints

REST endpoints for monitoring batch operations and system health.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time
from datetime import datetime, timedelta

from batch.monitors.progress_monitor import get_progress_monitor, ProgressSnapshot
from batch.queues.job_queue import get_job_queue
from batch.processors.batch_manager import BatchManager

router = APIRouter()

# Initialize components  
progress_monitor = get_progress_monitor()
job_queue = get_job_queue()
batch_manager = BatchManager()


# Pydantic models
class AlertResponse(BaseModel):
    type: str
    message: str
    timestamp: str


class ProgressResponse(BaseModel):
    operation_id: str
    timestamp: str
    total_items: int
    processed_items: int
    failed_items: int
    completion_percentage: float
    throughput: float
    estimated_remaining_time: Optional[float]
    active_workers: int
    memory_usage_mb: float


class PerformanceSummaryResponse(BaseModel):
    operation_id: str
    operation_type: str
    status: str
    duration_seconds: float
    total_items: int
    processed_items: int
    failed_items: int
    success_rate: float
    throughput: Dict[str, float]
    memory_usage: Dict[str, float]
    estimated_remaining_time: Optional[float]


@router.get("/health", summary="System health check")
async def health_check():
    """Comprehensive system health check"""
    
    try:
        # Check job queue health
        job_stats = job_queue.get_job_stats()
        queue_healthy = job_stats.get('running', 0) < 10  # Not too many running jobs
        
        # Check batch manager health
        batch_metrics = batch_manager.get_performance_metrics()
        batch_healthy = batch_metrics.get('active_batches', 0) < 50  # Not too many active batches
        
        # Check progress monitor health
        all_progress = progress_monitor.get_all_progress()
        monitor_healthy = len(all_progress) < 100  # Not tracking too many operations
        
        # Get alerts
        alerts = progress_monitor.get_alerts(limit=5)
        recent_alerts = len([a for a in alerts if 
                           datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(minutes=30)])
        alerts_healthy = recent_alerts < 10  # Not too many recent alerts
        
        # Overall health
        overall_healthy = queue_healthy and batch_healthy and monitor_healthy and alerts_healthy
        
        health_status = {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": time.time(),
            "components": {
                "job_queue": {
                    "status": "healthy" if queue_healthy else "degraded",
                    "stats": job_stats
                },
                "batch_manager": {
                    "status": "healthy" if batch_healthy else "degraded", 
                    "active_batches": batch_metrics.get('active_batches', 0)
                },
                "progress_monitor": {
                    "status": "healthy" if monitor_healthy else "degraded",
                    "tracked_operations": len(all_progress)
                },
                "alerts": {
                    "status": "healthy" if alerts_healthy else "warning",
                    "recent_alert_count": recent_alerts
                }
            },
            "uptime_seconds": time.time() - batch_metrics.get('processor_stats', {}).get('start_time', time.time()),
            "version": "0.1.0"
        }
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }


@router.get("/operations", summary="List monitored operations")
async def list_operations(
    status: Optional[str] = Query(None, description="Filter by status: running, completed, failed"),
    limit: int = Query(50, ge=1, le=500, description="Maximum operations to return")
):
    """List all monitored operations with current progress"""
    
    try:
        # Get all progress data
        all_progress = progress_monitor.get_all_progress()
        
        operations = []
        for operation_id, snapshot in all_progress.items():
            operation_info = {
                "operation_id": operation_id,
                "current_progress": ProgressResponse(
                    operation_id=operation_id,
                    timestamp=snapshot.timestamp.isoformat(),
                    total_items=snapshot.total_items,
                    processed_items=snapshot.processed_items,
                    failed_items=snapshot.failed_items,
                    completion_percentage=snapshot.completion_percentage,
                    throughput=snapshot.throughput,
                    estimated_remaining_time=snapshot.estimated_remaining_time,
                    active_workers=snapshot.active_workers,
                    memory_usage_mb=snapshot.memory_usage_mb
                ).dict()
            }
            
            # Add performance summary if available
            summary = progress_monitor.get_performance_summary(operation_id)
            if summary:
                operation_info["performance_summary"] = summary
            
            operations.append(operation_info)
        
        # Sort by most recent first
        operations.sort(key=lambda x: x["current_progress"]["timestamp"], reverse=True)
        
        # Apply limit
        operations = operations[:limit]
        
        return {
            "operations": operations,
            "total_count": len(all_progress),
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list operations: {str(e)}")


@router.get("/operations/{operation_id}", summary="Get operation progress")
async def get_operation_progress(operation_id: str):
    """Get current progress for specific operation"""
    
    try:
        snapshot = progress_monitor.get_progress(operation_id)
        
        if not snapshot:
            raise HTTPException(status_code=404, detail=f"Operation {operation_id} not found")
        
        return ProgressResponse(
            operation_id=operation_id,
            timestamp=snapshot.timestamp.isoformat(),
            total_items=snapshot.total_items,
            processed_items=snapshot.processed_items,
            failed_items=snapshot.failed_items,
            completion_percentage=snapshot.completion_percentage,
            throughput=snapshot.throughput,
            estimated_remaining_time=snapshot.estimated_remaining_time,
            active_workers=snapshot.active_workers,
            memory_usage_mb=snapshot.memory_usage_mb
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get operation progress: {str(e)}")


@router.get("/operations/{operation_id}/history", summary="Get operation history")
async def get_operation_history(
    operation_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum history entries to return")
):
    """Get progress history for specific operation"""
    
    try:
        history = progress_monitor.get_operation_history(operation_id, limit)
        
        if not history:
            raise HTTPException(status_code=404, detail=f"Operation {operation_id} not found")
        
        formatted_history = []
        for snapshot in history:
            formatted_history.append({
                "timestamp": snapshot.timestamp.isoformat(),
                "total_items": snapshot.total_items,
                "processed_items": snapshot.processed_items,
                "failed_items": snapshot.failed_items,
                "completion_percentage": snapshot.completion_percentage,
                "throughput": snapshot.throughput,
                "estimated_remaining_time": snapshot.estimated_remaining_time,
                "memory_usage_mb": snapshot.memory_usage_mb
            })
        
        return {
            "operation_id": operation_id,
            "history": formatted_history,
            "history_count": len(formatted_history),
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get operation history: {str(e)}")


@router.get("/operations/{operation_id}/summary", response_model=PerformanceSummaryResponse, summary="Get operation performance summary")
async def get_operation_summary(operation_id: str):
    """Get comprehensive performance summary for operation"""
    
    try:
        summary = progress_monitor.get_performance_summary(operation_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail=f"Operation {operation_id} not found")
        
        return PerformanceSummaryResponse(**summary)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get operation summary: {str(e)}")


@router.get("/alerts", summary="Get system alerts")
async def get_alerts(
    limit: int = Query(50, ge=1, le=500, description="Maximum alerts to return"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type")
):
    """Get recent system alerts and warnings"""
    
    try:
        alerts = progress_monitor.get_alerts(limit)
        
        # Filter by type if specified
        if alert_type:
            alerts = [a for a in alerts if a.get('type') == alert_type]
        
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append(AlertResponse(
                type=alert['type'],
                message=alert['message'],
                timestamp=alert['timestamp']
            ).dict())
        
        # Group alerts by type for summary
        alert_summary = {}
        for alert in alerts:
            alert_type = alert['type']
            if alert_type not in alert_summary:
                alert_summary[alert_type] = 0
            alert_summary[alert_type] += 1
        
        return {
            "alerts": formatted_alerts,
            "alert_count": len(formatted_alerts),
            "alert_summary": alert_summary,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.delete("/alerts", summary="Clear all alerts")
async def clear_alerts():
    """Clear all system alerts"""
    
    try:
        progress_monitor.clear_alerts()
        
        return {
            "success": True,
            "message": "All alerts cleared",
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear alerts: {str(e)}")


@router.get("/metrics", summary="Get system metrics")
async def get_system_metrics():
    """Get comprehensive system performance metrics"""
    
    try:
        # Get metrics from different components
        batch_metrics = batch_manager.get_performance_metrics()
        job_stats = job_queue.get_job_stats()
        
        # Get active operations
        active_operations = progress_monitor.get_all_progress()
        
        # Calculate system-wide metrics
        total_throughput = sum(op.throughput for op in active_operations.values())
        total_memory = sum(op.memory_usage_mb for op in active_operations.values())
        
        # Get alert counts
        alerts = progress_monitor.get_alerts(limit=1000)
        recent_alerts = len([a for a in alerts if 
                           datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=1)])
        
        metrics = {
            "system_overview": {
                "active_operations": len(active_operations),
                "total_throughput_per_sec": total_throughput,
                "total_memory_usage_mb": total_memory,
                "recent_alerts_1h": recent_alerts,
                "uptime_seconds": time.time() - batch_metrics.get('processor_stats', {}).get('start_time', time.time())
            },
            "job_queue": job_stats,
            "batch_processing": batch_metrics,
            "performance": {
                "operations_by_status": {
                    "running": len([op for op in active_operations.values() 
                                  if op.completion_percentage < 100]),
                    "completed": len([op for op in active_operations.values() 
                                   if op.completion_percentage >= 100])
                },
                "average_throughput": total_throughput / max(1, len(active_operations)),
                "peak_memory_usage": max([op.memory_usage_mb for op in active_operations.values()], default=0)
            },
            "timestamp": time.time()
        }
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")


@router.post("/operations/{operation_id}/export", summary="Export operation data")
async def export_operation_data(operation_id: str):
    """Export operation history and performance data"""
    
    try:
        # Export to file
        output_file = Path(f"output/exports/operation_{operation_id}_{int(time.time())}.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        success = progress_monitor.export_history(operation_id, output_file)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Operation {operation_id} not found or export failed")
        
        return {
            "success": True,
            "operation_id": operation_id,
            "export_file": str(output_file),
            "download_url": f"/api/v1/monitoring/download/{output_file.name}",
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/download/{filename}", summary="Download monitoring export")
async def download_export(filename: str):
    """Download exported monitoring data"""
    
    try:
        from fastapi.responses import FileResponse
        
        export_dir = Path("output/exports")
        file_path = export_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Export file {filename} not found")
        
        # Security check: ensure file is within exports directory
        try:
            file_path.resolve().relative_to(export_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/live", summary="Live system status")
async def get_live_status():
    """Get real-time system status for dashboards"""
    
    try:
        # Get current active operations
        active_operations = progress_monitor.get_all_progress()
        
        # Get recent job activity
        job_stats = job_queue.get_job_stats()
        
        # Calculate live metrics
        running_ops = [op for op in active_operations.values() if op.completion_percentage < 100]
        total_items_processing = sum(op.total_items for op in running_ops)
        total_processed = sum(op.processed_items for op in running_ops)
        
        live_status = {
            "status": "active" if running_ops else "idle",
            "active_operations": len(running_ops),
            "total_items_in_progress": total_items_processing,
            "total_items_processed": total_processed,
            "current_throughput": sum(op.throughput for op in running_ops),
            "queue_size": job_stats.get('pending', 0),
            "running_jobs": job_stats.get('running', 0),
            "memory_usage_mb": sum(op.memory_usage_mb for op in running_ops),
            "timestamp": time.time(),
            "last_activity": max([op.timestamp for op in active_operations.values()]).isoformat() if active_operations else None
        }
        
        # Add recent alerts
        recent_alerts = progress_monitor.get_alerts(limit=5)
        live_status["recent_alerts"] = len(recent_alerts)
        
        return live_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get live status: {str(e)}")


@router.post("/alerts/test", summary="Create test alert")
async def create_test_alert(
    alert_type: str = "test",
    message: str = "Test alert from API"
):
    """Create a test alert for monitoring system validation"""
    
    try:
        # Access the internal alert system
        progress_monitor._add_alert(alert_type, message)
        
        return {
            "success": True,
            "message": "Test alert created",
            "alert_type": alert_type,
            "alert_message": message,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create test alert: {str(e)}")