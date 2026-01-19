# Custom Multi-Agent Approaches

**Building multi-agent systems from scratch without frameworks - patterns and best practices**

---

## Overview

While frameworks like LangChain, AutoGen, and CrewAI provide powerful abstractions, building a custom multi-agent system from scratch offers maximum flexibility, control, and the ability to tailor the architecture to specific needs. This document covers patterns and best practices for implementing multi-agent systems without relying on existing frameworks.

### Key Benefits of Custom Implementation
- **Complete control**: Every aspect of the system is under your control
- **No framework lock-in**: Avoid dependency on external library evolution
- **Optimized architecture**: Design exactly what you need, nothing more
- **Performance**: Eliminate framework overhead
- **Learning**: Deep understanding of multi-agent systems

### Key Challenges
- **Complexity**: Must implement all coordination, state management, etc.
- **Maintenance**: You're responsible for all code
- **Testing**: Need to build testing infrastructure
- **Debugging**: More difficult without framework tooling
- **Time investment**: Higher upfront development cost

## Core Architecture Patterns

### 1. Event-Driven Architecture

Event-driven systems are highly scalable and decoupled.

```python
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
from collections import defaultdict
import json
import logging

@dataclass
class Event:
    type: str
    data: dict
    source: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.logger = logging.getLogger("EventBus")

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type"""
        self.subscribers[event_type].append(handler)
        self.logger.info(f"Subscribed to {event_type}")

    def publish(self, event: Event):
        """Publish an event to all subscribers"""
        self.logger.info(f"Publishing {event.type} from {event.source}")

        for handler in self.subscribers[event.type]:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Handler failed: {e}")

    async def publish_async(self, event: Event):
        """Publish event asynchronously"""
        tasks = [
            asyncio.create_task(self._safe_async_handler(handler, event))
            for handler in self.subscribers[event.type]
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_async_handler(self, handler: Callable, event: Event):
        try:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            self.logger.error(f"Async handler failed: {e}")

# Example usage
event_bus = EventBus()

def research_agent_handler(event: Event):
    if event.type == "new_task":
        print(f"Research agent processing: {event.data}")
        # Process task...

def writer_agent_handler(event: Event):
    if event.type == "research_complete":
        print(f"Writer agent processing: {event.data}")
        # Write content...

# Subscribe agents
event_bus.subscribe("new_task", research_agent_handler)
event_bus.subscribe("research_complete", writer_agent_handler)

# Publish events
event_bus.publish(Event(
    type="new_task",
    data={"query": "quantum computing"},
    source="user"
))
```

### 2. Actor Model

The Actor model provides isolated agents with message passing.

```python
import asyncio
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import uuid
from datetime import datetime

@dataclass
class Message:
    sender: str
    receiver: str
    content: Any
    message_id: str = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()

class Agent:
    def __init__(self, name: str, event_loop: asyncio.AbstractEventLoop):
        self.name = name
        self.loop = event_loop
        self.mailbox = asyncio.Queue()
        self.running = False
        self.handlers: Dict[str, callable] = {}
        self.context: Dict[str, Any] = {}

    def register_handler(self, message_type: str, handler: callable):
        self.handlers[message_type] = handler

    async def start(self):
        self.running = True
        asyncio.create_task(self._process_messages())

    async def stop(self):
        self.running = False

    async def send(self, message: Message):
        await self.mailbox.put(message)

    async def _process_messages(self):
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.mailbox.get(),
                    timeout=1.0
                )

                handler = self.handlers.get(message.content.get("type"))
                if handler:
                    await handler(message)
                else:
                    print(f"No handler for message: {message}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error processing message: {e}")

class AgentSystem:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.loop = asyncio.get_event_loop()

    def register_agent(self, agent: Agent):
        self.agents[agent.name] = agent

    async def start_all(self):
        for agent in self.agents.values():
            await agent.start()

    async def stop_all(self):
        for agent in self.agents.values():
            await agent.stop()

    async def send_message(self, sender: str, receiver: str, content: Any):
        if receiver not in self.agents:
            raise ValueError(f"Agent {receiver} not found")

        message = Message(
            sender=sender,
            receiver=receiver,
            content=content
        )

        await self.agents[receiver].send(message)

# Example usage
async def main():
    system = AgentSystem()

    # Create agents
    researcher = Agent("researcher", system.loop)
    writer = Agent("writer", system.loop)

    # Register handlers
    async def handle_research(message: Message):
        print(f"Researcher: Processing {message.content}")
        # Do research...
        await system.send_message(
            "researcher",
            "writer",
            {"type": "research_complete", "data": "Research results"}
        )

    async def handle_writing(message: Message):
        if message.content.get("type") == "research_complete":
            print(f"Writer: Writing based on {message.content['data']}")

    researcher.register_handler("research_task", handle_research)
    writer.register_handler("research_complete", handle_writing)

    # Register and start
    system.register_agent(researcher)
    system.register_agent(writer)
    await system.start_all()

    # Send task
    await system.send_message(
        "system",
        "researcher",
        {"type": "research_task", "query": "AI safety"}
    )

    # Let it process
    await asyncio.sleep(2)
    await system.stop_all()

# Run example
# asyncio.run(main())
```

### 3. Pipeline Architecture

Sequential processing through stages.

```python
from typing import List, Callable, Any
from dataclasses import dataclass
import asyncio

@dataclass
class PipelineResult:
    success: bool
    data: Any
    stage: str
    error: str = None

class PipelineStage:
    def __init__(self, name: str, processor: Callable):
        self.name = name
        self.processor = processor
        self.next_stage = None

    async def process(self, data: Any) -> PipelineResult:
        try:
            print(f"Stage {self.name}: Processing...")
            result = await self.processor(data)

            if self.next_stage:
                return await self.next_stage.process(result)
            else:
                return PipelineResult(
                    success=True,
                    data=result,
                    stage=self.name
                )
        except Exception as e:
            return PipelineResult(
                success=False,
                data=data,
                stage=self.name,
                error=str(e)
            )

    def set_next(self, stage: 'PipelineStage'):
        self.next_stage = stage
        return stage  # For chaining

class Pipeline:
    def __init__(self, name: str):
        self.name = name
        self.stages: List[PipelineStage] = []

    def add_stage(self, name: str, processor: Callable) -> PipelineStage:
        stage = PipelineStage(name, processor)
        if self.stages:
            self.stages[-1].set_next(stage)
        self.stages.append(stage)
        return stage

    async def execute(self, initial_data: Any) -> PipelineResult:
        if not self.stages:
            raise ValueError("No stages in pipeline")

        return await self.stages[0].process(initial_data)

# Example usage
async def research_stage(data):
    # Research logic
    await asyncio.sleep(0.1)
    return {"research": f"Research on {data['topic']}", **data}

async def analysis_stage(data):
    # Analysis logic
    await asyncio.sleep(0.1)
    return {"analysis": f"Analysis of {data['research']}", **data}

async def writing_stage(data):
    # Writing logic
    await asyncio.sleep(0.1)
    return {"content": f"Article: {data['analysis']}", **data}

# Create pipeline
pipeline = Pipeline("content_creation")
pipeline.add_stage("research", research_stage)
pipeline.add_stage("analysis", analysis_stage)
pipeline.add_stage("writing", writing_stage)

# Execute
# result = await pipeline.execute({"topic": "AI safety"})
```

## Context Sharing Patterns

### 1. Shared Memory Store

```python
from typing import Any, Dict, Optional
from threading import Lock
import json
import hashlib
from datetime import datetime

class SharedMemoryStore:
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._lock = Lock()
        self._timestamps: Dict[str, datetime] = {}

    def set(self, key: str, value: Any):
        with self._lock:
            self._store[key] = value
            self._timestamps[key] = datetime.now()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._store.get(key, default)

    def delete(self, key: str):
        with self._lock:
            if key in self._store:
                del self._store[key]
                del self._timestamps[key]

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return self._store.copy()

    def get_keys_since(self, since: datetime) -> List[str]:
        with self._lock:
            return [
                key for key, timestamp in self._timestamps.items()
                if timestamp > since
            ]

    def compute_hash(self) -> str:
        """Compute hash of current state for change detection"""
        with self._lock:
            state_str = json.dumps(self._store, sort_keys=True)
            return hashlib.md5(state_str.encode()).hexdigest()

# Usage
memory = SharedMemoryStore()

# Agent 1 writes
memory.set("research_data", {"facts": [...]})

# Agent 2 reads
research_data = memory.get("research_data")
```

### 2. Message Board Pattern

```python
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

@dataclass
class Message:
    id: str
    agent: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

class MessageBoard:
    def __init__(self, default_ttl_seconds: int = 3600):
        self.messages: Dict[str, Message] = {}
        self.default_ttl = timedelta(seconds=default_ttl_seconds)

    def post(self, agent: str, content: str,
             tags: List[str] = None,
             ttl: timedelta = None) -> str:
        """Post a message to the board"""
        msg_id = f"{agent}_{datetime.now().timestamp()}"

        expires_at = None
        if ttl:
            expires_at = datetime.now() + ttl
        else:
            expires_at = datetime.now() + self.default_ttl

        message = Message(
            id=msg_id,
            agent=agent,
            content=content,
            expires_at=expires_at,
            tags=tags or []
        )

        self.messages[msg_id] = message
        return msg_id

    def read(self, agent: str, tags: List[str] = None,
             since: datetime = None) -> List[Message]:
        """Read messages matching criteria"""
        now = datetime.now()
        matched = []

        for msg in self.messages.values():
            # Skip expired messages
            if msg.expires_at and msg.expires_at < now:
                continue

            # Skip if not from agent (unless reading all)
            # if agent != "*" and msg.agent != agent:
            #     continue

            # Filter by tags
            if tags and not any(tag in msg.tags for tag in tags):
                continue

            # Filter by time
            if since and msg.timestamp < since:
                continue

            matched.append(msg)

        return matched

    def cleanup(self):
        """Remove expired messages"""
        now = datetime.now()
        expired = [
            msg_id for msg_id, msg in self.messages.items()
            if msg.expires_at and msg.expires_at < now
        ]
        for msg_id in expired:
            del self.messages[msg_id]
```

### 3. Context Partitioning by Access Level

```python
from enum import Enum
from typing import Dict, List, Any

class AccessLevel(Enum):
    PUBLIC = 0
    AGENT_ONLY = 1
    ADMIN = 2

class PartitionedContextStore:
    def __init__(self):
        self.partitions: Dict[AccessLevel, Dict[str, Any]] = {
            level: {} for level in AccessLevel
        }

    def set(self, key: str, value: Any, level: AccessLevel):
        self.partitions[level][key] = value

    def get(self, key: str, access_levels: List[AccessLevel]) -> Any:
        """Get key, searching through allowed access levels"""
        for level in access_levels:
            if key in self.partitions[level]:
                return self.partitions[level][key]
        return None

    def get_context_for_agent(self, agent_access: List[AccessLevel]) -> Dict[str, Any]:
        """Get all context accessible to agent"""
        context = {}
        for level in agent_access:
            context.update(self.partitions[level])
        return context

# Usage
context = PartitionedContextStore()

# Public information
context.set("project_name", "Sleepless Agent", AccessLevel.PUBLIC)

# Agent-specific information
context.set("api_key", "sk-...", AccessLevel.AGENT_ONLY)

# Admin-only information
context.set("admin_token", "xyz123", AccessLevel.ADMIN)

# Regular agent can only see public + agent-only
regular_access = [AccessLevel.PUBLIC, AccessLevel.AGENT_ONLY]
regular_context = context.get_context_for_agent(regular_access)
# {"project_name": "Sleepless Agent", "api_key": "sk-..."}

# Admin can see everything
admin_access = [AccessLevel.PUBLIC, AccessLevel.AGENT_ONLY, AccessLevel.ADMIN]
admin_context = context.get_context_for_agent(admin_access)
```

## Task Distribution Patterns

### 1. Work Queue with Priority

```python
import heapq
from typing import Callable, Any, Dict
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

@dataclass(order=True)
class Task:
    priority: int
    created_at: datetime
    task_id: str
    data: Dict[str, Any] = field(compare=False)
    handler: Callable = field(compare=False, default=None)

class TaskQueue:
    def __init__(self):
        self.queue: list = []
        self.tasks: Dict[str, Task] = {}
        self.results: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def add_task(self, task_id: str, data: Dict,
                      priority: int = 5,
                      handler: Callable = None):
        task = Task(
            priority=priority,
            created_at=datetime.now(),
            task_id=task_id,
            data=data,
            handler=handler
        )

        async with self._lock:
            heapq.heappush(self.queue, task)
            self.tasks[task_id] = task

    async def get_next_task(self) -> Task:
        async with self._lock:
            if not self.queue:
                return None
            return heapq.heappop(self.queue)

    async def set_result(self, task_id: str, result: Any):
        async with self._lock:
            self.results[task_id] = result

    async def get_result(self, task_id: str) -> Any:
        async with self._lock:
            return self.results.get(task_id)

class TaskExecutor:
    def __init__(self, task_queue: TaskQueue, executor_id: str):
        self.queue = task_queue
        self.executor_id = executor_id
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            task = await self.queue.get_next_task()
            if task is None:
                await asyncio.sleep(0.1)
                continue

            print(f"Executor {self.executor_id} processing task {task.task_id}")

            try:
                if task.handler:
                    result = await task.handler(task.data)
                else:
                    result = f"Processed by {self.executor_id}"

                await self.queue.set_result(task.task_id, result)

            except Exception as e:
                await self.queue.set_result(task.task_id, {"error": str(e)})

    def stop(self):
        self.running = False

# Usage
async def example_handler(data: dict) -> str:
    await asyncio.sleep(0.1)  # Simulate work
    return f"Processed: {data['input']}"

queue = TaskQueue()

# Add tasks
await queue.add_task("task1", {"input": "data1"}, priority=1, handler=example_handler)
await queue.add_task("task2", {"input": "data2"}, priority=5, handler=example_handler)

# Start executors
executor1 = TaskExecutor(queue, "exec1")
executor2 = TaskExecutor(queue, "exec2")

await asyncio.gather(
    executor1.start(),
    executor2.start()
)
```

### 2. Dynamic Task Allocation

```python
from typing import Dict, List, Callable
import random

class TaskAllocator:
    def __init__(self):
        self.workers: Dict[str, Worker] = {}
        self.worker_capabilities: Dict[str, List[str]] = {}

    def register_worker(self, worker_id: str, capabilities: List[str]):
        self.worker_capabilities[worker_id] = capabilities
        self.workers[worker_id] = Worker(worker_id)

    def allocate(self, task_type: str, task_data: dict) -> str:
        """Allocate task to best worker"""
        capable_workers = [
            worker_id for worker_id, caps in self.worker_capabilities.items()
            if task_type in caps
        ]

        if not capable_workers:
            raise ValueError(f"No worker capable of {task_type}")

        # Select least loaded capable worker
        selected = min(
            capable_workers,
            key=lambda w: self.workers[w].current_load
        )

        self.workers[selected].current_load += 1
        return selected

    def complete_task(self, worker_id: str):
        if worker_id in self.workers:
            self.workers[worker_id].current_load = max(
                0, self.workers[worker_id].current_load - 1
            )

class Worker:
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.current_load = 0
        self.tasks_completed = 0

# Usage
allocator = TaskAllocator()
allocator.register_worker("worker1", ["research", "analysis"])
allocator.register_worker("worker2", ["writing", "editing"])
allocator.register_worker("worker3", ["research", "writing"])

# Allocate tasks
worker1 = allocator.allocate("research", {"query": "AI"})
worker2 = allocator.allocate("writing", {"topic": "ML"})

# Complete tasks
allocator.complete_task(worker1)
allocator.complete_task(worker2)
```

## State Management

### 1. Distributed State with etcd-style Key-Value Store

```python
import json
import asyncio
from typing import Any, Dict, Optional, List
from datetime import datetime

class DistributedStateStore:
    """In-memory implementation - could use etcd, Consul, etc."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._watchers: Dict[str, List[callable]] = {}
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any):
        async with self._lock:
            old_value = self._store.get(key)
            self._store[key] = value

            # Trigger watchers
            if key in self._watchers:
                for watcher in self._watchers[key]:
                    asyncio.create_task(watcher(key, old_value, value))

    async def get(self, key: str, default: Any = None) -> Any:
        async with self._lock:
            return self._store.get(key, default)

    async def delete(self, key: str):
        async with self._lock:
            if key in self._store:
                del self._store[key]

    async def watch(self, key: str, callback: callable):
        """Watch for changes to a key"""
        async with self._lock:
            if key not in self._watchers:
                self._watchers[key] = []
            self._watchers[key].append(callback)

    async def get_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all keys with prefix"""
        async with self._lock:
            return {
                k: v for k, v in self._store.items()
                if k.startswith(prefix)
            }

    async def transaction(self, operations: List[dict]):
        """Execute multiple operations atomically"""
        async with self._lock:
            results = []
            for op in operations:
                if op["type"] == "set":
                    self._store[op["key"]] = op["value"]
                elif op["type"] == "delete":
                    if op["key"] in self._store:
                        del self._store[op["key"]]
                elif op["type"] == "get":
                    results.append(self._store.get(op["key"]))
            return results
```

### 2. Event Sourcing

```python
from typing import List, Any, Callable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Event:
    event_id: str
    event_type: str
    data: dict
    timestamp: datetime

class EventStore:
    def __init__(self):
        self.events: List[Event] = []
        self.subscribers: List[Callable] = []

    def append(self, event_type: str, data: dict) -> Event:
        event = Event(
            event_id=f"{event_type}_{len(self.events)}_{datetime.now().timestamp()}",
            event_type=event_type,
            data=data,
            timestamp=datetime.now()
        )
        self.events.append(event)

        # Notify subscribers
        for sub in self.subscribers:
            sub(event)

        return event

    def subscribe(self, callback: Callable):
        self.subscribers.append(callback)

    def get_events_since(self, event_id: str) -> List[Event]:
        """Get all events after given event ID"""
        try:
            idx = next(i for i, e in enumerate(self.events) if e.event_id == event_id)
            return self.events[idx + 1:]
        except StopIteration:
            return []

    def replay(self, event_type: str = None) -> List[Event]:
        """Replay events, optionally filtered by type"""
        if event_type:
            return [e for e in self.events if e.event_type == event_type]
        return self.events

# Usage
event_store = EventStore()

def handle_event(event: Event):
    print(f"Event: {event.event_type} - {event.data}")

event_store.subscribe(handle_event)

# Append events
event_store.append("agent_created", {"agent_id": "agent1", "type": "researcher"})
event_store.append("task_assigned", {"agent_id": "agent1", "task_id": "task1"})
```

## 24/7 Operation Patterns

### 1. Supervisor Pattern

```python
import asyncio
from typing import List
from dataclasses import dataclass

@dataclass
class AgentHealth:
    agent_id: str
    is_alive: bool
    last_heartbeat: datetime
    restart_count: int = 0

class Supervisor:
    def __init__(self, heartbeat_interval=30):
        self.agents: Dict[str, AgentHealth] = {}
        self.heartbeat_interval = heartbeat_interval
        self.running = False

    async def register_agent(self, agent_id: str, agent_factory: callable):
        self.agents[agent_id] = AgentHealth(
            agent_id=agent_id,
            is_alive=False,
            last_heartbeat=datetime.fromtimestamp(0),
            restart_count=0
        )
        self.agent_factories[agent_id] = agent_factory

    async def monitor(self):
        """Monitor agent health and restart if needed"""
        self.running = True
        while self.running:
            for agent_id, health in self.agents.items():
                time_since_heartbeat = datetime.now() - health.last_heartbeat

                if time_since_heartbeat.total_seconds() > self.heartbeat_interval * 2:
                    print(f"Agent {agent_id} appears dead, restarting...")
                    await self._restart_agent(agent_id)

            await asyncio.sleep(self.heartbeat_interval)

    async def heartbeat(self, agent_id: str):
        """Agents call this to report they're alive"""
        if agent_id in self.agents:
            self.agents[agent_id].last_heartbeat = datetime.now()
            self.agents[agent_id].is_alive = True

    async def _restart_agent(self, agent_id: str):
        """Restart a dead agent"""
        health = self.agents[agent_id]
        health.restart_count += 1
        health.is_alive = False

        if agent_id in self.agent_factories:
            new_agent = self.agent_factories[agent_id]()
            await new_agent.start()
```

### 2. Circuit Breaker

```python
from enum import Enum
from datetime import datetime, timedelta
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
        self.lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        async with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout)
        )

    async def _on_success(self):
        async with self.lock:
            self.failures = 0
            self.state = CircuitState.CLOSED

    async def _on_failure(self):
        async with self.lock:
            self.failures += 1
            self.last_failure_time = datetime.now()
            if self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
```

## Budget Management

### 1. Token Budget Tracker

```python
from typing import Dict
from dataclasses import dataclass
import threading

@dataclass
class AgentBudget:
    agent_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0

class BudgetManager:
    def __init__(self, total_budget: float,
                 input_cost_per_1k: float = 0.0015,
                 output_cost_per_1k: float = 0.002):
        self.total_budget = total_budget
        self.input_cost = input_cost_per_1k
        self.output_cost = output_cost_per_1k
        self.budgets: Dict[str, AgentBudget] = {}
        self._lock = threading.Lock()

    def record_usage(self, agent_id: str, input_tokens: int, output_tokens: int):
        with self._lock:
            if agent_id not in self.budgets:
                self.budgets[agent_id] = AgentBudget(agent_id=agent_id)

            budget = self.budgets[agent_id]
            budget.input_tokens += input_tokens
            budget.output_tokens += output_tokens

            cost = (
                (input_tokens / 1000) * self.input_cost +
                (output_tokens / 1000) * self.output_cost
            )
            budget.total_cost += cost
            budget.request_count += 1

    def can_afford(self, agent_id: str, estimated_tokens: int) -> bool:
        with self._lock:
            spent = sum(b.total_cost for b in self.budgets.values())
            estimated_cost = (estimated_tokens / 1000) * self.input_cost
            return (spent + estimated_cost) <= self.total_budget

    def get_remaining_budget(self) -> float:
        with self._lock:
            spent = sum(b.total_cost for b in self.budgets.values())
            return self.total_budget - spent

    def get_agent_budgets(self) -> Dict[str, dict]:
        with self._lock:
            return {
                agent_id: {
                    "input_tokens": b.input_tokens,
                    "output_tokens": b.output_tokens,
                    "total_cost": b.total_cost,
                    "requests": b.request_count
                }
                for agent_id, b in self.budgets.items()
            }
```

## Best Practices

### ✅ DO:

1. **Start simple, evolve as needed**
   - Begin with basic message passing
   - Add complexity only when justified
   - Iterate on architecture based on real needs

2. **Use proven patterns**
   - Event-driven architecture for scalability
   - Actor model for isolation
   - Pipeline for sequential workflows

3. **Implement observability from day one**
   - Comprehensive logging
   - Metrics and monitoring
   - Distributed tracing

4. **Budget aggressively**
   - Track token usage per agent
   - Implement spending limits
   - Alert on budget overruns

5. **Plan for failure**
   - Circuit breakers for external calls
   - Timeouts for all operations
   - Graceful degradation

### ❌ DON'T:

1. **Over-engineer**
   - Don't build framework-level features you don't need
   - Avoid premature optimization
   - Keep it simple until proven otherwise

2. **Ignore concurrency**
   - Multi-agent systems are inherently concurrent
   - Use proper locking and async patterns
   - Test for race conditions

3. **Skip testing**
   - Unit test individual agents
   - Integration test communication
   - Load test for scale

4. **Forget observability**
   - Log all agent interactions
   - Track performance metrics
   - Monitor resource usage

5. **Assume reliability**
   - Network calls fail
   - Agents crash
   - Design for chaos

## When to Choose Custom Implementation

**Choose custom if:**
- You need maximum flexibility and control
- Your requirements are unique
- You have time to invest in architecture
- You want to avoid framework lock-in
- Performance is critical

**Avoid custom if:**
- You need to ship quickly
- Your team lacks experience
- Requirements are standard
- You want community support
- Frameworks meet your needs

## Resources

- [The Actor Model](https://en.wikipedia.org/wiki/Actor_model)
- [Event-Driven Architecture](https://en.wikipedia.org/wiki/Event-driven_architecture)
- [Multi-Agent Systems Research](https://www.researchgate.net/topic/Multi-Agent-Systems)
- [Python Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

---

**Next**: [Coordination Patterns](../patterns/coordination.md) | [Back to README](../README.md)
