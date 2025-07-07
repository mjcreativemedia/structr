"""
Batch Manager

High-level coordinator for batch processing operations.
Manages job queues, parallel processing, and progress monitoring.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta
import threading
import logging

from models.pdp import ProductData
from batch.queues.job_queue import JobQueue, Job, JobType, JobStatus, JobResult, get_job_queue
from batch.processors.parallel_processor import BatchProductProcessor, ProcessingConfig, ProcessingResult
from connectors.base import BaseConnector, ImportResult, ExportResult


class BatchManager:
    """
    High-level batch processing manager.
    
    Coordinates:
    - Data import from connectors
    - Job queue management
    - Parallel processing
    - Progress monitoring
    - Result aggregation
    """
    
    def __init__(self, 
                 output_dir: Optional[Path] = None,
                 processing_config: Optional[ProcessingConfig] = None):
        
        self.output_dir = output_dir or Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.job_queue = get_job_queue()
        self.processor = BatchProductProcessor(processing_config)
        
        # Register job processors with queue
        self._register_job_processors()
        
        # Progress tracking
        self._active_batches: Dict[str, Dict[str, Any]] = {}
        self._batch_lock = threading.RLock()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _register_job_processors(self) -> None:
        """Register job processing functions with the job queue"""
        
        def process_generate_job(job: Job) -> JobResult:
            return self._process_generate_job(job)
        
        def process_audit_job(job: Job) -> JobResult:
            return self._process_audit_job(job)
        
        def process_fix_job(job: Job) -> JobResult:
            return self._process_fix_job(job)
        
        def process_import_job(job: Job) -> JobResult:
            return self._process_import_job(job)
        
        def process_export_job(job: Job) -> JobResult:
            return self._process_export_job(job)
        
        # Register processors
        self.job_queue.register_processor(JobType.BATCH_GENERATE, process_generate_job)
        self.job_queue.register_processor(JobType.BATCH_AUDIT, process_audit_job)
        self.job_queue.register_processor(JobType.BATCH_FIX, process_fix_job)
        self.job_queue.register_processor(JobType.IMPORT, process_import_job)
        self.job_queue.register_processor(JobType.EXPORT, process_export_job)
    
    def import_and_generate(self, 
                           connector: BaseConnector,
                           source: Union[str, Path, Dict],
                           priority: int = 0) -> str:
        """
        Import products from connector and generate PDPs.
        
        Returns batch_id for tracking progress.
        """
        batch_id = f"batch_{int(time.time())}"
        
        # Create import job
        import_job_id = self.job_queue.submit_job(
            job_type=JobType.IMPORT,
            input_data={
                'connector': connector,
                'source': source,
                'batch_id': batch_id
            },
            priority=priority,
            metadata={'batch_id': batch_id}
        )
        
        # Create dependent generation job
        generate_job_id = self.job_queue.submit_job(
            job_type=JobType.BATCH_GENERATE,
            input_data={
                'batch_id': batch_id,
                'source': 'import_result'
            },
            priority=priority,
            dependencies=[import_job_id],
            metadata={'batch_id': batch_id}
        )
        
        # Track batch
        with self._batch_lock:
            self._active_batches[batch_id] = {
                'created_at': datetime.now(),
                'import_job_id': import_job_id,
                'generate_job_id': generate_job_id,
                'status': 'importing',
                'total_products': 0,
                'processed_products': 0
            }
        
        return batch_id
    
    def generate_batch(self, 
                      products: List[ProductData],
                      priority: int = 0) -> str:
        """
        Generate PDPs for a batch of products.
        
        Returns batch_id for tracking progress.
        """
        batch_id = f"generate_{int(time.time())}"
        
        job_id = self.job_queue.submit_job(
            job_type=JobType.BATCH_GENERATE,
            input_data={
                'products': products,
                'batch_id': batch_id
            },
            priority=priority,
            metadata={'batch_id': batch_id}
        )
        
        # Track batch
        with self._batch_lock:
            self._active_batches[batch_id] = {
                'created_at': datetime.now(),
                'job_id': job_id,
                'status': 'queued',
                'total_products': len(products),
                'processed_products': 0
            }
        
        return batch_id
    
    def audit_batch(self, 
                   product_ids: List[str],
                   priority: int = 0) -> str:
        """
        Audit a batch of existing PDP bundles.
        
        Returns batch_id for tracking progress.
        """
        batch_id = f"audit_{int(time.time())}"
        
        job_id = self.job_queue.submit_job(
            job_type=JobType.BATCH_AUDIT,
            input_data={
                'product_ids': product_ids,
                'batch_id': batch_id
            },
            priority=priority,
            metadata={'batch_id': batch_id}
        )
        
        # Track batch
        with self._batch_lock:
            self._active_batches[batch_id] = {
                'created_at': datetime.now(),
                'job_id': job_id,
                'status': 'queued',
                'total_products': len(product_ids),
                'processed_products': 0
            }
        
        return batch_id
    
    def fix_batch(self, 
                 product_ids: List[str],
                 priority: int = 0) -> str:
        """
        Fix a batch of flagged PDP bundles.
        
        Returns batch_id for tracking progress.
        """
        batch_id = f"fix_{int(time.time())}"
        
        job_id = self.job_queue.submit_job(
            job_type=JobType.BATCH_FIX,
            input_data={
                'product_ids': product_ids,
                'batch_id': batch_id
            },
            priority=priority,
            metadata={'batch_id': batch_id}
        )
        
        # Track batch
        with self._batch_lock:
            self._active_batches[batch_id] = {
                'created_at': datetime.now(),
                'job_id': job_id,
                'status': 'queued',
                'total_products': len(product_ids),
                'processed_products': 0
            }
        
        return batch_id
    
    def export_batch(self,
                    product_ids: List[str],
                    connector: BaseConnector,
                    destination: Union[str, Path],
                    priority: int = 0) -> str:
        """
        Export a batch of PDP bundles using connector.
        
        Returns batch_id for tracking progress.
        """
        batch_id = f"export_{int(time.time())}"
        
        job_id = self.job_queue.submit_job(
            job_type=JobType.EXPORT,
            input_data={
                'product_ids': product_ids,
                'connector': connector,
                'destination': destination,
                'batch_id': batch_id
            },
            priority=priority,
            metadata={'batch_id': batch_id}
        )
        
        # Track batch
        with self._batch_lock:
            self._active_batches[batch_id] = {
                'created_at': datetime.now(),
                'job_id': job_id,
                'status': 'queued',
                'total_products': len(product_ids),
                'processed_products': 0
            }
        
        return batch_id
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a batch operation"""
        with self._batch_lock:
            batch_info = self._active_batches.get(batch_id)
            if not batch_info:
                return None
            
            # Get job status
            job_id = batch_info.get('job_id') or batch_info.get('generate_job_id')
            job = self.job_queue.get_job(job_id) if job_id else None
            
            status = {
                'batch_id': batch_id,
                'created_at': batch_info['created_at'].isoformat(),
                'status': batch_info['status'],
                'total_products': batch_info['total_products'],
                'processed_products': batch_info['processed_products'],
                'completion_percentage': 0.0,
                'estimated_remaining_time': None,
                'job_status': job.status.value if job else 'unknown'
            }
            
            if batch_info['total_products'] > 0:
                status['completion_percentage'] = (
                    batch_info['processed_products'] / batch_info['total_products'] * 100
                )
            
            # Add job-specific details
            if job:
                status['job_details'] = {
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'duration': job.duration,
                    'retry_count': job.retry_count
                }
                
                if job.result:
                    status['result'] = {
                        'success': job.result.success,
                        'processing_time': job.result.processing_time,
                        'error': job.result.error,
                        'warnings': job.result.warnings
                    }
            
            return status
    
    def get_active_batches(self) -> List[Dict[str, Any]]:
        """Get status of all active batches"""
        with self._batch_lock:
            return [
                self.get_batch_status(batch_id) 
                for batch_id in self._active_batches.keys()
            ]
    
    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a batch operation"""
        with self._batch_lock:
            batch_info = self._active_batches.get(batch_id)
            if not batch_info:
                return False
            
            # Cancel all related jobs
            job_ids = []
            if 'job_id' in batch_info:
                job_ids.append(batch_info['job_id'])
            if 'import_job_id' in batch_info:
                job_ids.append(batch_info['import_job_id'])
            if 'generate_job_id' in batch_info:
                job_ids.append(batch_info['generate_job_id'])
            
            cancelled_count = 0
            for job_id in job_ids:
                if self.job_queue.cancel_job(job_id):
                    cancelled_count += 1
            
            if cancelled_count > 0:
                batch_info['status'] = 'cancelled'
                return True
            
            return False
    
    def cleanup_completed_batches(self, older_than_hours: int = 24) -> int:
        """Clean up completed batch tracking data"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        cleaned_count = 0
        
        with self._batch_lock:
            batches_to_remove = []
            
            for batch_id, batch_info in self._active_batches.items():
                if (batch_info['status'] in ['completed', 'failed', 'cancelled'] and
                    batch_info['created_at'] < cutoff):
                    batches_to_remove.append(batch_id)
            
            for batch_id in batches_to_remove:
                del self._active_batches[batch_id]
                cleaned_count += 1
        
        # Also clean up job queue
        cleaned_count += self.job_queue.clear_completed_jobs(older_than_hours)
        
        return cleaned_count
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get overall performance metrics"""
        job_stats = self.job_queue.get_job_stats()
        
        with self._batch_lock:
            active_batch_count = len([
                b for b in self._active_batches.values() 
                if b['status'] not in ['completed', 'failed', 'cancelled']
            ])
        
        return {
            'active_batches': active_batch_count,
            'job_queue_stats': job_stats,
            'processor_stats': self.processor.processor.get_performance_stats(),
            'output_directory': str(self.output_dir),
            'timestamp': datetime.now().isoformat()
        }
    
    # Job processor methods
    
    def _process_import_job(self, job: Job) -> JobResult:
        """Process import job"""
        try:
            input_data = job.input_data
            connector = input_data['connector']
            source = input_data['source']
            batch_id = input_data['batch_id']
            
            # Import data
            import_result = connector.import_data(source)
            
            if not import_result.success:
                return JobResult(
                    success=False,
                    error=f"Import failed: {'; '.join(import_result.errors)}"
                )
            
            # Save imported products for next job
            products_file = self.output_dir / f"{batch_id}_imported_products.json"
            products_data = [p.dict() for p in import_result.imported_products]
            
            with open(products_file, 'w') as f:
                json.dump(products_data, f, indent=2, default=str)
            
            # Update batch tracking
            with self._batch_lock:
                if batch_id in self._active_batches:
                    self._active_batches[batch_id]['total_products'] = len(import_result.imported_products)
                    self._active_batches[batch_id]['status'] = 'imported'
            
            return JobResult(
                success=True,
                data={
                    'imported_count': import_result.processed_records,
                    'failed_count': import_result.failed_records,
                    'products_file': str(products_file)
                },
                metrics={
                    'processing_time': import_result.processing_time,
                    'success_rate': import_result.success_rate
                }
            )
            
        except Exception as e:
            return JobResult(success=False, error=str(e))
    
    def _process_generate_job(self, job: Job) -> JobResult:
        """Process batch generation job"""
        try:
            input_data = job.input_data
            batch_id = input_data['batch_id']
            
            # Get products
            if 'products' in input_data:
                products = [ProductData(**p) if isinstance(p, dict) else p for p in input_data['products']]
            else:
                # Load from import result
                products_file = self.output_dir / f"{batch_id}_imported_products.json"
                with open(products_file, 'r') as f:
                    products_data = json.load(f)
                products = [ProductData(**p) for p in products_data]
            
            # Update batch status
            with self._batch_lock:
                if batch_id in self._active_batches:
                    self._active_batches[batch_id]['status'] = 'generating'
            
            # Generate PDPs
            result = self.processor.generate_batch(products, self.output_dir)
            
            # Update batch tracking
            with self._batch_lock:
                if batch_id in self._active_batches:
                    self._active_batches[batch_id]['processed_products'] = result.processed_items
                    self._active_batches[batch_id]['status'] = 'completed' if result.success_rate > 50 else 'failed'
            
            return JobResult(
                success=result.success_rate > 50,
                data={
                    'generated_count': result.processed_items,
                    'failed_count': result.failed_items,
                    'success_rate': result.success_rate,
                    'throughput': result.throughput
                },
                warnings=result.warnings[:10],  # Limit warnings
                processing_time=result.processing_time,
                metrics={
                    'batch_id': batch_id,
                    'total_items': result.total_items,
                    'processing_time': result.processing_time,
                    'throughput': result.throughput
                }
            )
            
        except Exception as e:
            return JobResult(success=False, error=str(e))
    
    def _process_audit_job(self, job: Job) -> JobResult:
        """Process batch audit job"""
        try:
            input_data = job.input_data
            product_ids = input_data['product_ids']
            batch_id = input_data['batch_id']
            
            # Update batch status
            with self._batch_lock:
                if batch_id in self._active_batches:
                    self._active_batches[batch_id]['status'] = 'auditing'
            
            # Audit PDPs
            result = self.processor.audit_batch(product_ids, self.output_dir / "bundles")
            
            # Update batch tracking
            with self._batch_lock:
                if batch_id in self._active_batches:
                    self._active_batches[batch_id]['processed_products'] = result.processed_items
                    self._active_batches[batch_id]['status'] = 'completed' if result.success_rate > 80 else 'completed_with_issues'
            
            return JobResult(
                success=True,
                data={
                    'audited_count': result.processed_items,
                    'failed_count': result.failed_items,
                    'success_rate': result.success_rate
                },
                warnings=result.warnings[:10],
                processing_time=result.processing_time,
                metrics={
                    'batch_id': batch_id,
                    'total_items': result.total_items,
                    'throughput': result.throughput
                }
            )
            
        except Exception as e:
            return JobResult(success=False, error=str(e))
    
    def _process_fix_job(self, job: Job) -> JobResult:
        """Process batch fix job"""
        try:
            input_data = job.input_data
            product_ids = input_data['product_ids']
            batch_id = input_data['batch_id']
            
            # Update batch status
            with self._batch_lock:
                if batch_id in self._active_batches:
                    self._active_batches[batch_id]['status'] = 'fixing'
            
            # Fix PDPs
            result = self.processor.fix_batch(product_ids, self.output_dir / "bundles")
            
            # Update batch tracking
            with self._batch_lock:
                if batch_id in self._active_batches:
                    self._active_batches[batch_id]['processed_products'] = result.processed_items
                    self._active_batches[batch_id]['status'] = 'completed'
            
            return JobResult(
                success=result.success_rate > 70,
                data={
                    'fixed_count': result.processed_items,
                    'failed_count': result.failed_items,
                    'success_rate': result.success_rate
                },
                warnings=result.warnings[:10],
                processing_time=result.processing_time,
                metrics={
                    'batch_id': batch_id,
                    'total_items': result.total_items,
                    'throughput': result.throughput
                }
            )
            
        except Exception as e:
            return JobResult(success=False, error=str(e))
    
    def _process_export_job(self, job: Job) -> JobResult:
        """Process batch export job"""
        try:
            input_data = job.input_data
            product_ids = input_data['product_ids']
            connector = input_data['connector']
            destination = input_data['destination']
            batch_id = input_data['batch_id']
            
            # Update batch status
            with self._batch_lock:
                if batch_id in self._active_batches:
                    self._active_batches[batch_id]['status'] = 'exporting'
            
            # Load products from bundles
            products = []
            bundle_dir = self.output_dir / "bundles"
            
            for product_id in product_ids:
                sync_file = bundle_dir / product_id / "sync.json"
                if sync_file.exists():
                    with open(sync_file, 'r') as f:
                        product_data = json.load(f)
                    products.append(ProductData(**product_data))
            
            # Export using connector
            export_result = connector.export_data(products, destination)
            
            # Update batch tracking
            with self._batch_lock:
                if batch_id in self._active_batches:
                    self._active_batches[batch_id]['processed_products'] = export_result.exported_count
                    self._active_batches[batch_id]['status'] = 'completed' if export_result.success else 'failed'
            
            return JobResult(
                success=export_result.success,
                data={
                    'exported_count': export_result.exported_count,
                    'output_path': str(export_result.output_path) if export_result.output_path else None,
                    'format': export_result.format
                },
                error='; '.join(export_result.errors) if export_result.errors else None,
                processing_time=export_result.processing_time,
                metrics={
                    'batch_id': batch_id,
                    'export_format': export_result.format,
                    'processing_time': export_result.processing_time
                }
            )
            
        except Exception as e:
            return JobResult(success=False, error=str(e))