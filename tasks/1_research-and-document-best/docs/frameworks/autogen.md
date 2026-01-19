# AutoGen Multi-Agent Framework

**Microsoft's conversational multi-agent framework for building sophisticated AI agent systems**

---

## Overview

AutoGen is a framework developed by Microsoft that enables the development of LLM applications using multiple agents that can converse with each other to solve tasks. AutoGen agents are customizable, can participate in conversations, and can be human-in-the-loop.

### Key Strengths
- **Conversational paradigm**: Natural agent-to-agent communication
- **Human-in-the-loop**: Built-in support for human interaction
- **Code execution**: Agents can write and execute code
- **Flexible orchestration**: Support for various conversation patterns
- **Microsoft backing**: Active development with good documentation

### Key Weaknesses
- **Framework lock-in**: Specific conversation model, less flexible than LangChain
- **Less mature**: Newer than LangChain, smaller community
- **State management**: Less sophisticated than LangGraph
- **Documentation gaps**: Some advanced patterns lack examples

## Architecture Patterns

### 1. Conversational Agents

AutoGen's core abstraction is the conversational agent that can send and receive messages.

```python
import autogen

# Define agents
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={
        "model": "gpt-4",
        "api_key": "your-api-key",
        "temperature": 0
    }
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",  # Fully autonomous
    max_consecutive_auto_reply=10,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False
    }
)

# Start conversation
user_proxy.initiate_chat(
    assistant,
    message="Write a Python function to calculate fibonacci numbers"
)
```

### 2. Multi-Agent Conversation Groups

AutoGen supports group chats where multiple agents collaborate.

```python
# Create specialized agents
coder = autogen.AssistantAgent(
    name="Coder",
    system_message="You are a coding expert. Write clean, efficient code.",
    llm_config=llm_config
)

reviewer = autogen.AssistantAgent(
    name="Reviewer",
    system_message="You are a code reviewer. Check for bugs and improvements.",
    llm_config=llm_config
)

tester = autogen.AssistantAgent(
    name="Tester",
    system_message="You write comprehensive tests for code.",
    llm_config=llm_config
)

user_proxy = autogen.UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=0
)

# Create group chat
groupchat = autogen.GroupChat(
    agents=[user_proxy, coder, reviewer, tester],
    messages=[],
    max_round=20
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_config
)

# Start group conversation
user_proxy.initiate_chat(
    manager,
    message="Create a web scraper for news sites"
)
```

### 3. Hierarchical Conversations

Pattern for having a manager agent coordinate worker agents.

```python
# Manager agent
manager = autogen.AssistantAgent(
    name="Manager",
    system_message="""You are a project manager.
    Coordinate tasks between team members.
    Delegate work to the appropriate specialist.""",
    llm_config=llm_config
)

# Worker agents
researcher = autogen.AssistantAgent(
    name="Researcher",
    system_message="You conduct research and gather information.",
    llm_config=llm_config
)

developer = autogen.AssistantAgent(
    name="Developer",
    system_message="You write code based on requirements.",
    llm_config=llm_config
)

# Define conversation flow
def hierarchical_workflow(task: str):
    # Manager gets the task
    manager.initiate_chat(
        user_proxy,
        message=f"Task: {task}. Coordinate this work."
    )

    # AutoGen handles routing through the GroupChatManager
    # based on conversation context
```

## Context Sharing Patterns

### 1. Message History Propagation

AutoGen automatically maintains conversation history.

```python
class ContextAwareAgent(autogen.AssistantAgent):
    def __init__(self, *args, context_memory_limit=10, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_memory_limit = context_memory_limit

    def generate_reply(self, messages, sender, config):
        # Filter to recent messages for context
        recent_messages = messages[-self.context_memory_limit:]

        # Add agent-specific context
        system_context = f"""
        You are {self.name}.
        Recent conversation:
        {self._format_messages(recent_messages)}
        """

        # Generate response
        return super().generate_reply(messages, sender, config)

    def _format_messages(self, messages):
        return "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ])
```

### 2. Shared Knowledge Base

```python
from typing import Dict, List
import json

class SharedKnowledge:
    def __init__(self):
        self.facts: List[str] = []
        self.decisions: List[Dict] = []

    def add_fact(self, fact: str, source_agent: str):
        self.facts.append({
            "content": fact,
            "source": source_agent,
            "timestamp": datetime.now().isoformat()
        })

    def add_decision(self, decision: str, rationale: str, agent: str):
        self.decisions.append({
            "decision": decision,
            "rationale": rationale,
            "agent": agent,
            "timestamp": datetime.now().isoformat()
        })

    def get_relevant_context(self, query: str) -> str:
        """Get context relevant to a query"""
        # Simple implementation - could use embeddings
        relevant_facts = [f["content"] for f in self.facts]
        relevant_decisions = [
            f"{d['decision']}: {d['rationale']}"
            for d in self.decisions
        ]

        return f"""
        Known Facts:
        {chr(10).join(relevant_facts)}

        Previous Decisions:
        {chr(10).join(relevant_decisions)}
        """

# Use in AutoGen agents
knowledge = SharedKnowledge()

agent1 = autogen.AssistantAgent(
    name="Researcher",
    system_message="""
    You are a researcher.
    When you discover information, add it to the shared knowledge.
    """,
    llm_config=llm_config
)

agent2 = autogen.AssistantAgent(
    name="Writer",
    system_message="""
    You are a writer.
    Use the shared knowledge to inform your writing.
    """,
    llm_config=llm_config
)
```

### 3. Context Filters for Privacy

```python
class PrivacyFilteredContext:
    def __init__(self):
        self.public_context = []
        self.private_context = {}

    def add_message(self, content: str, agent: str, is_private: bool = False):
        if is_private:
            if agent not in self.private_context:
                self.private_context[agent] = []
            self.private_context[agent].append({
                "content": content,
                "timestamp": datetime.now()
            })
        else:
            self.public_context.append({
                "content": content,
                "agent": agent,
                "timestamp": datetime.now()
            })

    def get_context_for_agent(self, agent: str) -> List[dict]:
        """Get context - public + agent's private messages"""
        context = self.public_context.copy()
        if agent in self.private_context:
            context.extend(self.private_context[agent])
        return context
```

## Task Distribution Patterns

### 1. Task Queue with AutoGen Agents

```python
import queue
import threading

class AutoGenTaskQueue:
    def __init__(self, agents: Dict[str, autogen.AssistantAgent]):
        self.task_queue = queue.Queue()
        self.agents = agents
        self.results = {}
        self.running = True

    def add_task(self, task_id: str, task_data: dict, agent_type: str):
        self.task_queue.put({
            "task_id": task_id,
            "task_data": task_data,
            "agent_type": agent_type
        })

    def worker_loop(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                agent = self.agents[task["agent_type"]]

                # Execute task with agent
                result = self._execute_task(agent, task)

                self.results[task["task_id"]] = {
                    "status": "complete",
                    "result": result
                }

            except queue.Empty:
                continue
            except Exception as e:
                self.results[task["task_id"]] = {
                    "status": "failed",
                    "error": str(e)
                }
            finally:
                self.task_queue.task_done()

    def _execute_task(self, agent, task):
        # Create a user proxy for this task
        user_proxy = autogen.UserProxyAgent(
            name=f"task_proxy_{task['task_id']}",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1
        )

        # Initiate chat with the agent
        user_proxy.initiate_chat(
            agent,
            message=task["task_data"]["prompt"]
        )

        return user_proxy.last_message()

    def start_workers(self, num_workers=3):
        self.workers = []
        for i in range(num_workers):
            thread = threading.Thread(target=self.worker_loop, daemon=True)
            thread.start()
            self.workers.append(thread)
```

### 2. Dynamic Task Allocation

```python
class DynamicTaskAllocator:
    def __init__(self, agents: Dict[str, autogen.AssistantAgent]):
        self.agents = agents
        self.agent_load = {name: 0 for name in agents.keys()}
        self.agent_capabilities = self._assess_capabilities()

    def _assess_capabilities(self) -> Dict[str, List[str]]:
        """Assess what each agent can do"""
        return {
            "coder": ["coding", "debugging", "algorithms"],
            "writer": ["writing", "editing", "formatting"],
            "researcher": ["analysis", "research", "fact-checking"]
        }

    def allocate_task(self, task: dict) -> str:
        """Dynamically allocate task to best-suited agent"""
        task_type = task.get("type", "general")

        # Find agents capable of this task
        capable_agents = [
            agent for agent, capabilities in self.agent_capabilities.items()
            if task_type in capabilities
        ]

        if not capable_agents:
            # Default to least loaded agent
            return min(self.agent_load, key=self.agent_load.get)

        # Select least loaded capable agent
        selected = min(
            capable_agents,
            key=lambda a: self.agent_load[a]
        )

        # Increment load
        self.agent_load[selected] += 1

        return selected

    def release_agent(self, agent_name: str):
        if self.agent_load[agent_name] > 0:
            self.agent_load[agent_name] -= 1
```

## State Management

### 1. Conversation State Persistence

```python
import pickle
from pathlib import Path

class ConversationStateManager:
    def __init__(self, save_dir: str = "./conversations"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)

    def save_conversation(self, conversation_id: str, messages: list):
        """Save conversation state"""
        filepath = self.save_dir / f"{conversation_id}.pkl"
        with open(filepath, 'wb') as f:
            pickle.dump(messages, f)

    def load_conversation(self, conversation_id: str) -> list:
        """Load conversation state"""
        filepath = self.save_dir / f"{conversation_id}.pkl"
        if filepath.exists():
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        return []

    def resume_conversation(self, conversation_id: str, agents: dict):
        """Resume a saved conversation"""
        messages = self.load_conversation(conversation_id)

        # Create a group chat with the saved messages
        groupchat = autogen.GroupChat(
            agents=list(agents.values()),
            messages=messages,
            max_round=100
        )

        manager = autogen.GroupChatManager(
            groupchat=groupchat,
            llm_config=llm_config
        )

        return manager
```

### 2. Distributed State with Redis

```python
import redis
import json
from typing import Any

class AutoGenStateStore:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.client = redis.from_url(redis_url)

    def save_agent_state(self, agent_name: str, state: dict):
        """Save agent-specific state"""
        key = f"agent:{agent_name}:state"
        self.client.set(key, json.dumps(state))

    def load_agent_state(self, agent_name: str) -> dict:
        """Load agent-specific state"""
        key = f"agent:{agent_name}:state"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return {}

    def save_conversation_state(self, conversation_id: str, messages: list):
        """Save conversation messages"""
        key = f"conversation:{conversation_id}:messages"
        self.client.set(key, json.dumps(messages))

    def get_conversation_state(self, conversation_id: str) -> list:
        """Get conversation messages"""
        key = f"conversation:{conversation_id}:messages"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return []
```

## 24/7 Operation Considerations

### 1. Resilient Agent Wrapper

```python
from autogen import ConversableAgent
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

class ResilientAgent(ConversableAgent):
    def __init__(self, *args, max_retries=3, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
        self.logger = logging.getLogger(self.name)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_reply(self, messages, sender, config):
        try:
            return super().generate_reply(messages, sender, config)
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed: {e}")
            # Return a fallback response
            return {
                "content": f"Agent {self.name} encountered an error. Please retry.",
                "error": str(e)
            }

    def generate_reply_with_timeout(self, messages, sender, config, timeout=30):
        """Generate reply with timeout to prevent hanging"""
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Agent {self.name} timed out")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        try:
            result = self.generate_reply(messages, sender, config)
            signal.alarm(0)
            return result
        except TimeoutError as e:
            signal.alarm(0)
            return {
                "content": f"Agent {self.name} timed out",
                "error": str(e)
            }
```

### 2. Health Monitoring

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict

@dataclass
class AgentHealthStatus:
    agent_name: str
    is_healthy: bool
    last_activity: datetime
    failure_count: int
    success_count: int
    avg_response_time: float

class AutoGenHealthMonitor:
    def __init__(self):
        self.health_status: Dict[str, AgentHealthStatus] = {}
        self.health_checks = {}

    def register_agent(self, agent_name: str):
        self.health_status[agent_name] = AgentHealthStatus(
            agent_name=agent_name,
            is_healthy=True,
            last_activity=datetime.now(),
            failure_count=0,
            success_count=0,
            avg_response_time=0.0
        )

    def record_success(self, agent_name: str, response_time: float):
        if agent_name not in self.health_status:
            self.register_agent(agent_name)

        status = self.health_status[agent_name]
        status.last_activity = datetime.now()
        status.success_count += 1
        status.failure_count = 0
        status.is_healthy = True

        # Update average response time
        status.avg_response_time = (
            (status.avg_response_time * (status.success_count - 1) + response_time)
            / status.success_count
        )

    def record_failure(self, agent_name: str):
        if agent_name not in self.health_status:
            self.register_agent(agent_name)

        status = self.health_status[agent_name]
        status.last_activity = datetime.now()
        status.failure_count += 1

        if status.failure_count >= 5:
            status.is_healthy = False

    def is_healthy(self, agent_name: str) -> bool:
        if agent_name not in self.health_status:
            return True

        status = self.health_status[agent_name]
        return status.is_healthy and (
            datetime.now() - status.last_activity < timedelta(minutes=5)
        )

    def get_health_report(self) -> Dict[str, dict]:
        return {
            name: {
                "healthy": status.is_healthy,
                "last_activity": status.last_activity.isoformat(),
                "failures": status.failure_count,
                "successes": status.success_count,
                "avg_response_time": status.avg_response_time
            }
            for name, status in self.health_status.items()
        }
```

### 3. Automatic Recovery

```python
class AutoGenRecoveryManager:
    def __init__(self, agents: Dict[str, ConversableAgent]):
        self.agents = agents
        self.health_monitor = AutoGenHealthMonitor()
        self.backup_configs = self._create_backup_configs()

    def _create_backup_configs(self):
        """Create backup configurations for recovery"""
        return {
            name: {
                "llm_config": agent.llm_config,
                "system_message": agent.system_message
            }
            for name, agent in self.agents.items()
        }

    def check_and_recover_agents(self):
        """Check all agents and recover failed ones"""
        for agent_name in self.agents.keys():
            if not self.health_monitor.is_healthy(agent_name):
                self._recover_agent(agent_name)

    def _recover_agent(self, agent_name: str):
        """Recover a failed agent"""
        print(f"Attempting to recover agent: {agent_name}")

        # Create new agent instance with backup config
        backup_config = self.backup_configs[agent_name]

        # Recreate agent
        self.agents[agent_name] = autogen.AssistantAgent(
            name=agent_name,
            **backup_config
        )

        # Reset health status
        self.health_monitor.register_agent(agent_name)

        print(f"Agent {agent_name} recovered")
```

## Budget Management

### 1. Token Budget Tracking

```python
from typing import Dict
from dataclasses import dataclass

@dataclass
class BudgetTracker:
    agent_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0

class AutoGenBudgetManager:
    def __init__(self, total_budget: float, cost_per_1k_input: float = 0.0015,
                 cost_per_1k_output: float = 0.002):
        self.total_budget = total_budget
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output
        self.trackers: Dict[str, BudgetTracker] = {}

    def get_tracker(self, agent_name: str) -> BudgetTracker:
        if agent_name not in self.trackers:
            self.trackers[agent_name] = BudgetTracker(agent_name=agent_name)
        return self.trackers[agent_name]

    def record_usage(self, agent_name: str, input_tokens: int, output_tokens: int):
        tracker = self.get_tracker(agent_name)

        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        total_cost = input_cost + output_cost

        tracker.input_tokens += input_tokens
        tracker.output_tokens += output_tokens
        tracker.total_cost += total_cost

    def can_afford(self, estimated_input: int, estimated_output: int) -> bool:
        estimated_cost = (
            (estimated_input / 1000) * self.cost_per_1k_input +
            (estimated_output / 1000) * self.cost_per_1k_output
        )

        spent = sum(t.total_cost for t in self.trackers.values())
        return (spent + estimated_cost) <= self.total_budget

    def get_spent(self) -> float:
        return sum(t.total_cost for t in self.trackers.values())

    def get_remaining(self) -> float:
        return self.total_budget - self.get_spent()
```

### 2. Budget-Constrained Agent

```python
class BudgetAwareAgent(autogen.AssistantAgent):
    def __init__(self, *args, budget_manager: AutoGenBudgetManager, **kwargs):
        super().__init__(*args, **kwargs)
        self.budget_manager = budget_manager

    def generate_reply(self, messages, sender, config):
        # Estimate token usage
        message_text = str(messages)
        estimated_input = len(message_text) // 4  # Rough estimate
        estimated_output = 500  # Conservative estimate

        # Check budget
        if not self.budget_manager.can_afford(estimated_input, estimated_output):
            return {
                "content": "Budget limit reached. Cannot process this request."
            }

        # Generate reply
        start_time = datetime.now()
        reply = super().generate_reply(messages, sender, config)
        end_time = datetime.now()

        # Track actual usage (if available)
        # Note: AutoGen doesn't always provide token counts, so estimate
        self.budget_manager.record_usage(
            self.name,
            estimated_input,
            estimated_output
        )

        return reply
```

## Best Practices

### ✅ DO:

1. **Leverage conversational patterns**
   - AutoGen excels at dialogue-based agent interaction
   - Use group chats for collaborative problem solving
   - Let agents negotiate and refine solutions together

2. **Implement human-in-the-loop strategically**
   - Use for critical decisions or approvals
   - Can be disabled for fully autonomous operation
   - Good for learning from human feedback

3. **Use code execution carefully**
   - Sandbox code execution environment
   - Limit execution time and resources
   - Validate code before execution

4. **Monitor conversation health**
   - Track conversation length and loops
   - Detect and break circular conversations
   - Implement max_round limits

5. **Budget for conversation overhead**
   - Multi-turn conversations use more tokens
   - Track both input and output tokens
   - Set per-conversation limits

### ❌ DON'T:

1. **Let conversations run indefinitely**
   - Always set max_round limits
   - Implement timeout mechanisms
   - Monitor for circular conversations

2. **Ignore conversation state**
   - Save important conversation state
   - Implement checkpoint/resume capabilities
   - Don't rely solely on in-memory state

3. **Overload agents with context**
   - Filter conversation history
   - Summarize long conversations
   - Be selective about what to include

4. **Skip error handling**
   - Agents can and will fail
   - Implement retry logic
   - Have fallback strategies

5. **Assume all agents succeed**
   - Monitor agent health
   - Implement recovery mechanisms
   - Handle partial failures gracefully

## Comparison with Alternatives

| Feature | AutoGen | LangChain | CrewAI | Custom |
|---------|---------|-----------|--------|--------|
| Conversational Model | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Human-in-the-Loop | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Code Execution | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| State Management | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Flexibility | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## When to Choose AutoGen

**Choose AutoGen if:**
- Your use case is naturally conversational
- You need human-in-the-loop capabilities
- Agents need to write and execute code
- You want Microsoft-backed support
- You need easy group chat orchestration

**Avoid AutoGen if:**
- You need complex stateful workflows (LangGraph is better)
- You want maximum architectural flexibility
- You need fine-grained control over agent behavior
- Your agents don't need conversational interaction

## Resources

- [Official Documentation](https://microsoft.github.io/autogen/)
- [AutoGen GitHub](https://github.com/microsoft/autogen)
- [Tutorials](https://microsoft.github.io/autogen/docs/Getting-Started)
- [Examples](https://github.com/microsoft/autogen/tree/main/notebook)

---

**Next**: [CrewAI Framework](crewai.md) | [Back to README](../README.md)
