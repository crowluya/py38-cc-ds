# LangChain Multi-Agent Framework

**Comprehensive guide to LangChain's multi-agent architecture, patterns, and best practices**

---

## Overview

LangChain is one of the most mature and widely-adopted frameworks for building LLM applications. Its multi-agent capabilities have evolved significantly with the introduction of **LangGraph**, which provides a stateful, graph-based approach to agent orchestration.

### Key Strengths
- **Mature ecosystem**: Extensive documentation, large community, battle-tested in production
- **LangGraph**: Stateful agent orchestration with cyclic flows
- **Rich integrations**: 50+ tools and integrations (vector stores, APIs, databases)
- **Flexibility**: Supports both simple chains and complex multi-agent systems
- **Type safety**: Good TypeScript/Python support with Pydantic models

### Key Weaknesses
- **Complexity**: Steep learning curve for advanced patterns
- **Overhead**: Can be heavy for simple use cases
- **State management**: LangGraph adds complexity for stateful workflows
- **Cost**: Multiple agents = multiple LLM calls = multiplied costs

## Architecture Patterns

### 1. LangGraph: Stateful Agent Orchestration

LangGraph is LangChain's recommended approach for multi-agent systems. It uses a graph-based architecture where agents are nodes and communication patterns are edges.

```python
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from typing import TypedDict, Annotated, Sequence
import operator

# Define the state that flows between agents
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    context: dict

# Define individual agents
def research_agent(state: AgentState) -> AgentState:
    """Agent that researches and gathers information"""
    messages = state["messages"]
    last_message = messages[-1]

    # Process with LLM
    response = llm.invoke([
        SystemMessage(content="You are a research specialist. Gather facts and information."),
        last_message
    ])

    return {
        "messages": [response],
        "next_agent": "writer"
    }

def writer_agent(state: AgentState) -> AgentState:
    """Agent that writes and formats content"""
    messages = state["messages"]
    # Use all previous context
    response = llm.invoke([
        SystemMessage(content="You are a writer. Create well-structured content."),
        *messages
    ])

    return {
        "messages": [response],
        "next_agent": END
    }

# Build the graph
workflow = StateGraph(AgentState)

# Add nodes (agents)
workflow.add_node("researcher", research_agent)
workflow.add_node("writer", writer_agent)

# Add edges (communication flow)
workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)

# Compile the graph
app = workflow.compile()

# Execute
result = app.invoke({
    "messages": [HumanMessage(content="Write about quantum computing")],
    "next_agent": "researcher",
    "context": {}
})
```

**When to use LangGraph:**
- Complex, multi-step workflows
- Stateful conversations with memory
- Cyclic workflows (agents can loop back)
- Production systems requiring reliability

### 2. Agent Teams: Specialized Cooperation

LangChain supports teams of specialized agents with shared communication channels.

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate

# Define specialized tools
def search_tool(query: str) -> str:
    """Search for information"""
    return f"Search results for: {query}"

def calculator_tool(expression: str) -> str:
    """Calculate mathematical expressions"""
    return str(eval(expression))

tools = [
    Tool(name="search", func=search_tool,
         description="Search for current information"),
    Tool(name="calculator", func=calculator_tool,
         description="Calculate mathematical expressions")
]

# Create specialized agents
research_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a research specialist. Use search tools to gather information."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

research_agent = create_openai_tools_agent(llm, tools, research_prompt)
research_executor = AgentExecutor(
    agent=research_agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

# Writer agent (different tools)
writer_tools = [
    Tool(name="file_writer", func=lambda x: f"Wrote: {x}",
         description="Write content to files")
]

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a writer. Create and format content."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

writer_agent = create_openai_tools_agent(llm, writer_tools, writer_prompt)
writer_executor = AgentExecutor(
    agent=writer_agent,
    tools=writer_tools,
    verbose=True
)

# Orchestrate the team
async def run_team(task: str):
    # Research phase
    research_result = await research_executor.ainvoke({"input": task})

    # Writing phase
    write_result = await writer_executor.ainvoke({
        "input": f"Write about: {research_result['output']}"
    })

    return write_result
```

### 3. Hierarchical Agent Supervision

Pattern for having a supervisor agent coordinate worker agents.

```python
from langchain.output_parsers import CommaSeparatedListOutputParser
from langchain_core.prompts import PromptTemplate

# Supervisor that routes tasks
supervisor_prompt = PromptTemplate(
    template="""Given the following task, determine which agent should handle it.

Available agents:
- researcher: For gathering information and facts
- writer: For creating and formatting content
- analyst: For analyzing data and providing insights

Task: {task}

Respond with just the agent name:""",
    input_variables=["task"]
)

supervisor_chain = supervisor_prompt | llm | StrOutputParser()

# Worker agents (same as before)
workers = {
    "researcher": research_executor,
    "writer": writer_executor,
    "analyst": analyst_executor
}

# Supervisor loop
def supervised_workflow(task: str, max_iterations: int = 5):
    context = {"task": task, "history": []}

    for i in range(max_iterations):
        # Supervisor decides next action
        next_agent = supervisor_chain.invoke({"task": task})

        if next_agent not in workers:
            break

        # Execute selected agent
        result = workers[next_agent].invoke({"input": task})

        context["history"].append({
            "agent": next_agent,
            "result": result["output"]
        })

        # Check if task is complete
        if "complete" in result["output"].lower():
            break

    return context
```

## Context Sharing Patterns

### 1. Shared Message History

LangChain's `BaseMessage` classes enable rich context sharing.

```python
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    BaseMessage
)

class SharedContext:
    def __init__(self):
        self.messages: list[BaseMessage] = []
        self.shared_data: dict = {}

    def add_message(self, message: BaseMessage):
        self.messages.append(message)

    def get_context_for_agent(self, agent_name: str) -> list[BaseMessage]:
        """Filter and prepare context for specific agent"""
        # Add agent-specific system prompt
        system_prompts = {
            "researcher": "You are a researcher. Focus on facts.",
            "writer": "You are a writer. Focus on clarity.",
        }

        context = [SystemMessage(content=system_prompts[agent_name])]
        context.extend(self.messages[-10:])  # Last 10 messages
        return context

# Usage
context = SharedContext()
context.add_message(HumanMessage(content="Initial task"))

# Agent 1
agent1_context = context.get_context_for_agent("researcher")
response1 = llm.invoke(agent1_context)
context.add_message(response1)

# Agent 2 (now has Agent 1's context)
agent2_context = context.get_context_for_agent("writer")
response2 = llm.invoke(agent2_context)
```

### 2. Checkpoint-Based State (LangGraph)

LangGraph provides built-in state persistence with checkpoints.

```python
from langgraph.checkpoint.memory import MemorySaver

# Add checkpointing to workflow
memory = MemorySaver()
app = workflow.compile(checkpointer=memory, interrupt_before=["writer"])

# Run with thread_id for persistence
config = {"configurable": {"thread_id": "conversation-1"}}
result = app.invoke(initial_state, config)

# Resume later with same thread_id
result = app.invoke(None, config)
```

### 3. Context Partitioning

For sensitive information, partition context by access level.

```python
from enum import Enum
from typing import Dict, List

class AccessLevel(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"

class PartitionedContext:
    def __init__(self):
        self.partitions: Dict[AccessLevel, List[BaseMessage]] = {
            AccessLevel.PUBLIC: [],
            AccessLevel.INTERNAL: [],
            AccessLevel.RESTRICTED: [],
        }

    def add_message(self, message: BaseMessage, level: AccessLevel):
        self.partitions[level].append(message)

    def get_context(self, agent_access: List[AccessLevel]) -> List[BaseMessage]:
        """Get messages based on agent's access level"""
        context = []
        for level in agent_access:
            context.extend(self.partitions[level])
        return context

# Usage
context = PartitionedContext()
context.add_message(
    HumanMessage(content="Public info"),
    AccessLevel.PUBLIC
)
context.add_message(
    HumanMessage(content="API_KEY=sk-..."),
    AccessLevel.RESTRICTED
)

# Public agent only sees public info
public_context = context.get_context([AccessLevel.PUBLIC])

# Admin agent sees everything
admin_context = context.get_context([
    AccessLevel.PUBLIC,
    AccessLevel.INTERNAL,
    AccessLevel.RESTRICTED
])
```

## Task Distribution Patterns

### 1. Queue-Based Distribution

```python
from queue import Queue
from threading import Thread
import time

class TaskQueue:
    def __init__(self):
        self.queue = Queue()
        self.results = {}
        self.workers = []

    def add_task(self, task_id: str, task_data: dict):
        self.queue.put((task_id, task_data))

    def worker(self, agent, agent_name: str):
        while True:
            task_id, task_data = self.queue.get()

            try:
                result = agent.invoke(task_data)
                self.results[task_id] = {
                    "status": "complete",
                    "result": result,
                    "agent": agent_name
                }
            except Exception as e:
                self.results[task_id] = {
                    "status": "failed",
                    "error": str(e),
                    "agent": agent_name
                }
            finally:
                self.queue.task_done()

    def start_workers(self, agents: dict):
        for name, agent in agents.items():
            thread = Thread(
                target=self.worker,
                args=(agent, name),
                daemon=True
            )
            thread.start()
            self.workers.append(thread)

# Usage
task_queue = TaskQueue()
task_queue.start_workers({
    "agent1": agent1,
    "agent2": agent2,
    "agent3": agent3
})

# Add tasks
task_queue.add_task("task1", {"input": "Research topic A"})
task_queue.add_task("task2", {"input": "Write about topic B"})

# Wait for completion
task_queue.queue.join()
```

### 2. Priority-Based Scheduling

```python
import heapq
from dataclasses import dataclass
from datetime import datetime

@dataclass(order=True)
class PrioritizedTask:
    priority: int
    timestamp: datetime
    task_id: str
    task_data: dict

class PriorityTaskQueue:
    def __init__(self):
        self.queue = []

    def add_task(self, task_id: str, task_data: dict, priority: int):
        task = PrioritizedTask(
            priority=priority,
            timestamp=datetime.now(),
            task_id=task_id,
            task_data=task_data
        )
        heapq.heappush(self.queue, task)

    def get_next_task(self) -> PrioritizedTask:
        return heapq.heappop(self.queue)

# Usage
priority_queue = PriorityTaskQueue()

# High priority task
priority_queue.add_task("urgent", {...}, priority=1)

# Low priority task
priority_queue.add_task("normal", {...}, priority=10)
```

## State Management

### 1. Centralized State Store

```python
from typing import Any, Dict
from threading import Lock

class StateStore:
    def __init__(self):
        self._state = {}
        self._lock = Lock()

    def get(self, key: str, default=None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any):
        with self._lock:
            self._state[key] = value

    def update(self, updates: Dict[str, Any]):
        with self._lock:
            self._state.update(updates)

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return self._state.copy()

# Usage
state_store = StateStore()

# Agent 1 writes state
state_store.set("research_data", {...})

# Agent 2 reads state
research_data = state_store.get("research_data")
```

### 2. Distributed State with Redis

```python
import redis
import json
from typing import Any

class RedisStateStore:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.client = redis.from_url(redis_url)

    def get(self, key: str) -> Any:
        value = self.client.get(key)
        if value:
            return json.loads(value)
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        serialized = json.dumps(value)
        if ttl:
            self.client.setex(key, ttl, serialized)
        else:
            self.client.set(key, serialized)

    def delete(self, key: str):
        self.client.delete(key)

    def exists(self, key: str) -> bool:
        return self.client.exists(key) > 0
```

## 24/7 Operation Considerations

### 1. Error Handling and Retries

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientAgent:
    def __init__(self, agent, max_retries=3):
        self.agent = agent
        self.max_retries = max_retries

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def invoke_with_retry(self, inputs: dict) -> dict:
        try:
            return self.agent.invoke(inputs)
        except Exception as e:
            print(f"Agent failed: {e}, retrying...")
            raise

    def safe_invoke(self, inputs: dict) -> dict:
        """Invoke with fallback on final failure"""
        try:
            return self.invoke_with_retry(inputs)
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed",
                "fallback": "Default response"
            }
```

### 2. Circuit Breaker Pattern

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout)
        )

    def _on_success(self):
        self.failures = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.now()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

### 3. Health Monitoring

```python
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class AgentHealth:
    agent_name: str
    is_healthy: bool
    last_success: datetime
    last_failure: datetime
    failure_count: int
    avg_latency_ms: float

class HealthMonitor:
    def __init__(self):
        self.health_status = {}

    def record_success(self, agent_name: str, latency_ms: float):
        if agent_name not in self.health_status:
            self.health_status[agent_name] = AgentHealth(
                agent_name=agent_name,
                is_healthy=True,
                last_success=datetime.now(),
                last_failure=None,
                failure_count=0,
                avg_latency_ms=latency_ms
            )
        else:
            health = self.health_status[agent_name]
            health.last_success = datetime.now()
            health.failure_count = 0
            health.is_healthy = True
            # Update moving average
            health.avg_latency_ms = (health.avg_latency_ms * 0.9 + latency_ms * 0.1)

    def record_failure(self, agent_name: str):
        if agent_name not in self.health_status:
            self.health_status[agent_name] = AgentHealth(
                agent_name=agent_name,
                is_healthy=False,
                last_success=None,
                last_failure=datetime.now(),
                failure_count=1,
                avg_latency_ms=0
            )
        else:
            health = self.health_status[agent_name]
            health.last_failure = datetime.now()
            health.failure_count += 1
            if health.failure_count > 5:
                health.is_healthy = False

    def is_healthy(self, agent_name: str) -> bool:
        health = self.health_status.get(agent_name)
        return health.is_healthy if health else True
```

## Budget Management

### 1. Token Budget Tracking

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class BudgetTracker:
    agent_name: str
    total_tokens: int = 0
    total_cost: float = 0.0
    request_count: int = 0

class BudgetManager:
    def __init__(self, total_budget: float, cost_per_1k_tokens: float = 0.002):
        self.total_budget = total_budget
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.trackers: Dict[str, BudgetTracker] = {}
        self.global_spent = 0.0

    def get_tracker(self, agent_name: str) -> BudgetTracker:
        if agent_name not in self.trackers:
            self.trackers[agent_name] = BudgetTracker(agent_name=agent_name)
        return self.trackers[agent_name]

    def record_usage(self, agent_name: str, tokens: int):
        cost = (tokens / 1000) * self.cost_per_1k_tokens

        tracker = self.get_tracker(agent_name)
        tracker.total_tokens += tokens
        tracker.total_cost += cost
        tracker.request_count += 1

        self.global_spent += cost

    def can_afford(self, estimated_tokens: int) -> bool:
        estimated_cost = (estimated_tokens / 1000) * self.cost_per_1k_tokens
        return (self.global_spent + estimated_cost) <= self.total_budget

    def get_remaining_budget(self) -> float:
        return self.total_budget - self.global_spent

    def get_agent_budgets(self) -> Dict[str, float]:
        return {
            name: tracker.total_cost
            for name, tracker in self.trackers.items()
        }
```

### 2. Budget-Constrained Agent Wrapper

```python
class BudgetConstrainedAgent:
    def __init__(self, agent, agent_name: str, budget_manager: BudgetManager):
        self.agent = agent
        self.agent_name = agent_name
        self.budget_manager = budget_manager

    def invoke(self, inputs: dict) -> dict:
        # Estimate token usage (rough estimate)
        estimated_tokens = len(str(inputs)) // 4  # Rough estimate

        if not self.budget_manager.can_afford(estimated_tokens):
            raise Exception(f"Budget exceeded for agent {self.agent_name}")

        # Execute
        result = self.agent.invoke(inputs)

        # Track actual usage (if available from response metadata)
        actual_tokens = result.get("token_usage", estimated_tokens)
        self.budget_manager.record_usage(self.agent_name, actual_tokens)

        return result

    def get_budget_status(self) -> dict:
        tracker = self.budget_manager.get_tracker(self.agent_name)
        return {
            "agent": self.agent_name,
            "spent": tracker.total_cost,
            "tokens": tracker.total_tokens,
            "requests": tracker.request_count,
            "remaining": self.budget_manager.get_remaining_budget()
        }
```

## Best Practices

### ✅ DO:

1. **Use LangGraph for production systems**
   - Provides state persistence and checkpointing
   - Better error handling and recovery
   - More predictable behavior

2. **Implement proper error boundaries**
   - Each agent should have its own error handling
   - Use circuit breakers for external service calls
   - Log all failures for debugging

3. **Budget aggressively**
   - Assume 2-3x estimated token usage
   - Set per-agent and global limits
   - Monitor spending in real-time

4. **Context management**
   - Limit context window per agent (last N messages)
   - Sanitize sensitive information before sharing
   - Use checkpoints for long conversations

5. **Testing**
   - Unit test individual agents
   - Integration test agent workflows
   - Load test for concurrency issues

### ❌ DON'T:

1. **Share raw context between all agents**
   - Leads to context bleed
   - Wastes tokens on irrelevant information
   - Security risk for sensitive data

2. **Ignore token costs**
   - Multi-agent systems multiply costs
   - Always track and budget
   - Implement caching where possible

3. **Hard-code agent roles**
   - Use configuration for flexibility
   - Allow dynamic agent addition/removal
   - Make agents pluggable

4. **Skip observability**
   - Log all agent communications
   - Track performance metrics
   - Monitor budget spending

5. **Assume agents always succeed**
   - Implement timeouts
   - Have fallback strategies
   - Graceful degradation

## Comparison with Alternatives

| Feature | LangChain | AutoGen | CrewAI | Custom |
|---------|-----------|---------|--------|--------|
| Maturity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Flexibility | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Learning Curve | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 24/7 Ready | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Community | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | N/A |

## When to Choose LangChain

**Choose LangChain if:**
- You need a mature, production-ready framework
- Your workflow benefits from stateful orchestration (LangGraph)
- You want extensive tool integrations out of the box
- You have a team that can learn the framework
- You need enterprise features (monitoring, tracing, etc.)

**Avoid LangChain if:**
- Your use case is simple (1-2 agents, linear flow)
- You want maximum control and minimal abstraction
- You're building a prototype and don't need the overhead
- You have very specific architectural requirements

## Resources

- [Official Documentation](https://python.langchain.com/)
- [LangGraph Guide](https://langchain-ai.github.io/langgraph/)
- [LangChain GitHub](https://github.com/langchain-ai/langchain)
- [Multi-Agent Tutorial](https://python.langchain.com/docs/use_cases/multi_agent/)

---

**Next**: [AutoGen Framework](autogen.md) | [Back to README](../README.md)
