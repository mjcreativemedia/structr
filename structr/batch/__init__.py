"""
Batch Processing Package

Enhanced batch processing for scaling Structr to handle
thousands of products efficiently.
"""

from .processors.batch_manager import BatchManager
from .processors.parallel_processor import ParallelProcessor
from .queues.job_queue import JobQueue, Job, JobStatus
from .monitors.progress_monitor import ProgressMonitor

__version__ = "0.1.0"

__all__ = [
    "BatchManager",
    "ParallelProcessor", 
    "JobQueue",
    "Job",
    "JobStatus",
    "ProgressMonitor"
]