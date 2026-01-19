# CrewAI Multi-Agent Framework

**Role-based collaborative AI agent framework for structured multi-agent workflows**

---

## Overview

CrewAI is a framework that orchestrates role-playing AI agents. It enables you to create teams of agents with specific roles, goals, and tools that work together to accomplish complex tasks through structured collaboration.

### Key Strengths
- **Role-based architecture**: Clear separation of concerns through defined roles
- **Hierarchical organization**: Natural support for manager-worker patterns
- **Task delegation**: Built-in task distribution and dependency management
- **Process-driven**: Explicit control over agent workflows and sequences
- **Intuitive API**: Simple, readable syntax for defining crews

### Key Weaknesses
- **Less mature**: Newer framework with smaller community than LangChain
- **Limited documentation**: Some advanced patterns lack examples
- **Rigid structure**: Role-based approach can be inflexible for dynamic scenarios
- **Fewer integrations**: Less extensive tool ecosystem than LangChain

## Architecture Patterns

### 1. Basic Crew Setup

CrewAI uses "Crews" (teams of agents) that work on "Tasks" through a defined "Process".

```python
from crewai import Agent, Task, Crew, Process

# Define agents with specific roles
researcher = Agent(
    role="Research Specialist",
    goal="Discover and analyze cutting-edge information",
    backstory="""You are an experienced researcher with expertise in
    finding and synthesizing information from various sources.""",
    verbose=True,
    tools=[search_tool, web_scraper]
)

writer = Agent(
    role="Content Writer",
    goal="Create engaging and informative content",
    backstory="""You are a skilled writer who can transform complex
    information into clear, compelling narratives.""",
    verbose=True
)

# Define tasks
research_task = Task(
    description="Research the latest developments in quantum computing",
    expected_output="A comprehensive report on quantum computing advances",
    agent=researcher
)

writing_task = Task(
    description="Write a blog post about quantum computing",
    expected_output="An engaging 1000-word blog post",
    agent=writer,
    context=[research_task]  # Use output from research_task
)

# Create crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    process=Process.sequential,  # Tasks execute in sequence
    verbose=True
)

# Execute
result = crew.kickoff()
```

### 2. Hierarchical Agent Teams

CrewAI excels at hierarchical organization where managers delegate to workers.

```python
from crewai import Crew, Agent, Task, Process

# Manager agent
project_manager = Agent(
    role="Project Manager",
    goal="Coordinate team efforts and ensure project success",
    backstory="""You are an experienced project manager skilled at
    delegating tasks and coordinating team efforts.""",
    verbose=True,
    allow_delegation=True  # Can delegate tasks to other agents
)

# Worker agents
developer = Agent(
    role="Senior Developer",
    goal="Write high-quality, efficient code",
    backstory="You are an expert developer with 10+ years of experience",
    verbose=True,
    tools=[code_executor, file_writer]
)

tester = Agent(
    role="QA Engineer",
    goal="Ensure code quality through thorough testing",
    backstory="You are a detail-oriented QA specialist",
    verbose=True,
    tools=[test_runner, coverage_tool]
)

designer = Agent(
    role="UI/UX Designer",
    goal="Create intuitive and beautiful user interfaces",
    backstory="You are a creative designer with UX expertise",
    verbose=True
)

# Manager's task - will delegate to workers
management_task = Task(
    description="Oversee the development of a web application",
    expected_output="Completed web application with tests",
    agent=project_manager
)

# Create hierarchical crew
crew = Crew(
    agents=[project_manager, developer, tester, designer],
    tasks=[management_task],
    process=Process.hierarchical,  # Manager delegates to workers
    manager_llm="gpt-4"  # LLM used for delegation decisions
)

result = crew.kickoff()
```

### 3. Parallel Task Execution

Run multiple agents in parallel to accomplish independent tasks simultaneously.

```python
# Agents for different aspects
market_researcher = Agent(
    role="Market Researcher",
    goal="Analyze market trends and competition",
    backstory="You are expert at market analysis",
    tools=[market_data_api, competitor_analyzer]
)

technical_researcher = Agent(
    role="Technical Researcher",
    goal="Research technical requirements and solutions",
    backstory="You are a technical architect",
    tools=[tech_docs, stack_overflow]
)

financial_analyst = Agent(
    role="Financial Analyst",
    goal="Analyze costs and financial viability",
    backstory="You are a financial planning expert",
    tools=[cost_calculator, roi_tool]
)

# Parallel tasks
market_task = Task(
    description="Analyze the market for our product",
    agent=market_researcher
)

technical_task = Task(
    description="Research technical requirements",
    agent=technical_researcher
)

financial_task = Task(
    description="Create financial projections",
    agent=financial_analyst
)

# Synthesis task (runs after parallel tasks complete)
synthesis_task = Task(
    description="Combine all research into a comprehensive report",
    agent=senior_analyst,
    context=[market_task, technical_task, financial_task]
)

# Crew with parallel execution
crew = Crew(
    agents=[market_researcher, technical_researcher,
            financial_analyst, senior_analyst],
    tasks=[market_task, technical_task, financial_task, synthesis_task],
    process=Process.parallel  # Parallel execution
)

result = crew.kickoff()
```

## Context Sharing Patterns

### 1. Task Output as Context

CrewAI makes it easy to pass task outputs to subsequent tasks.

```python
# Research task
research_task = Task(
    description="Research AI safety best practices",
    agent=researcher,
    expected_output="Detailed research findings"
)

# Analysis task uses research output
analysis_task = Task(
    description="Analyze the research findings",
    agent=analyst,
    expected_output="Analysis report",
    context=[research_task]  # Automatically includes research output
)

# Writing task uses both previous outputs
writing_task = Task(
    description="Write a comprehensive guide based on research and analysis",
    agent=writer,
    expected_output="Complete guide document",
    context=[research_task, analysis_task]  # Combines multiple contexts
)
```

### 2. Shared Knowledge Base

```python
from typing import Dict, List
import json

class CrewKnowledgeBase:
    def __init__(self):
        self.facts: List[Dict] = []
        self.decisions: List[Dict] = []
        self.artifacts: Dict[str, any] = {}

    def add_fact(self, fact: str, source_agent: str, confidence: float = 1.0):
        self.facts.append({
            "fact": fact,
            "source": source_agent,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })

    def add_decision(self, decision: str, rationale: str, agent: str):
        self.decisions.append({
            "decision": decision,
            "rationale": rationale,
            "agent": agent,
            "timestamp": datetime.now().isoformat()
        })

    def store_artifact(self, key: str, value: any, agent: str):
        self.artifacts[key] = {
            "value": value,
            "created_by": agent,
            "created_at": datetime.now().isoformat()
        }

    def get_relevant_context(self, query_keywords: List[str]) -> str:
        """Retrieve context relevant to keywords"""
        relevant_facts = [
            f["fact"] for f in self.facts
            if any(kw in f["fact"].lower() for kw in query_keywords)
        ]

        return f"""
        Relevant Facts:
        {chr(10).join(relevant_facts)}

        Recent Decisions:
        {chr(10).join([d['decision'] for d in self.decisions[-5:]])}
        """

# Use with CrewAI
knowledge_base = CrewKnowledgeBase()

# Custom agent that uses knowledge base
class KnowledgeAwareAgent(Agent):
    def __init__(self, *args, knowledge_base, **kwargs):
        super().__init__(*args, **kwargs)
        self.knowledge_base = knowledge_base

    def execute_task(self, task: Task):
        # Get relevant context
        context = self.knowledge_base.get_relevant_context(
            task.description.split()
        )

        # Add context to task
        enhanced_description = f"""
        Task: {task.description}

        Relevant Context:
        {context}
        """

        # Execute with enhanced context
        result = super().execute_task(
            Task(description=enhanced_description, **task.__dict__)
        )

        # Store learnings back to knowledge base
        self.knowledge_base.add_fact(
            result,
            self.role,
            confidence=0.9
        )

        return result
```

### 3. Cross-Crew Communication

Share state between multiple crews.

```python
class SharedContext:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()

    def set(self, key: str, value: any):
        with self.lock:
            self.data[key] = value

    def get(self, key: str, default=None):
        with self.lock:
            return self.data.get(key, default)

    def update(self, updates: dict):
        with self.lock:
            self.data.update(updates)

# Shared context between crews
shared_context = SharedContext()

# Crew 1: Research
research_crew = Crew(
    agents=[research_agent, analyst_agent],
    tasks=[research_task],
    process=Process.sequential
)

research_result = research_crew.kickoff()
shared_context.set("research_data", research_result)

# Crew 2: Development (uses research data)
development_crew = Crew(
    agents=[developer_agent, tester_agent],
    tasks=[development_task],
    process=Process.sequential
)

development_result = development_crew.kickoff()
shared_context.set("development_artifacts", development_result)

# Crew 3: Documentation (uses both)
doc_crew = Crew(
    agents=[writer_agent, editor_agent],
    tasks=[documentation_task],
    process=Process.sequential
)
```

## Task Distribution Patterns

### 1. Automatic Delegation

CrewAI agents can automatically delegate tasks to more suitable agents.

```python
# Manager that can delegate
manager = Agent(
    role="Project Manager",
    goal="Coordinate team to complete project",
    backstory="Experienced PM",
    allow_delegation=True,  # Key: enables delegation
    verbose=True
)

# Specialists that receive delegated tasks
coder = Agent(
    role="Developer",
    goal="Write high-quality code",
    backstory="Expert developer"
)

designer = Agent(
    role="Designer",
    goal="Create beautiful designs",
    backstory="Creative designer"
)

# Manager's task will be delegated automatically
manager_task = Task(
    description="Build a web application with clean code and good design",
    expected_output="Completed application",
    agent=manager
)

crew = Crew(
    agents=[manager, coder, designer],
    tasks=[manager_task],
    process=Process.hierarchical
)

# Manager will automatically delegate to coder and designer
result = crew.kickoff()
```

### 2. Manual Task Routing

Explicit control over which agent handles which task.

```python
class TaskRouter:
    def __init__(self, agents: Dict[str, Agent]):
        self.agents = agents
        self.task_queue = []

    def add_task(self, task: Task, preferred_agent: str = None):
        self.task_queue.append({
            "task": task,
            "preferred_agent": preferred_agent
        })

    def execute(self) -> dict:
        results = {}

        for item in self.task_queue:
            task = item["task"]
            preferred = item["preferred_agent"]

            if preferred and preferred in self.agents:
                agent = self.agents[preferred]
            else:
                agent = self._select_best_agent(task)

            result = agent.execute_task(task)
            results[task.description] = result

        return results

    def _select_best_agent(self, task: Task) -> Agent:
        """Select best agent based on task description"""
        task_lower = task.description.lower()

        # Simple keyword matching
        if "code" in task_lower or "develop" in task_lower:
            return self.agents.get("developer")
        elif "design" in task_lower or "ui" in task_lower:
            return self.agents.get("designer")
        elif "test" in task_lower or "qa" in task_lower:
            return self.agents.get("tester")
        else:
            return self.agents.get("generalist")

# Usage
router = TaskRouter({
    "developer": developer,
    "designer": designer,
    "tester": tester,
    "generalist": generalist
})

router.add_task(coding_task, preferred_agent="developer")
router.add_task(design_task, preferred_agent="designer")
router.add_task(testing_task, preferred_agent="tester")

results = router.execute()
```

### 3. Priority-Based Task Scheduling

```python
from queue import PriorityQueue
from dataclasses import dataclass
from enum import Enum

class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class PrioritizedTask:
    priority: Priority
    task: Task

    def __lt__(self, other):
        return self.priority.value < other.priority.value

class PriorityTaskScheduler:
    def __init__(self, agents: Dict[str, Agent]):
        self.agents = agents
        self.task_queue = PriorityQueue()

    def add_task(self, task: Task, priority: Priority = Priority.MEDIUM):
        prioritized = PrioritizedTask(priority=priority, task=task)
        self.task_queue.put(prioritized)

    def execute_all(self):
        results = []

        while not self.task_queue.empty():
            prioritized = self.task_queue.get()
            task = prioritized.task

            # Select appropriate agent
            agent = self._select_agent(task)

            result = agent.execute_task(task)
            results.append(result)

        return results

    def _select_agent(self, task: Task) -> Agent:
        # Agent selection logic
        return list(self.agents.values())[0]
```

## State Management

### 1. Crew-Level State

```python
from typing import TypedDict
import json

class CrewState(TypedDict):
    tasks_completed: List[str]
    current_phase: str
    shared_data: Dict[str, any]
    errors: List[Dict]

class StatefulCrew(Crew):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state: CrewState = {
            "tasks_completed": [],
            "current_phase": "initialization",
            "shared_data": {},
            "errors": []
        }

    def update_state(self, updates: dict):
        self.state.update(updates)

    def save_state(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.state, f, indent=2)

    def load_state(self, filepath: str):
        with open(filepath, 'r') as f:
            self.state = json.load(f)

# Usage
crew = StatefulCrew(
    agents=[agent1, agent2],
    tasks=[task1, task2],
    process=Process.sequential
)

crew.update_state({"current_phase": "execution"})

# Execute
result = crew.kickoff()

# Save state for later
crew.save_state("crew_state.json")
```

### 2. Distributed State with Redis

```python
import redis
import json
import threading

class DistributedCrewState:
    def __init__(self, redis_url: str = "redis://localhost:6379",
                 crew_id: str = "default"):
        self.client = redis.from_url(redis_url)
        self.crew_id = crew_id
        self.lock = threading.Lock()

    def _make_key(self, key: str) -> str:
        return f"crew:{self.crew_id}:{key}"

    def set(self, key: str, value: any):
        redis_key = self._make_key(key)
        with self.lock:
            self.client.set(redis_key, json.dumps(value))

    def get(self, key: str, default=None):
        redis_key = self._make_key(key)
        value = self.client.get(redis_key)
        if value:
            return json.loads(value)
        return default

    def update(self, updates: dict):
        with self.lock:
            for key, value in updates.items():
                self.set(key, value)

    def get_all(self) -> dict:
        keys = self.client.keys(f"crew:{self.crew_id}:*")
        result = {}
        for key in keys:
            short_key = key.split(":")[-1].decode()
            result[short_key] = self.get(short_key)
        return result
```

### 3. Checkpoint and Recovery

```python
from datetime import datetime
import pickle

class CheckpointManager:
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def save_checkpoint(self, crew: Crew, checkpoint_id: str = None):
        if checkpoint_id is None:
            checkpoint_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        filepath = self.checkpoint_dir / f"crew_{checkpoint_id}.pkl"

        checkpoint_data = {
            "crew_id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "state": crew.state if hasattr(crew, 'state') else {},
            "completed_tasks": [],
            "pending_tasks": []
        }

        with open(filepath, 'wb') as f:
            pickle.dump(checkpoint_data, f)

        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> dict:
        filepath = self.checkpoint_dir / f"crew_{checkpoint_id}.pkl"

        with open(filepath, 'rb') as f:
            return pickle.load(f)

    def list_checkpoints(self) -> List[str]:
        return [
            f.stem.replace("crew_", "")
            for f in self.checkpoint_dir.glob("crew_*.pkl")
        ]
```

## 24/7 Operation Considerations

### 1. Resilient Agent Wrapper

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

class ResilientCrewAgent(Agent):
    def __init__(self, *args, max_retries=3, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
        self.logger = logging.getLogger(self.role)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def execute_task(self, task: Task):
        try:
            result = super().execute_task(task)
            self.logger.info(f"Task completed successfully: {task.description}")
            return result
        except Exception as e:
            self.logger.error(f"Task failed: {e}")
            raise

    def safe_execute_task(self, task: Task):
        """Execute with fallback on final failure"""
        try:
            return self.execute_task(task)
        except Exception as e:
            self.logger.critical(f"All retries failed for task: {task.description}")
            return {
                "error": str(e),
                "task": task.description,
                "fallback": "Task failed after all retries"
            }
```

### 2. Health Monitoring

```python
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class AgentHealth:
    agent_name: str
    role: str
    is_healthy: bool
    last_task_time: datetime
    consecutive_failures: int
    total_tasks: int
    success_rate: float

class CrewHealthMonitor:
    def __init__(self):
        self.agent_health: Dict[str, AgentHealth] = {}

    def register_agent(self, agent: Agent):
        self.agent_health[agent.role] = AgentHealth(
            agent_name=agent.role,
            role=agent.role,
            is_healthy=True,
            last_task_time=datetime.now(),
            consecutive_failures=0,
            total_tasks=0,
            success_rate=1.0
        )

    def record_success(self, agent_role: str):
        if agent_role not in self.agent_health:
            return

        health = self.agent_health[agent_role]
        health.last_task_time = datetime.now()
        health.consecutive_failures = 0
        health.total_tasks += 1

        # Recalculate success rate
        health.success_rate = (
            (health.total_tasks - 1) * health.success_rate + 1.0
        ) / health.total_tasks

        health.is_healthy = True

    def record_failure(self, agent_role: str):
        if agent_role not in self.agent_health:
            return

        health = self.agent_health[agent_role]
        health.last_task_time = datetime.now()
        health.consecutive_failures += 1
        health.total_tasks += 1

        # Update success rate
        health.success_rate = (
            (health.total_tasks - 1) * health.success_rate
        ) / health.total_tasks

        if health.consecutive_failures >= 5:
            health.is_healthy = False

    def is_healthy(self, agent_role: str) -> bool:
        if agent_role not in self.agent_health:
            return True

        health = self.agent_health[agent_role]
        return health.is_healthy

    def get_health_report(self) -> Dict[str, dict]:
        return {
            role: {
                "healthy": health.is_healthy,
                "success_rate": health.success_rate,
                "total_tasks": health.total_tasks,
                "consecutive_failures": health.consecutive_failures,
                "last_task": health.last_task_time.isoformat()
            }
            for role, health in self.agent_health.items()
        }
```

### 3. Automatic Recovery

```python
class SelfHealingCrew(Crew):
    def __init__(self, *args, auto_recovery=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_recovery = auto_recovery
        self.health_monitor = CrewHealthMonitor()

        # Register all agents
        for agent in self.agents:
            self.health_monitor.register_agent(agent)

    def kickoff(self, *args, **kwargs):
        # Monitor health during execution
        for agent in self.agents:
            agent_role = agent.role

            try:
                # Execute tasks
                result = super().kickoff(*args, **kwargs)
                self.health_monitor.record_success(agent_role)

            except Exception as e:
                self.health_monitor.record_failure(agent_role)

                if self.auto_recovery:
                    self._attempt_recovery(agent_role, e)
                else:
                    raise

        return result

    def _attempt_recovery(self, agent_role: str, error: Exception):
        """Attempt to recover from agent failure"""
        if self.health_monitor.agent_health[agent_role].consecutive_failures >= 3:
            # Agent is unhealthy, try recreating it
            print(f"Attempting recovery for agent: {agent_role}")

            # Recovery logic: recreate agent, reset state, etc.
            # This would be implementation-specific
```

## Budget Management

### 1. Token Budget Tracker for CrewAI

```python
from typing import Dict
from dataclasses import dataclass

@dataclass
class AgentBudget:
    agent_role: str
    total_tokens: int = 0
    total_cost: float = 0.0
    tasks_completed: int = 0

class CrewBudgetManager:
    def __init__(self, total_budget: float,
                 cost_per_1k_tokens: float = 0.002):
        self.total_budget = total_budget
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.agent_budgets: Dict[str, AgentBudget] = {}
        self.global_spent = 0.0

    def get_agent_budget(self, agent_role: str) -> AgentBudget:
        if agent_role not in self.agent_budgets:
            self.agent_budgets[agent_role] = AgentBudget(agent_role=agent_role)
        return self.agent_budgets[agent_role]

    def record_task_cost(self, agent_role: str, tokens: int):
        cost = (tokens / 1000) * self.cost_per_1k_tokens

        budget = self.get_agent_budget(agent_role)
        budget.total_tokens += tokens
        budget.total_cost += cost
        budget.tasks_completed += 1

        self.global_spent += cost

    def can_afford_task(self, estimated_tokens: int) -> bool:
        estimated_cost = (estimated_tokens / 1000) * self.cost_per_1k_tokens
        return (self.global_spent + estimated_cost) <= self.total_budget

    def get_remaining_budget(self) -> float:
        return self.total_budget - self.global_spent

    def get_budget_report(self) -> dict:
        return {
            "total_budget": self.total_budget,
            "spent": self.global_spent,
            "remaining": self.get_remaining_budget(),
            "by_agent": {
                role: {
                    "spent": budget.total_cost,
                    "tokens": budget.total_tokens,
                    "tasks": budget.tasks_completed
                }
                for role, budget in self.agent_budgets.items()
            }
        }
```

### 2. Budget-Constrained Crew

```python
class BudgetAwareCrew(Crew):
    def __init__(self, *args, budget_manager: CrewBudgetManager, **kwargs):
        super().__init__(*args, **kwargs)
        self.budget_manager = budget_manager

    def kickoff(self, *args, **kwargs):
        # Estimate total tokens needed
        estimated_tokens = sum(
            len(task.description) // 4  # Rough estimate
            for task in self.tasks
        )

        if not self.budget_manager.can_afford_task(estimated_tokens):
            raise Exception("Insufficient budget to complete tasks")

        # Execute normally
        result = super().kickoff(*args, **kwargs)

        # Record actual costs (would need to extract from result)
        for agent in self.agents:
            estimated = len(str(result)) // 4
            self.budget_manager.record_task_cost(agent.role, estimated)

        return result

    def get_budget_status(self) -> dict:
        return self.budget_manager.get_budget_report()
```

## Best Practices

### ✅ DO:

1. **Leverage role-based architecture**
   - Define clear, specific roles for each agent
   - Use roles to separate concerns naturally
   - Let agent expertise guide task allocation

2. **Use hierarchical process for complex tasks**
   - Manager agents coordinate worker agents
   - Enables automatic delegation
   - Scales better than flat organization

3. **Structure tasks with dependencies**
   - Use `context` parameter to chain tasks
   - Clearly define expected outputs
   - Make dependencies explicit

4. **Monitor crew health**
   - Track success/failure rates
   - Detect unhealthy agents early
   - Implement recovery mechanisms

5. **Budget conservatively**
   - Estimate token usage per task
   - Add 2-3x buffer for multi-agent overhead
   - Track spending per agent

### ❌ DON'T:

1. **Create too many agents**
   - More agents = more cost and complexity
   - Start with 3-5 well-defined roles
   - Add more only if justified

2. **Ignore task dependencies**
   - Tasks will run in wrong order without context
   - Always specify dependencies explicitly
   - Use sequential process for dependent tasks

3. **Overuse delegation**
   - Automatic delegation can be unpredictable
   - Manual routing gives more control
   - Mix both approaches strategically

4. **Skip error handling**
   - Agent failures will halt the crew
   - Implement retries and fallbacks
   - Monitor and log all failures

5. **Allow unlimited task execution**
   - Set timeouts and max iterations
   - Prevent infinite delegation loops
   - Monitor task completion status

## Comparison with Alternatives

| Feature | CrewAI | LangChain | AutoGen | Custom |
|---------|--------|-----------|---------|--------|
| Role-Based | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Hierarchical | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Task Delegation | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Ease of Use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Flexibility | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## When to Choose CrewAI

**Choose CrewAI if:**
- Your problem naturally maps to specialized roles
- You need hierarchical organization
- Task dependencies are important
- You want an intuitive, readable API
- Automatic delegation is valuable

**Avoid CrewAI if:**
- You need maximum flexibility
- Your use case doesn't fit role-based model
- You require complex state management
- You want fine-grained control over execution

## Resources

- [Official Documentation](https://docs.crewai.com/)
- [CrewAI GitHub](https://github.com/joaomdmoura/crewAI)
- [Examples](https://github.com/joaomdmoura/crewAI-examples)
- [Tutorials](https://docs.crewai.com/introduction)

---

**Next**: [Custom Approaches](custom.md) | [Back to README](../README.md)
