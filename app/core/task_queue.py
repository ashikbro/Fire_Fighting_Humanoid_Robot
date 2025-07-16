"""
Background task queue system for async processing
"""
import asyncio
import queue
import threading
import time
import uuid
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import pickle
import json
from concurrent.futures import ThreadPoolExecutor

from app.core.error_handling import logger

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Task:
    """Task data structure"""
    id: str
    name: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: float = 5.0
    timeout: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO format
        for key in ['created_at', 'started_at', 'completed_at']:
            if data[key]:
                data[key] = data[key].isoformat()
        # Convert enums to values
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        # Remove function reference for serialization
        data.pop('func', None)
        return data

class TaskQueue:
    """Advanced task queue with priority and retry support"""
    
    def __init__(self, max_workers: int = 4, max_queue_size: int = 1000):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        
        # Priority queues for different priority levels
        self.queues = {
            TaskPriority.CRITICAL: queue.PriorityQueue(),
            TaskPriority.HIGH: queue.PriorityQueue(),
            TaskPriority.NORMAL: queue.PriorityQueue(),
            TaskPriority.LOW: queue.PriorityQueue()
        }
        
        # Task storage
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, Task] = {}
        
        # Worker management
        self.workers: List[threading.Thread] = []
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        
        # Statistics
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'retried_tasks': 0,
            'cancelled_tasks': 0
        }
        
        # Lock for thread safety
        self.lock = threading.RLock()
    
    def start(self):
        """Start the task queue workers"""
        if self.running:
            return
        
        self.running = True
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, name=f"TaskWorker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started task queue with {self.max_workers} workers")
    
    def stop(self, timeout: float = 30.0):
        """Stop the task queue workers"""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel all pending tasks
        with self.lock:
            for task in self.tasks.values():
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    self.stats['cancelled_tasks'] += 1
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=timeout / len(self.workers))
        
        # Shutdown executor
        self.executor.shutdown(wait=True, timeout=timeout)
        
        logger.info("Task queue stopped")
    
    def add_task(self, 
                 func: Callable,
                 args: tuple = (),
                 kwargs: dict = None,
                 name: str = None,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 max_retries: int = 3,
                 retry_delay: float = 5.0,
                 timeout: Optional[float] = None) -> str:
        """Add a task to the queue"""
        
        if not self.running:
            raise RuntimeError("Task queue is not running")
        
        # Check queue size
        total_pending = sum(q.qsize() for q in self.queues.values())
        if total_pending >= self.max_queue_size:
            raise RuntimeError("Task queue is full")
        
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout
        )
        
        with self.lock:
            self.tasks[task_id] = task
            # Add to appropriate priority queue
            # Use negative timestamp for priority ordering (older tasks first within same priority)
            priority_value = (-priority.value, -time.time(), task_id)
            self.queues[priority].put((priority_value, task))
            self.stats['total_tasks'] += 1
        
        logger.debug(f"Added task {task_id} ({name}) with priority {priority.name}")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status and information"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                return task.to_dict()
            return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                self.stats['cancelled_tasks'] += 1
                logger.info(f"Cancelled task {task_id}")
                return True
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self.lock:
            queue_sizes = {
                priority.name: q.qsize() 
                for priority, q in self.queues.items()
            }
            
            return {
                'running': self.running,
                'workers': len(self.workers),
                'queue_sizes': queue_sizes,
                'total_pending': sum(queue_sizes.values()),
                'running_tasks': len(self.running_tasks),
                'total_tasks_count': len(self.tasks),
                'statistics': self.stats.copy()
            }
    
    def _worker_loop(self):
        """Main worker loop"""
        logger.info(f"Worker {threading.current_thread().name} started")
        
        while self.running:
            try:
                task = self._get_next_task()
                if task:
                    self._execute_task(task)
                else:
                    time.sleep(0.1)  # Short sleep if no tasks available
                    
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(1)  # Sleep on error to prevent tight loop
        
        logger.info(f"Worker {threading.current_thread().name} stopped")
    
    def _get_next_task(self) -> Optional[Task]:
        """Get next task from queues (priority order)"""
        # Check queues in priority order
        for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
            try:
                _, task = self.queues[priority].get_nowait()
                with self.lock:
                    if task.status == TaskStatus.PENDING:
                        task.status = TaskStatus.RUNNING
                        task.started_at = datetime.now()
                        self.running_tasks[task.id] = task
                        return task
            except queue.Empty:
                continue
        
        return None
    
    def _execute_task(self, task: Task):
        """Execute a task"""
        try:
            logger.debug(f"Executing task {task.id} ({task.name})")
            
            # Execute task with timeout
            future = self.executor.submit(task.func, *task.args, **task.kwargs)
            
            if task.timeout:
                result = future.result(timeout=task.timeout)
            else:
                result = future.result()
            
            # Task completed successfully
            with self.lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = result
                self.running_tasks.pop(task.id, None)
                self.stats['completed_tasks'] += 1
            
            logger.debug(f"Task {task.id} completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task {task.id} failed: {error_msg}")
            
            with self.lock:
                task.error = error_msg
                task.retry_count += 1
                
                # Check if we should retry
                if task.retry_count <= task.max_retries:
                    task.status = TaskStatus.RETRY
                    self.stats['retried_tasks'] += 1
                    
                    # Schedule retry after delay
                    retry_task = threading.Thread(
                        target=self._schedule_retry,
                        args=(task,)
                    )
                    retry_task.daemon = True
                    retry_task.start()
                    
                    logger.info(f"Scheduling retry {task.retry_count}/{task.max_retries} for task {task.id}")
                else:
                    # Max retries exceeded
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    self.stats['failed_tasks'] += 1
                    logger.error(f"Task {task.id} failed permanently after {task.retry_count} retries")
                
                self.running_tasks.pop(task.id, None)
    
    def _schedule_retry(self, task: Task):
        """Schedule task retry after delay"""
        time.sleep(task.retry_delay)
        
        if self.running and task.status == TaskStatus.RETRY:
            with self.lock:
                task.status = TaskStatus.PENDING
                task.started_at = None
                # Re-add to queue
                priority_value = (-task.priority.value, -time.time(), task.id)
                self.queues[task.priority].put((priority_value, task))

# Common task functions for fire fighting robot
def process_sensor_data(sensor_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process sensor data and generate alerts"""
    logger.info(f"Processing sensor data: {sensor_data}")
    
    # Simulate processing time
    time.sleep(0.5)
    
    # Check for fire conditions
    temperature = sensor_data.get('temperature', 0)
    smoke_density = sensor_data.get('smoke_density', 0)
    
    fire_risk = 'low'
    if temperature > 60 or smoke_density > 500:
        fire_risk = 'high'
    elif temperature > 40 or smoke_density > 300:
        fire_risk = 'medium'
    
    return {
        'processed_at': datetime.now().isoformat(),
        'fire_risk': fire_risk,
        'alert_required': fire_risk in ['medium', 'high']
    }

def generate_patrol_route(start_point: tuple, waypoints: List[tuple]) -> List[tuple]:
    """Generate optimized patrol route"""
    logger.info(f"Generating patrol route from {start_point} through {len(waypoints)} waypoints")
    
    # Simulate route calculation
    time.sleep(1.0)
    
    # Simple route: start -> waypoints -> start
    route = [start_point] + waypoints + [start_point]
    
    return route

def send_alert_notification(alert_data: Dict[str, Any]) -> bool:
    """Send alert notification to external systems"""
    logger.info(f"Sending alert notification: {alert_data}")
    
    # Simulate network call
    time.sleep(0.3)
    
    # Simulate occasional failures
    import random
    if random.random() < 0.1:  # 10% failure rate
        raise Exception("Network timeout")
    
    return True

# Global task queue instance
task_queue = TaskQueue(max_workers=4)

# Convenience functions
def enqueue_sensor_processing(sensor_data: Dict[str, Any]) -> str:
    """Enqueue sensor data processing task"""
    return task_queue.add_task(
        process_sensor_data,
        args=(sensor_data,),
        name="process_sensor_data",
        priority=TaskPriority.HIGH
    )

def enqueue_patrol_planning(start_point: tuple, waypoints: List[tuple]) -> str:
    """Enqueue patrol route planning task"""
    return task_queue.add_task(
        generate_patrol_route,
        args=(start_point, waypoints),
        name="generate_patrol_route",
        priority=TaskPriority.NORMAL
    )

def enqueue_alert(alert_data: Dict[str, Any]) -> str:
    """Enqueue alert notification task"""
    return task_queue.add_task(
        send_alert_notification,
        args=(alert_data,),
        name="send_alert",
        priority=TaskPriority.CRITICAL,
        max_retries=5,
        retry_delay=2.0
    )

# Export commonly used items
__all__ = [
    'TaskStatus', 'TaskPriority', 'Task', 'TaskQueue', 'task_queue',
    'enqueue_sensor_processing', 'enqueue_patrol_planning', 'enqueue_alert'
]
 