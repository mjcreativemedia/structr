"""
Progress Monitor

Real-time monitoring and reporting for batch operations.
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import json

from batch.queues.job_queue import JobQueue, JobStatus


@dataclass
class ProgressSnapshot:
    """Point-in-time progress snapshot"""
    timestamp: datetime
    total_items: int
    processed_items: int
    failed_items: int
    completion_percentage: float
    throughput: float  # items per second
    estimated_remaining_time: Optional[float]  # seconds
    active_workers: int
    memory_usage_mb: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'failed_items': self.failed_items,
            'completion_percentage': self.completion_percentage,
            'throughput': self.throughput,
            'estimated_remaining_time': self.estimated_remaining_time,
            'active_workers': self.active_workers,
            'memory_usage_mb': self.memory_usage_mb
        }


class ProgressMonitor:
    """
    Real-time progress monitoring for batch operations.
    
    Features:
    - Live progress tracking
    - Performance metrics
    - Alerts and notifications
    - Historical data retention
    - Export capabilities
    """
    
    def __init__(self, 
                 update_interval: int = 5,  # seconds
                 history_retention_hours: int = 24,
                 storage_dir: Optional[Path] = None):
        
        self.update_interval = update_interval
        self.history_retention_hours = history_retention_hours
        self.storage_dir = storage_dir or Path("output/monitoring")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Progress tracking
        self._monitored_operations: Dict[str, Dict[str, Any]] = {}
        self._progress_history: Dict[str, List[ProgressSnapshot]] = {}
        self._callbacks: List[Callable[[str, ProgressSnapshot], None]] = []
        self._alerts: List[Dict[str, Any]] = []
        
        # Threading
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # Start monitoring
        self.start_monitoring()
    
    def register_operation(self, 
                          operation_id: str,
                          operation_type: str,
                          total_items: int,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register a new operation for monitoring"""
        
        with self._lock:
            self._monitored_operations[operation_id] = {
                'operation_type': operation_type,
                'total_items': total_items,
                'processed_items': 0,
                'failed_items': 0,
                'start_time': datetime.now(),
                'last_update': datetime.now(),
                'status': 'running',
                'metadata': metadata or {}
            }
            
            self._progress_history[operation_id] = []
    
    def update_progress(self, 
                       operation_id: str,
                       processed_items: int,
                       failed_items: int = 0,
                       additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Update progress for an operation"""
        
        with self._lock:
            if operation_id not in self._monitored_operations:
                return
            
            operation = self._monitored_operations[operation_id]
            operation['processed_items'] = processed_items
            operation['failed_items'] = failed_items
            operation['last_update'] = datetime.now()
            
            if additional_data:
                operation['metadata'].update(additional_data)
            
            # Create progress snapshot
            snapshot = self._create_snapshot(operation_id, operation)
            self._progress_history[operation_id].append(snapshot)
            
            # Cleanup old history
            self._cleanup_history(operation_id)
            
            # Trigger callbacks
            for callback in self._callbacks:
                try:
                    callback(operation_id, snapshot)
                except Exception as e:
                    self._add_alert('callback_error', f"Progress callback failed: {str(e)}")
    
    def complete_operation(self, 
                          operation_id: str,
                          status: str = 'completed') -> None:
        """Mark operation as completed"""
        
        with self._lock:
            if operation_id in self._monitored_operations:
                operation = self._monitored_operations[operation_id]
                operation['status'] = status
                operation['end_time'] = datetime.now()
                
                # Create final snapshot
                snapshot = self._create_snapshot(operation_id, operation)
                self._progress_history[operation_id].append(snapshot)
                
                # Save operation summary
                self._save_operation_summary(operation_id, operation)
    
    def get_progress(self, operation_id: str) -> Optional[ProgressSnapshot]:
        """Get current progress for an operation"""
        
        with self._lock:
            if operation_id not in self._monitored_operations:
                return None
            
            operation = self._monitored_operations[operation_id]
            return self._create_snapshot(operation_id, operation)
    
    def get_all_progress(self) -> Dict[str, ProgressSnapshot]:
        """Get progress for all active operations"""
        
        with self._lock:
            progress = {}
            for operation_id, operation in self._monitored_operations.items():
                if operation['status'] == 'running':
                    progress[operation_id] = self._create_snapshot(operation_id, operation)
            return progress
    
    def get_operation_history(self, 
                             operation_id: str,
                             limit: Optional[int] = None) -> List[ProgressSnapshot]:
        """Get progress history for an operation"""
        
        with self._lock:
            history = self._progress_history.get(operation_id, [])
            if limit:
                history = history[-limit:]
            return history.copy()
    
    def get_performance_summary(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get performance summary for an operation"""
        
        with self._lock:
            if operation_id not in self._monitored_operations:
                return None
            
            operation = self._monitored_operations[operation_id]
            history = self._progress_history.get(operation_id, [])
            
            if not history:
                return None
            
            # Calculate metrics
            start_time = operation['start_time']
            end_time = operation.get('end_time', datetime.now())
            duration = (end_time - start_time).total_seconds()
            
            latest_snapshot = history[-1]
            
            # Throughput over time
            throughput_history = [s.throughput for s in history if s.throughput > 0]
            avg_throughput = sum(throughput_history) / len(throughput_history) if throughput_history else 0
            max_throughput = max(throughput_history) if throughput_history else 0
            
            # Memory usage
            memory_history = [s.memory_usage_mb for s in history]
            avg_memory = sum(memory_history) / len(memory_history) if memory_history else 0
            max_memory = max(memory_history) if memory_history else 0
            
            return {
                'operation_id': operation_id,
                'operation_type': operation['operation_type'],
                'status': operation['status'],
                'duration_seconds': duration,
                'total_items': operation['total_items'],
                'processed_items': latest_snapshot.processed_items,
                'failed_items': latest_snapshot.failed_items,
                'success_rate': (latest_snapshot.processed_items / operation['total_items'] * 100) if operation['total_items'] > 0 else 0,
                'throughput': {
                    'current': latest_snapshot.throughput,
                    'average': avg_throughput,
                    'maximum': max_throughput
                },
                'memory_usage': {
                    'current': latest_snapshot.memory_usage_mb,
                    'average': avg_memory,
                    'maximum': max_memory
                },
                'estimated_remaining_time': latest_snapshot.estimated_remaining_time
            }
    
    def add_progress_callback(self, callback: Callable[[str, ProgressSnapshot], None]) -> None:
        """Add callback to be triggered on progress updates"""
        self._callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[str, ProgressSnapshot], None]) -> None:
        """Remove progress callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_alerts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        with self._lock:
            alerts = self._alerts.copy()
            if limit:
                alerts = alerts[-limit:]
            return alerts
    
    def clear_alerts(self) -> None:
        """Clear all alerts"""
        with self._lock:
            self._alerts.clear()
    
    def export_history(self, 
                      operation_id: str,
                      output_file: Path) -> bool:
        """Export operation history to JSON file"""
        
        try:
            with self._lock:
                if operation_id not in self._progress_history:
                    return False
                
                history = self._progress_history[operation_id]
                operation = self._monitored_operations.get(operation_id, {})
                
                export_data = {
                    'operation_id': operation_id,
                    'operation_info': operation,
                    'progress_history': [snapshot.to_dict() for snapshot in history],
                    'performance_summary': self.get_performance_summary(operation_id),
                    'exported_at': datetime.now().isoformat()
                }
                
                with open(output_file, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                return True
                
        except Exception as e:
            self._add_alert('export_error', f"Failed to export history: {str(e)}")
            return False
    
    def start_monitoring(self) -> None:
        """Start the monitoring thread"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="ProgressMonitor",
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop the monitoring thread"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                self._update_all_progress()
                self._check_alerts()
                time.sleep(self.update_interval)
            except Exception as e:
                self._add_alert('monitor_error', f"Monitoring error: {str(e)}")
    
    def _update_all_progress(self) -> None:
        """Update progress for all active operations"""
        with self._lock:
            for operation_id, operation in list(self._monitored_operations.items()):
                if operation['status'] == 'running':
                    # Check if operation has stalled
                    last_update = operation['last_update']
                    if datetime.now() - last_update > timedelta(minutes=10):
                        self._add_alert('stalled_operation', f"Operation {operation_id} may be stalled")
                    
                    # Create periodic snapshot
                    snapshot = self._create_snapshot(operation_id, operation)
                    if self._progress_history[operation_id]:
                        last_snapshot = self._progress_history[operation_id][-1]
                        # Only add if there's been progress
                        if (snapshot.processed_items != last_snapshot.processed_items or
                            snapshot.failed_items != last_snapshot.failed_items):
                            self._progress_history[operation_id].append(snapshot)
                    else:
                        self._progress_history[operation_id].append(snapshot)
    
    def _create_snapshot(self, operation_id: str, operation: Dict[str, Any]) -> ProgressSnapshot:
        """Create progress snapshot from operation data"""
        
        total_items = operation['total_items']
        processed_items = operation['processed_items']
        failed_items = operation['failed_items']
        
        # Calculate completion percentage
        completion_percentage = (processed_items / total_items * 100) if total_items > 0 else 0
        
        # Calculate throughput
        start_time = operation['start_time']
        elapsed_time = (datetime.now() - start_time).total_seconds()
        throughput = processed_items / elapsed_time if elapsed_time > 0 else 0
        
        # Estimate remaining time
        remaining_items = total_items - processed_items
        estimated_remaining_time = remaining_items / throughput if throughput > 0 else None
        
        # Get system metrics
        try:
            import psutil
            memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
            active_workers = operation.get('active_workers', 1)
        except:
            memory_usage_mb = 0.0
            active_workers = 1
        
        return ProgressSnapshot(
            timestamp=datetime.now(),
            total_items=total_items,
            processed_items=processed_items,
            failed_items=failed_items,
            completion_percentage=completion_percentage,
            throughput=throughput,
            estimated_remaining_time=estimated_remaining_time,
            active_workers=active_workers,
            memory_usage_mb=memory_usage_mb
        )
    
    def _cleanup_history(self, operation_id: str) -> None:
        """Clean up old history entries"""
        cutoff = datetime.now() - timedelta(hours=self.history_retention_hours)
        
        history = self._progress_history.get(operation_id, [])
        self._progress_history[operation_id] = [
            snapshot for snapshot in history 
            if snapshot.timestamp > cutoff
        ]
    
    def _check_alerts(self) -> None:
        """Check for alert conditions"""
        with self._lock:
            for operation_id, operation in self._monitored_operations.items():
                if operation['status'] != 'running':
                    continue
                
                # Check for high failure rate
                total_items = operation['total_items']
                failed_items = operation['failed_items']
                
                if total_items > 0 and failed_items / total_items > 0.2:  # >20% failure rate
                    self._add_alert('high_failure_rate', 
                                  f"Operation {operation_id} has high failure rate: {failed_items}/{total_items}")
                
                # Check for low throughput
                history = self._progress_history.get(operation_id, [])
                if len(history) > 2:
                    recent_throughputs = [s.throughput for s in history[-3:]]
                    avg_throughput = sum(recent_throughputs) / len(recent_throughputs)
                    
                    if avg_throughput < 0.1:  # Less than 0.1 items per second
                        self._add_alert('low_throughput',
                                      f"Operation {operation_id} has low throughput: {avg_throughput:.2f} items/sec")
    
    def _add_alert(self, alert_type: str, message: str) -> None:
        """Add an alert"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        self._alerts.append(alert)
        
        # Limit alert history
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]
    
    def _save_operation_summary(self, operation_id: str, operation: Dict[str, Any]) -> None:
        """Save operation summary to disk"""
        try:
            summary_file = self.storage_dir / f"{operation_id}_summary.json"
            
            summary = {
                'operation_id': operation_id,
                'operation_info': operation,
                'performance_summary': self.get_performance_summary(operation_id),
                'saved_at': datetime.now().isoformat()
            }
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
                
        except Exception as e:
            self._add_alert('save_error', f"Failed to save operation summary: {str(e)}")


# Global monitor instance
_progress_monitor: Optional[ProgressMonitor] = None


def get_progress_monitor() -> ProgressMonitor:
    """Get or create global progress monitor"""
    global _progress_monitor
    if _progress_monitor is None:
        _progress_monitor = ProgressMonitor()
    return _progress_monitor


def shutdown_progress_monitor() -> None:
    """Shutdown global progress monitor"""
    global _progress_monitor
    if _progress_monitor:
        _progress_monitor.stop_monitoring()
        _progress_monitor = None