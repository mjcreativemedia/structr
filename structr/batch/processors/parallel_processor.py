"""
Parallel Processor

High-performance parallel processing for PDP operations.
Handles thousands of products efficiently using multiprocessing.
"""

import multiprocessing as mp
import concurrent.futures
from typing import List, Dict, Any, Callable, Optional, Iterator, Union
from dataclasses import dataclass
from pathlib import Path
import time
import logging
import queue
import threading
import psutil

from models.pdp import ProductData
from batch.queues.job_queue import Job, JobResult, JobStatus


@dataclass
class ProcessingConfig:
    """Configuration for parallel processing"""
    max_workers: int = 0  # 0 = auto-detect
    batch_size: int = 100
    chunk_size: int = 10  # Items per worker chunk
    timeout_per_item: int = 60  # Seconds per item
    memory_limit_mb: int = 1000  # Memory limit per worker
    enable_progress_callback: bool = True
    fail_fast: bool = False  # Stop on first error


@dataclass
class ProcessingResult:
    """Result of parallel processing operation"""
    total_items: int
    processed_items: int
    failed_items: int
    success_rate: float
    processing_time: float
    errors: List[str]
    warnings: List[str]
    results: List[Any]
    
    @property
    def throughput(self) -> float:
        """Items processed per second"""
        return self.processed_items / self.processing_time if self.processing_time > 0 else 0.0


class ParallelProcessor:
    """
    High-performance parallel processor for PDP operations.
    
    Supports:
    - Multiprocessing for CPU-intensive tasks
    - Threading for I/O-intensive tasks  
    - Automatic worker scaling
    - Memory management
    - Progress tracking
    - Error handling and recovery
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.config = config or ProcessingConfig()
        
        # Auto-detect optimal worker count
        if self.config.max_workers <= 0:
            self.config.max_workers = min(mp.cpu_count(), 8)  # Cap at 8 for memory reasons
        
        # Progress tracking
        self._progress_callbacks: List[Callable] = []
        self._total_items = 0
        self._processed_items = 0
        self._start_time = 0.0
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def add_progress_callback(self, callback: Callable[[int, int, float], None]) -> None:
        """Add progress callback function(processed, total, elapsed_time)"""
        self._progress_callbacks.append(callback)
    
    def process_batch_multiprocessing(
        self,
        items: List[Any],
        processor_func: Callable[[Any], Any],
        **kwargs
    ) -> ProcessingResult:
        """
        Process items using multiprocessing for CPU-intensive tasks.
        
        Best for: Generation, audit, heavy text processing
        """
        return self._process_with_executor(
            items,
            processor_func,
            concurrent.futures.ProcessPoolExecutor,
            **kwargs
        )
    
    def process_batch_threading(
        self,
        items: List[Any],
        processor_func: Callable[[Any], Any], 
        **kwargs
    ) -> ProcessingResult:
        """
        Process items using threading for I/O-intensive tasks.
        
        Best for: API calls, file operations, database operations
        """
        return self._process_with_executor(
            items,
            processor_func,
            concurrent.futures.ThreadPoolExecutor,
            **kwargs
        )
    
    def _process_with_executor(
        self,
        items: List[Any],
        processor_func: Callable[[Any], Any],
        executor_class: type,
        **kwargs
    ) -> ProcessingResult:
        """Generic processing with configurable executor"""
        
        self._total_items = len(items)
        self._processed_items = 0
        self._start_time = time.time()
        
        result = ProcessingResult(
            total_items=len(items),
            processed_items=0,
            failed_items=0,
            success_rate=0.0,
            processing_time=0.0,
            errors=[],
            warnings=[],
            results=[]
        )
        
        if not items:
            return result
        
        try:
            # Create chunks for processing
            chunks = self._create_chunks(items)
            
            # Process with executor
            with executor_class(max_workers=self.config.max_workers) as executor:
                
                # Submit all chunks
                future_to_chunk = {}
                for chunk in chunks:
                    future = executor.submit(self._process_chunk, chunk, processor_func)
                    future_to_chunk[future] = chunk
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(
                    future_to_chunk,
                    timeout=self.config.timeout_per_item * len(items)
                ):
                    try:
                        chunk_result = future.result()
                        
                        # Update overall result
                        result.results.extend(chunk_result['results'])
                        result.processed_items += chunk_result['processed']
                        result.failed_items += chunk_result['failed']
                        result.errors.extend(chunk_result['errors'])
                        result.warnings.extend(chunk_result['warnings'])
                        
                        # Update progress
                        self._processed_items = result.processed_items
                        self._update_progress()
                        
                        # Fail fast if configured
                        if self.config.fail_fast and chunk_result['failed'] > 0:
                            break
                            
                    except concurrent.futures.TimeoutError:
                        result.errors.append("Processing timeout exceeded")
                        if self.config.fail_fast:
                            break
                    except Exception as e:
                        result.errors.append(f"Chunk processing failed: {str(e)}")
                        if self.config.fail_fast:
                            break
        
        except Exception as e:
            result.errors.append(f"Processing failed: {str(e)}")
        
        # Calculate final metrics
        result.processing_time = time.time() - self._start_time
        result.success_rate = (
            (result.processed_items / result.total_items * 100) 
            if result.total_items > 0 else 0.0
        )
        
        return result
    
    def _create_chunks(self, items: List[Any]) -> List[List[Any]]:
        """Create processing chunks from items list"""
        chunks = []
        chunk_size = max(1, self.config.chunk_size)
        
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            chunks.append(chunk)
        
        return chunks
    
    def _process_chunk(
        self,
        chunk: List[Any], 
        processor_func: Callable[[Any], Any]
    ) -> Dict[str, Any]:
        """Process a single chunk of items"""
        chunk_result = {
            'results': [],
            'processed': 0,
            'failed': 0,
            'errors': [],
            'warnings': []
        }
        
        for item in chunk:
            try:
                # Monitor memory usage
                self._check_memory_usage()
                
                # Process item
                item_result = processor_func(item)
                chunk_result['results'].append(item_result)
                chunk_result['processed'] += 1
                
            except MemoryError:
                error_msg = f"Memory limit exceeded processing item: {getattr(item, 'id', 'unknown')}"
                chunk_result['errors'].append(error_msg)
                chunk_result['failed'] += 1
                
                # Try to free memory
                import gc
                gc.collect()
                
            except Exception as e:
                error_msg = f"Failed to process item {getattr(item, 'id', 'unknown')}: {str(e)}"
                chunk_result['errors'].append(error_msg)
                chunk_result['failed'] += 1
        
        return chunk_result
    
    def _check_memory_usage(self) -> None:
        """Check if memory usage is within limits"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.config.memory_limit_mb:
                import gc
                gc.collect()
                
                # Check again after garbage collection
                memory_mb = process.memory_info().rss / 1024 / 1024
                if memory_mb > self.config.memory_limit_mb * 1.2:  # 20% buffer
                    raise MemoryError(f"Memory usage ({memory_mb:.1f} MB) exceeds limit ({self.config.memory_limit_mb} MB)")
        
        except psutil.NoSuchProcess:
            pass  # Process monitoring not available
    
    def _update_progress(self) -> None:
        """Update progress for all registered callbacks"""
        if not self.config.enable_progress_callback:
            return
        
        elapsed_time = time.time() - self._start_time
        
        for callback in self._progress_callbacks:
            try:
                callback(self._processed_items, self._total_items, elapsed_time)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {str(e)}")
    
    def estimate_completion_time(self) -> Optional[float]:
        """Estimate remaining processing time in seconds"""
        if self._processed_items == 0:
            return None
        
        elapsed = time.time() - self._start_time
        rate = self._processed_items / elapsed
        remaining_items = self._total_items - self._processed_items
        
        return remaining_items / rate if rate > 0 else None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        elapsed = time.time() - self._start_time if self._start_time > 0 else 0
        
        return {
            'processed_items': self._processed_items,
            'total_items': self._total_items,
            'completion_percentage': (self._processed_items / self._total_items * 100) if self._total_items > 0 else 0,
            'elapsed_time': elapsed,
            'throughput': self._processed_items / elapsed if elapsed > 0 else 0,
            'estimated_remaining_time': self.estimate_completion_time(),
            'workers': self.config.max_workers,
            'memory_limit_mb': self.config.memory_limit_mb
        }


class BatchProductProcessor:
    """
    Specialized processor for PDP operations on product batches.
    
    Provides high-level methods for common operations:
    - Batch generation
    - Batch auditing  
    - Batch fixing
    - Batch export
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        self.processor = ParallelProcessor(config)
        
        # Import functions (avoid circular imports)
        self._llm_service = None
        self._auditor = None
        self._fixer = None
    
    def _get_llm_service(self):
        """Lazy load LLM service"""
        if self._llm_service is None:
            from llm_service.generator import OllamaLLMService
            self._llm_service = OllamaLLMService()
        return self._llm_service
    
    def _get_auditor(self):
        """Lazy load auditor"""
        if self._auditor is None:
            from models.audit import PDPAuditor
            self._auditor = PDPAuditor()
        return self._auditor
    
    def _get_fixer(self):
        """Lazy load fixer"""
        if self._fixer is None:
            from fix_broken_pdp import PDPFixer
            self._fixer = PDPFixer()
        return self._fixer
    
    def generate_batch(self, products: List[ProductData], output_dir: Path) -> ProcessingResult:
        """Generate PDPs for a batch of products"""
        
        def generate_single(product: ProductData) -> Dict[str, Any]:
            try:
                llm_service = self._get_llm_service()
                
                # Generate PDP
                html_content = llm_service.generate_pdp_html(product)
                
                # Create bundle directory
                bundle_dir = output_dir / "bundles" / product.id
                bundle_dir.mkdir(parents=True, exist_ok=True)
                
                # Save files
                (bundle_dir / "index.html").write_text(html_content, encoding='utf-8')
                (bundle_dir / "sync.json").write_text(
                    product.json(indent=2), encoding='utf-8'
                )
                
                return {
                    'product_id': product.id,
                    'success': True,
                    'bundle_path': str(bundle_dir)
                }
                
            except Exception as e:
                return {
                    'product_id': product.id,
                    'success': False,
                    'error': str(e)
                }
        
        return self.processor.process_batch_multiprocessing(products, generate_single)
    
    def audit_batch(self, product_ids: List[str], bundle_dir: Path) -> ProcessingResult:
        """Audit a batch of existing PDP bundles"""
        
        def audit_single(product_id: str) -> Dict[str, Any]:
            try:
                auditor = self._get_auditor()
                
                # Load bundle
                product_bundle_dir = bundle_dir / product_id
                html_file = product_bundle_dir / "index.html"
                
                if not html_file.exists():
                    return {
                        'product_id': product_id,
                        'success': False,
                        'error': 'HTML file not found'
                    }
                
                html_content = html_file.read_text(encoding='utf-8')
                
                # Run audit
                audit_result = auditor.audit_html(html_content, product_id)
                
                # Save audit result
                audit_file = product_bundle_dir / "audit.json"
                audit_file.write_text(audit_result.json(indent=2), encoding='utf-8')
                
                return {
                    'product_id': product_id,
                    'success': True,
                    'audit_score': audit_result.score,
                    'audit_file': str(audit_file)
                }
                
            except Exception as e:
                return {
                    'product_id': product_id,
                    'success': False,
                    'error': str(e)
                }
        
        return self.processor.process_batch_threading(product_ids, audit_single)
    
    def fix_batch(self, product_ids: List[str], bundle_dir: Path) -> ProcessingResult:
        """Fix a batch of flagged PDP bundles"""
        
        def fix_single(product_id: str) -> Dict[str, Any]:
            try:
                fixer = self._get_fixer()
                
                # Fix the PDP
                fix_result = fixer.fix_product_pdp(product_id, str(bundle_dir))
                
                return {
                    'product_id': product_id,
                    'success': fix_result.success,
                    'before_score': fix_result.before_score,
                    'after_score': fix_result.after_score,
                    'improvement': fix_result.improvement,
                    'error': fix_result.error if not fix_result.success else None
                }
                
            except Exception as e:
                return {
                    'product_id': product_id,
                    'success': False,
                    'error': str(e)
                }
        
        return self.processor.process_batch_multiprocessing(product_ids, fix_single)
    
    def export_batch(self, product_ids: List[str], bundle_dir: Path, format: str = "csv") -> ProcessingResult:
        """Export a batch of PDP bundles"""
        
        def export_single(product_id: str) -> Dict[str, Any]:
            try:
                from export.csv_exporter import StructrCatalogExporter
                
                product_bundle_dir = bundle_dir / product_id
                
                # Load bundle data
                sync_file = product_bundle_dir / "sync.json"
                if not sync_file.exists():
                    return {
                        'product_id': product_id,
                        'success': False,
                        'error': 'Sync file not found'
                    }
                
                # Create export data
                bundle_data = {
                    'product_id': product_id,
                    'bundle_path': str(product_bundle_dir),
                    'exported_at': time.time()
                }
                
                return {
                    'product_id': product_id,
                    'success': True,
                    'export_data': bundle_data
                }
                
            except Exception as e:
                return {
                    'product_id': product_id,
                    'success': False,
                    'error': str(e)
                }
        
        return self.processor.process_batch_threading(product_ids, export_single)