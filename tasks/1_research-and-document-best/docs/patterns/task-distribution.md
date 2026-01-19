# Task Distribution Patterns

**Strategies for distributing work among multiple agents efficiently**

---

## Overview

Task distribution is critical for multi-agent system performance. Proper distribution ensures work is balanced, agents are utilized effectively, and tasks complete efficiently.

## Core Challenges

1. **Load Balancing**: Distribute work evenly
2. **Dependency Management**: Handle task dependencies
3. **Priority Handling**: Process urgent tasks first
4. **Failure Recovery**: Handle agent failures
5. **Scalability**: Scale to many agents/tasks

---

## 1. Queue-Based Distribution

### Description
Tasks placed in queue, workers pull and execute. Simple and effective.

### Implementation

```python
import asyncio
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    data: Dict[str, Any]
    priority: int = 5
    status: TaskStatus = TaskStatus.PENDING
    assigned_worker: Optional[str] = None
    result: Any = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class TaskQueue:
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.tasks: Dict[str, Task] = {}
        self.results: Dict[str, Any] = {}

    async def add_task(self, task: Task):
        """Add task to queue"""
        await self.queue.put(task)
        self.tasks[task.id] = task

    async def get_task(self) -> Optional[Task]:
        """Get next task from queue"""
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def update_task(self, task_id: str, **kwargs):
        """Update task status"""
        if task_id in self.tasks:
            for key, value in kwargs.items():
                setattr(self.tasks[task_id], key, value)

    def set_result(self, task_id: str, result: Any):
        """Store task result"""
        self.results[task_id] = result

class Worker:
    def __init__(self, worker_id: str, task_queue: TaskQueue,
                 handler: Callable):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.handler = handler
        self.running = False

    async def start(self):
        """Start worker loop"""
        self.running = True
        while self.running:
            task = await self.task_queue.get_task()
            if task is None:
                continue

            await self.process_task(task)

    async def process_task(self, task: Task):
        """Process a task"""
        self.task_queue.update_task(
            task.id,
            status=TaskStatus.PROCESSING,
            assigned_worker=self.worker_id
        )

        try:
            result = await self.handler(task.data)
            self.task_queue.update_task(task.id, status=TaskStatus.COMPLETED)
            self.task_queue.set_result(task.id, result)
        except Exception as e:
            self.task_queue.update_task(
                task.id,
                status=TaskStatus.FAILED,
                result={"error": str(e)}
            )

    def stop(self):
        self.running = False

# Usage
async def task_handler(data: dict) -> dict:
    await asyncio.sleep(0.1)  # Simulate work
    return {"result": f"Processed {data['input']}"}

queue = TaskQueue()

# Create workers
workers = [
    Worker(f"worker_{i}", queue, task_handler)
    for i in range(3)
]

# Add tasks
for i in range(10):
    await queue.add_task(Task(
        id=f"task_{i}",
        data={"input": f"data_{i}"}
    ))

# Start workers
await asyncio.gather(*[w.start() for w in workers])
```

### Benefits
- ✅ Simple and reliable
- ✅ Natural load balancing
- ✅ Easy to implement
- ✅ Fault tolerant (workers can fail)

### Drawbacks
- ❌ No priority by default
- ❌ FIFO only (unless enhanced)
- ❌ No task dependencies

---

## 2. Priority-Based Distribution

### Description
Tasks prioritized, high-priority tasks executed first.

### Implementation

```python
import heapq
from dataclasses import dataclass, field
from typing import Any

@dataclass(order=True)
class PriorityTask:
    priority: int
    created_at: float
    task: Any = field(compare=False)

class PriorityTaskQueue:
    def __init__(self):
        self.queue = []

    def add_task(self, task: Task, priority: int = 5):
        """Add task with priority (1=highest)"""
        priority_task = PriorityTask(
            priority=priority,
            created_at=datetime.now().timestamp(),
            task=task
        )
        heapq.heappush(self.queue, priority_task)

    def get_task(self) -> Optional[Task]:
        """Get highest priority task"""
        if not self.queue:
            return None
        priority_task = heapq.heappop(self.queue)
        return priority_task.task

    def peek(self) -> Optional[Task]:
        """Look at next task without removing"""
        if not self.queue:
            return None
        return self.queue[0].task

# Usage
priority_queue = PriorityTaskQueue()

priority_queue.add_task(Task(id="t1", data={}), priority=5)  # Normal
priority_queue.add_task(Task(id="t2", data={}), priority=1)  # Urgent
priority_queue.add_task(Task(id="t3", data={}), priority=10)  # Low

# t2 will be retrieved first (priority 1)
next_task = priority_queue.get_task()
```

### Benefits
- ✅ Urgent tasks processed first
- ✅ Better responsiveness
- ✅ Flexible prioritization

### Drawbacks
- ❌ Low-priority tasks may starve
- ❌ Requires priority assignment
- ❌ More complex than simple queue

---

## 3. Dynamic Allocation

### Description
Tasks dynamically assigned to best-suited agents based on capabilities, load, and availability.

### Implementation

```python
from typing import Dict, List, Callable
import threading

class WorkerInfo:
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.capabilities: List[str] = []
        self.current_load = 0
        self.max_capacity = 5
        self.is_available = True

class DynamicAllocator:
    def __init__(self):
        self.workers: Dict[str, WorkerInfo] = {}
        self.lock = threading.Lock()

    def register_worker(self, worker_id: str, capabilities: List[str],
                       max_capacity: int = 5):
        """Register a worker with its capabilities"""
        with self.lock:
            self.workers[worker_id] = WorkerInfo(worker_id)
            self.workers[worker_id].capabilities = capabilities
            self.workers[worker_id].max_capacity = max_capacity

    def allocate_task(self, task_type: str, task_data: Dict) -> Optional[str]:
        """Allocate task to best-suited available worker"""
        with self.lock:
            capable_workers = [
                (worker_id, worker)
                for worker_id, worker in self.workers.items()
                if task_type in worker.capabilities
                and worker.current_load < worker.max_capacity
            ]

            if not capable_workers:
                return None

            # Select least loaded capable worker
            worker_id = min(
                capable_workers,
                key=lambda x: x[1].current_load
            )[0]

            # Increment load
            self.workers[worker_id].current_load += 1

            return worker_id

    def release_worker(self, worker_id: str):
        """Release worker (task completed)"""
        with self.lock:
            if worker_id in self.workers:
                self.workers[worker_id].current_load = max(
                    0, self.workers[worker_id].current_load - 1
                )

    def mark_unavailable(self, worker_id: str):
        """Mark worker as unavailable (failed)"""
        with self.lock:
            if worker_id in self.workers:
                self.workers[worker_id].is_available = False

# Usage
allocator = DynamicAllocator()

allocator.register_worker("worker1", ["research", "analysis"], max_capacity=3)
allocator.register_worker("worker2", ["writing", "editing"], max_capacity=2)
allocator.register_worker("worker3", ["research", "writing"], max_capacity=3)

# Allocate tasks
worker1 = allocator.allocate_task("research", {"query": "AI"})
worker2 = allocator.allocate_task("writing", {"topic": "ML"})

# Task completes
allocator.release_worker(worker1)
```

### Benefits
- ✅ Optimal worker selection
- ✅ Load balancing
- ✅ Capability matching
- ✅ Adapts to failures

### Drawbacks
- ❌ More complex logic
- ❌ Requires capability tracking
- ❌ Central allocator can be bottleneck

---

## 4. DAG-Based Execution

### Description
Tasks organized as Directed Acyclic Graph (DAG), dependencies determine execution order.

### Implementation

```python
from typing import Dict, List, Set
from collections import deque

class DAGTask:
    def __init__(self, task_id: str, data: dict, dependencies: List[str] = None):
        self.task_id = task_id
        self.data = data
        self.dependencies = dependencies or []
        self.status = "pending"
        self.result = None

class DAGScheduler:
    def __init__(self):
        self.tasks: Dict[str, DAGTask] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}  # task -> dependents
        self.completed_tasks: Set[str] = set()

    def add_task(self, task: DAGTask):
        """Add task to DAG"""
        self.tasks[task.task_id] = task

        # Build dependency graph
        if task.task_id not in self.dependency_graph:
            self.dependency_graph[task.task_id] = set()

        for dep_id in task.dependencies:
            if dep_id not in self.dependency_graph:
                self.dependency_graph[dep_id] = set()
            self.dependency_graph[dep_id].add(task.task_id)

    def get_ready_tasks(self) -> List[DAGTask]:
        """Get tasks whose dependencies are satisfied"""
        ready = []
        for task_id, task in self.tasks.items():
            if task.status == "pending":
                # Check if all dependencies completed
                if all(dep in self.completed_tasks for dep in task.dependencies):
                    ready.append(task)
        return ready

    def mark_complete(self, task_id: str, result: Any):
        """Mark task as complete"""
        if task_id in self.tasks:
            self.tasks[task_id].status = "completed"
            self.tasks[task_id].result = result
            self.completed_tasks.add(task_id)

    def get_executable_order(self) -> List[List[str]]:
        """Get layers of tasks that can execute in parallel"""
        layers = []
        remaining = set(self.tasks.keys())

        while remaining:
            # Find tasks with all dependencies met
            ready = []
            for task_id in remaining:
                task = self.tasks[task_id]
                if all(dep in self.completed_tasks for dep in task.dependencies):
                    ready.append(task_id)

            if not ready:
                raise Exception("Circular dependency detected")

            layers.append(ready)
            remaining -= set(ready)

        return layers

# Usage
scheduler = DAGScheduler()

# Add tasks with dependencies
scheduler.add_task(DAGTask("t1", {"data": "research"}))
scheduler.add_task(DAGTask("t2", {"data": "analysis"}, dependencies=["t1"]))
scheduler.add_task(DAGTask("t3", {"data": "writing"}, dependencies=["t1"]))
scheduler.add_task(DAGTask("t4", {"data": "editing"}, dependencies=["t2", "t3"]))

# Get execution order
layers = scheduler.get_executable_order()
# [["t1"], ["t2", "t3"], ["t4"]]
# t1 executes first, then t2 and t3 in parallel, then t4
```

### Benefits
- ✅ Explicit dependencies
- ✅ Parallel execution where possible
- ✅ No deadlocks (DAG guaranteed)
- ✅ Visualizable workflow

### Drawbacks
- ❌ Requires planning dependencies
- ❌ Can't handle cycles
- ❌ More complex setup

---

## Best Practices

### ✅ DO:

1. **Monitor queue sizes**
   - Detect backlog
   - Scale workers if needed
   - Alert on growing queues

2. **Handle timeouts**
   - Tasks shouldn't run forever
   - Set reasonable timeouts
   - Requeue or fail timed-out tasks

3. **Track task metrics**
   - Completion time
   - Success/failure rate
   - Queue wait time

4. **Implement retries**
   - Transient failures happen
   - Exponential backoff
   - Limit retry attempts

5. **Load balance**
   - Distribute work evenly
   - Consider worker capabilities
   - Avoid overloading any worker

### ❌ DON'T:

1. **Ignore dependencies**
   - Tasks execute in wrong order
   - Produces incorrect results
   - Hard to debug

2. **Let queues grow unbounded**
   - Memory exhaustion
   - Increased latency
   - System instability

3. **Forget worker health**
   - Workers can fail
   - Need detection and recovery
   - Don't assign to dead workers

4. **Skip task prioritization**
   - Urgent tasks delayed
   - Poor user experience
   - SLA violations

---

**Next**: [State Management](state-management.md) | [Back to README](../README.md)
