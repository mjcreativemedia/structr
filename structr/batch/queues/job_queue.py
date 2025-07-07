"""
Job Queue System

Robust job queuing and status tracking for batch operations.
"""

import json
import uuid
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
import queue
import logging

from models.pdp import ProductData


class JobStatus(Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobType(Enum):
    """Types of jobs that can be processed"""
    GENERATE = "generate"
    AUDIT = "audit"
    FIX = "fix"
    EXPORT = "export"
    IMPORT = "import"
    BATCH_GENERATE = "batch_generate"
    BATCH_AUDIT = "batch_audit"
    BATCH_FIX = "batch_fix"


@dataclass
class JobResult:
    """Result of a job execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    output_files: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Job:
    """Represents a single job in the queue"""
    id: str
    job_type: JobType
    input_data: Any
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[JobResult] = None
    priority: int = 0  # Higher number = higher priority
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300  # seconds
    dependencies: List[str] = field(default_factory=list)  # Job IDs that must complete first
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Get job duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_complete(self) -> bool:
        """Check if job is in a terminal state"""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization"""
        data = asdict(self)
        
        # Convert enums to strings
        data['job_type'] = self.job_type.value
        data['status'] = self.status.value
        
        # Convert datetime objects
        for field_name in ['created_at', 'started_at', 'completed_at']:
            if data[field_name]:
                data[field_name] = data[field_name].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary"""
        # Convert enums
        data['job_type'] = JobType(data['job_type'])
        data['status'] = JobStatus(data['status'])
        
        # Convert datetime strings
        for field_name in ['created_at', 'started_at', 'completed_at']:
            if data[field_name]:
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        # Handle result
        if data.get('result'):
            data['result'] = JobResult(**data['result'])
        
        return cls(**data)


class JobQueue:
    """
    Thread-safe job queue with priority, dependencies, and persistence.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None, max_workers: int = 4):
        self.storage_dir = storage_dir or Path("output/jobs")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_workers = max_workers
        self._jobs: Dict[str, Job] = {}
        self._pending_queue = queue.PriorityQueue()
        self._running_jobs: Dict[str, Job] = {}
        self._completed_jobs: Dict[str, Job] = {}
        
        self._lock = threading.RLock()
        self._workers: List[threading.Thread] = []
        self._stop_event = threading.Event()
        self._job_processors: Dict[JobType, Callable] = {}
        
        # Load persisted jobs
        self._load_jobs()
        
        # Start worker threads
        self._start_workers()
    
    def register_processor(self, job_type: JobType, processor: Callable[[Job], JobResult]) -> None:
        """Register a processor function for a job type"""
        self._job_processors[job_type] = processor
    
    def submit_job(self, job_type: JobType, input_data: Any, **kwargs) -> str:
        """Submit a new job to the queue"""
        job = Job(
            id=str(uuid.uuid4()),
            job_type=job_type,
            input_data=input_data,
            **kwargs
        )
        
        with self._lock:
            self._jobs[job.id] = job
            
            # Check dependencies
            if self._check_dependencies(job):
                self._pending_queue.put((-job.priority, job.created_at.timestamp(), job.id))
            
            # Persist job
            self._save_job(job)
        
        return job.id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get all jobs with given status"""
        with self._lock:
            return [job for job in self._jobs.values() if job.status == status]
    
    def get_job_stats(self) -> Dict[str, int]:
        """Get job statistics"""
        with self._lock:
            stats = {}
            for status in JobStatus:
                stats[status.value] = len([j for j in self._jobs.values() if j.status == status])
            stats['total'] = len(self._jobs)
            return stats
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                self._save_job(job)
                return True
            return False
    
    def retry_job(self, job_id: str) -> bool:
        """Retry a failed job"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.FAILED and job.retry_count < job.max_retries:
                job.status = JobStatus.PENDING
                job.retry_count += 1
                job.started_at = None
                job.completed_at = None
                job.result = None
                
                if self._check_dependencies(job):
                    self._pending_queue.put((-job.priority, job.created_at.timestamp(), job.id))
                
                self._save_job(job)
                return True
            return False
    
    def clear_completed_jobs(self, older_than_hours: int = 24) -> int:
        """Clear completed jobs older than specified hours"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        cleared_count = 0
        
        with self._lock:
            jobs_to_remove = []
            
            for job_id, job in self._jobs.items():
                if (job.is_complete and 
                    job.completed_at and 
                    job.completed_at < cutoff):
                    jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self._jobs[job_id]
                job_file = self.storage_dir / f"{job_id}.json"
                if job_file.exists():
                    job_file.unlink()
                cleared_count += 1
        
        return cleared_count
    
    def shutdown(self, timeout: int = 30) -> None:
        """Shutdown the job queue and worker threads"""
        self._stop_event.set()
        
        # Wait for workers to finish
        for worker in self._workers:
            worker.join(timeout=timeout)
        
        # Save all jobs
        with self._lock:
            for job in self._jobs.values():
                self._save_job(job)
    
    def _check_dependencies(self, job: Job) -> bool:
        """Check if job dependencies are satisfied"""
        if not job.dependencies:
            return True
        
        for dep_id in job.dependencies:
            dep_job = self._jobs.get(dep_id)
            if not dep_job or dep_job.status != JobStatus.COMPLETED:
                return False
        
        return True
    
    def _start_workers(self) -> None:
        """Start worker threads"""
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"JobWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
    
    def _worker_loop(self) -> None:
        """Main worker loop"""
        while not self._stop_event.is_set():
            try:
                # Get next job from queue (blocks for up to 1 second)
                try:
                    _, _, job_id = self._pending_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                with self._lock:
                    job = self._jobs.get(job_id)
                    if not job or job.status != JobStatus.PENDING:
                        continue
                    
                    # Check dependencies again
                    if not self._check_dependencies(job):
                        # Re-queue for later
                        self._pending_queue.put((-job.priority, job.created_at.timestamp(), job.id))
                        continue
                    
                    # Mark as running
                    job.status = JobStatus.RUNNING
                    job.started_at = datetime.now()
                    self._running_jobs[job_id] = job
                    self._save_job(job)
                
                # Process job outside the lock
                result = self._process_job(job)
                
                # Update job with result
                with self._lock:
                    job.result = result
                    job.completed_at = datetime.now()
                    job.status = JobStatus.COMPLETED if result.success else JobStatus.FAILED
                    
                    if job_id in self._running_jobs:
                        del self._running_jobs[job_id]
                    
                    self._completed_jobs[job_id] = job
                    self._save_job(job)
                    
                    # Check for dependent jobs
                    self._check_dependent_jobs(job_id)
                
            except Exception as e:
                logging.error(f"Worker error: {str(e)}")
    
    def _process_job(self, job: Job) -> JobResult:
        """Process a single job"""
        start_time = time.time()
        
        try:
            # Check for timeout
            def timeout_handler():
                time.sleep(job.timeout)
                if job.status == JobStatus.RUNNING:
                    job.status = JobStatus.FAILED
            
            timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
            timeout_thread.start()
            
            # Get processor for job type
            processor = self._job_processors.get(job.job_type)
            if not processor:
                return JobResult(
                    success=False,
                    error=f"No processor registered for job type: {job.job_type.value}"
                )
            
            # Execute processor
            result = processor(job)
            result.processing_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            return JobResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _check_dependent_jobs(self, completed_job_id: str) -> None:
        """Check if any pending jobs can now run due to completed dependency"""
        jobs_to_queue = []
        
        for job in self._jobs.values():
            if (job.status == JobStatus.PENDING and 
                completed_job_id in job.dependencies and
                self._check_dependencies(job)):
                jobs_to_queue.append(job)
        
        for job in jobs_to_queue:
            self._pending_queue.put((-job.priority, job.created_at.timestamp(), job.id))
    
    def _save_job(self, job: Job) -> None:
        """Persist job to disk"""
        try:
            job_file = self.storage_dir / f"{job.id}.json"
            with open(job_file, 'w') as f:
                json.dump(job.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Failed to save job {job.id}: {str(e)}")
    
    def _load_jobs(self) -> None:
        """Load persisted jobs from disk"""
        try:
            for job_file in self.storage_dir.glob("*.json"):
                try:
                    with open(job_file, 'r') as f:
                        job_data = json.load(f)
                    
                    job = Job.from_dict(job_data)
                    self._jobs[job.id] = job
                    
                    # Re-queue pending jobs
                    if job.status == JobStatus.PENDING and self._check_dependencies(job):
                        self._pending_queue.put((-job.priority, job.created_at.timestamp(), job.id))
                    elif job.status == JobStatus.RUNNING:
                        # Mark running jobs as failed on restart
                        job.status = JobStatus.FAILED
                        job.completed_at = datetime.now()
                        if not job.result:
                            job.result = JobResult(
                                success=False,
                                error="Job interrupted by system restart"
                            )
                        self._save_job(job)
                
                except Exception as e:
                    logging.error(f"Failed to load job from {job_file}: {str(e)}")
        
        except Exception as e:
            logging.error(f"Failed to load jobs: {str(e)}")


# Job queue singleton instance
_job_queue_instance: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get or create the global job queue instance"""
    global _job_queue_instance
    if _job_queue_instance is None:
        _job_queue_instance = JobQueue()
    return _job_queue_instance


def shutdown_job_queue() -> None:
    """Shutdown the global job queue"""
    global _job_queue_instance
    if _job_queue_instance:
        _job_queue_instance.shutdown()
        _job_queue_instance = None