# Budget Management Strategies

**Cost control and optimization for multi-agent systems**

---

## Overview

Multi-agent systems can quickly become expensive due to multiple LLM calls. Effective budget management is essential for 24/7 operation.

## Cost Factors

1. **Input tokens**: Context sent to LLM per request
2. **Output tokens**: LLM response length
3. **Request frequency**: How often agents call LLM
4. **Model pricing**: GPT-4 vs GPT-3.5, etc.
5. **Agent count**: More agents = more cost

## Rule of Thumb

**Budget = (Single Agent Cost) × (Number of Agents) × (Overhead Multiplier)**

- Overhead multiplier: 2-5x depending on architecture
- Accounts for repeated context, coordination messages, retries

---

## 1. Per-Agent Budget Tracking

```python
from dataclasses import dataclass
from typing import Dict
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
            budget.request_count += 1

            cost = ((input_tokens / 1000) * self.input_cost +
                   (output_tokens / 1000) * self.output_cost)
            budget.total_cost += cost

    def can_afford(self, agent_id: str, estimated_tokens: int) -> bool:
        with self._lock:
            spent = sum(b.total_cost for b in self.budgets.values())
            estimated_cost = (estimated_tokens / 1000) * self.input_cost
            return (spent + estimated_cost) <= self.total_budget

    def get_remaining(self) -> float:
        with self._lock:
            spent = sum(b.total_cost for b in self.budgets.values())
            return self.total_budget - spent

    def get_report(self) -> dict:
        with self._lock:
            return {
                "total_budget": self.total_budget,
                "spent": sum(b.total_cost for b in self.budgets.values()),
                "remaining": self.get_remaining(),
                "by_agent": {
                    agent_id: {
                        "spent": b.total_cost,
                        "tokens": b.input_tokens + b.output_tokens,
                        "requests": b.request_count
                    }
                    for agent_id, b in self.budgets.items()
                }
            }
```

---

## 2. Cost Optimization Strategies

### Cache Repeated Queries

```python
from typing import Dict, Tuple
import hashlib

class ResultCache:
    def __init__(self, ttl: int = 3600):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl

    def _hash_input(self, input_data: dict) -> str:
        input_str = str(sorted(input_data.items()))
        return hashlib.md5(input_str.encode()).hexdigest()

    def get(self, input_data: dict) -> Any:
        key = self._hash_input(input_data)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return result
        return None

    def set(self, input_data: dict, result: Any):
        key = self._hash_input(input_data)
        self.cache[key] = (result, time.time())
```

### Use Cheaper Models When Possible

```python
class ModelSelector:
    def __init__(self):
        self.model_costs = {
            "gpt-4": 0.03,  # per 1k tokens
            "gpt-3.5-turbo": 0.002
        }

    def select_model(self, task_complexity: str) -> str:
        if task_complexity == "simple":
            return "gpt-3.5-turbo"
        elif task_complexity == "complex":
            return "gpt-4"
        else:
            return "gpt-3.5-turbo"  # Default to cheaper
```

### Limit Context Size

```python
def trim_context(messages: list, max_tokens: int = 2000) -> list:
    """Keep only recent messages within token limit"""
    total_tokens = 0
    trimmed = []

    for msg in reversed(messages):
        token_count = len(msg["content"]) // 4
        if total_tokens + token_count > max_tokens:
            break
        trimmed.insert(0, msg)
        total_tokens += token_count

    return trimmed
```

---

## 3. Budget-Constrained Agent Wrapper

```python
class BudgetConstrainedAgent:
    def __init__(self, agent, agent_id: str, budget_manager: BudgetManager):
        self.agent = agent
        self.agent_id = agent_id
        self.budget_manager = budget_manager

    async def execute(self, task: dict) -> dict:
        # Check if we can afford this request
        estimated_tokens = len(str(task)) // 4

        if not self.budget_manager.can_afford(self.agent_id, estimated_tokens):
            raise Exception(f"Budget exceeded for agent {self.agent_id}")

        # Execute normally
        result = await self.agent.execute(task)

        # Record actual usage (would get from API response)
        actual_tokens = estimated_tokens
        self.budget_manager.record_usage(self.agent_id, actual_tokens, actual_tokens // 2)

        return result
```

---

## Best Practices

### ✅ DO:

1. **Track costs per agent**
   - Know which agents are expensive
   - Identify optimization opportunities
   - Allocate budget appropriately

2. **Cache aggressively**
   - Repeated queries are common
   - Cache LLM responses
   - Share cache between agents

3. **Use model hierarchy**
   - Simple tasks: cheaper models
   - Complex tasks: better models
   - Route appropriately

4. **Compress context**
   - Summarize long conversations
   - Keep only recent messages
   - Remove redundant information

5. **Set spending limits**
   - Per-agent limits
   - Global daily/monthly limits
   - Alert when approaching limits

### ❌ DON'T:

1. **Ignore token costs**
   - Multi-agent systems multiply costs
   - Always track usage
   - Budget conservatively (2-3x estimates)

2. **Send full context every time**
   - Wastes tokens
   - Slows responses
   - Increases costs

3. **Use expensive models unnecessarily**
   - GPT-4 for everything
   - Match model to task
   - Start with cheaper models

4. **Skip caching**
   - Same queries processed repeatedly
   - Wasteful spending
   - Poor performance

---

## Budget Planning

### Example Cost Calculation

**Scenario**: 5 agents, 100 tasks/day, average 1000 tokens per task

```
Single agent cost:
- 100 tasks × 1000 tokens = 100k tokens/day
- 100k × $0.002/1k = $0.20/day per agent

5 agents:
- $0.20 × 5 = $1.00/day base cost

With 3x overhead for context sharing, coordination:
- $1.00 × 3 = $3.00/day

Monthly:
- $3.00 × 30 = $90/month
```

**Budget Recommendation**: Multiply base estimate by 3-5x for safety.

---

**Next**: [Knowledge Sharing](knowledge-sharing.md) | [Back to README](../README.md)
