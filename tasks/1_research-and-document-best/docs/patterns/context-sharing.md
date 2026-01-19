# Context Sharing Strategies

**Patterns and techniques for sharing information between agents in multi-agent systems**

---

## Overview

Context sharing is fundamental to multi-agent systems. Agents need to share information, coordinate actions, and maintain shared understanding. This document covers strategies for effective, secure, and efficient context sharing.

## Core Challenges

1. **Information Overload**: Too much context degrades performance
2. **Privacy/Security**: Sensitive data must be protected
3. **Consistency**: All agents need consistent view
4. **Latency**: Context sharing adds communication overhead
5. **Relevance**: Agents need relevant context, not everything

---

## 1. Message-Based Context Sharing

### Description
Agents share context through explicit messages. Simple, direct, and traceable.

### Implementation

```python
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ContextMessage:
    sender: str
    receiver: str
    context_type: str
    data: Dict[str, Any]
    timestamp: datetime

class ContextSharingAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.local_context: Dict[str, Any] = {}
        self.context_history: List[ContextMessage] = []

    def share_context(self, receiver: str, context_type: str, data: Dict[str, Any]):
        """Share context with another agent"""
        message = ContextMessage(
            sender=self.agent_id,
            receiver=receiver,
            context_type=context_type,
            data=data,
            timestamp=datetime.now()
        )
        self.context_history.append(message)
        # Send to receiver...
        return message

    def receive_context(self, message: ContextMessage):
        """Receive shared context"""
        self.context_history.append(message)
        self.local_context[message.context_type] = message.data

    def get_relevant_context(self, context_types: List[str]) -> Dict[str, Any]:
        """Get context of specific types"""
        return {
            ctx_type: self.local_context[ctx_type]
            for ctx_type in context_types
            if ctx_type in self.local_context
        }
```

### Benefits
- ✅ Explicit and traceable
- ✅ Type-safe context transfer
- ✅ Easy to audit
- ✅ Simple implementation

### Drawbacks
- ❌ Verbose for frequent sharing
- ❌ Requires active management
- ❌ Can duplicate data

---

## 2. Shared Memory / Blackboard Pattern

### Description
Common shared memory space where agents read and write information. Agents access shared state directly.

### Implementation

```python
from typing import Dict, Any, Optional, List
from threading import Lock
from datetime import datetime
import hashlib

class SharedBlackboard:
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._owners: Dict[str, str] = {}  # Who wrote this
        self._lock = Lock()
        self._subscribers: Dict[str, List[str]] = {}  # Key -> agent_ids

    def write(self, key: str, value: Any, agent_id: str):
        """Write to shared blackboard"""
        with self._lock:
            self._store[key] = value
            self._timestamps[key] = datetime.now()
            self._owners[key] = agent_id

            # Notify subscribers
            if key in self._subscribers:
                for subscriber_id in self._subscribers[key]:
                    # Notify subscriber...
                    pass

    def read(self, key: str, agent_id: str) -> Optional[Any]:
        """Read from shared blackboard"""
        with self._lock:
            value = self._store.get(key)
            # Log read access
            return value

    def subscribe(self, key: str, agent_id: str):
        """Subscribe to changes on a key"""
        with self._lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            self._subscribers[key].append(agent_id)

    def read_with_history(self, key: str) -> Dict[str, Any]:
        """Read value with metadata"""
        with self._lock:
            if key not in self._store:
                return None
            return {
                "value": self._store[key],
                "timestamp": self._timestamps[key],
                "owner": self._owners[key]
            }

    def find_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """Find all keys with prefix"""
        with self._lock:
            return {
                k: v for k, v in self._store.items()
                if k.startswith(prefix)
            }

    def get_state_hash(self) -> str:
        """Get hash of current state for change detection"""
        with self._lock:
            state_str = str(sorted(self._store.items()))
            return hashlib.md5(state_str.encode()).hexdigest()

# Usage
blackboard = SharedBlackboard()

# Agent 1 writes research results
blackboard.write("research.quantum_findings", {...}, "research_agent")

# Agent 2 reads research results
findings = blackboard.read("research.quantum_findings", "writer_agent")

# Agent 3 subscribes to research updates
blackboard.subscribe("research.*", "analyst_agent")
```

### Benefits
- ✅ Simple shared access
- ✅ Centralized state management
- ✅ Easy to implement
- ✅ Natural for shared artifacts

### Drawbacks
- ❌ Requires locking (contention)
- ❌ No access control by default
- ❌ Can become bottleneck
- ❌ Harder to scale

---

## 3. Context Partitioning by Access Level

### Description
Partition context based on security/access requirements. Agents only see context they're authorized for.

### Implementation

```python
from enum import Enum
from typing import Dict, Any, List

class AccessLevel(Enum):
    PUBLIC = 0      # All agents can see
    TEAM = 1        # Team members can see
    RESTRICTED = 2  # Specific agents only
    SECRET = 3      # Only admin agents

class PartitionedContextStore:
    def __init__(self):
        self.partitions: Dict[AccessLevel, Dict[str, Any]] = {
            level: {} for level in AccessLevel
        }
        self.agent_access: Dict[str, List[AccessLevel]] = {}

    def grant_access(self, agent_id: str, levels: List[AccessLevel]):
        """Grant access levels to an agent"""
        self.agent_access[agent_id] = levels

    def write(self, key: str, value: Any, level: AccessLevel):
        """Write data at access level"""
        self.partitions[level][key] = value

    def read(self, agent_id: str, key: str) -> Any:
        """Read key if agent has access"""
        # Find the highest level where key exists
        for level in reversed(list(AccessLevel)):
            if key in self.partitions[level]:
                if level in self.agent_access.get(agent_id, []):
                    return self.partitions[level][key]
        return None

    def get_all_context(self, agent_id: str) -> Dict[str, Any]:
        """Get all context accessible to agent"""
        context = {}
        for level in self.agent_access.get(agent_id, []):
            context.update(self.partitions[level])
        return context

    def copy_key(self, key: str, from_level: AccessLevel, to_level: AccessLevel):
        """Copy key to different access level (e.g., sanitize)"""
        if key in self.partitions[from_level]:
            self.partitions[to_level][key] = self._sanitize(
                self.partitions[from_level][key],
                to_level
            )

    def _sanitize(self, value: Any, target_level: AccessLevel) -> Any:
        """Sanitize data for target access level"""
        # Implement sanitization logic
        if target_level == AccessLevel.PUBLIC:
            # Remove sensitive fields
            if isinstance(value, dict):
                return {k: v for k, v in value.items()
                       if not k.startswith("private_")}
        return value

# Usage
context_store = PartitionedContextStore()

# Define access
context_store.grant_access("public_agent", [AccessLevel.PUBLIC])
context_store.grant_access("team_agent", [AccessLevel.PUBLIC, AccessLevel.TEAM])
context_store.grant_access("admin_agent", [AccessLevel.PUBLIC, AccessLevel.TEAM,
                                           AccessLevel.RESTRICTED, AccessLevel.SECRET])

# Write data at different levels
context_store.write("project_status", {"status": "on_track"}, AccessLevel.PUBLIC)
context_store.write("api_key", "sk-...", AccessLevel.SECRET)
context_store.write("team_metrics", {...}, AccessLevel.TEAM)

# Agents can only read what they have access to
public_context = context_store.get_all_context("public_agent")
# Only has "project_status"

admin_context = context_store.get_all_context("admin_agent")
# Has everything
```

### Benefits
- ✅ Security by design
- ✅ Clear access boundaries
- ✅ Prevents information leakage
- ✅ Compliant with security requirements

### Drawbacks
- ❌ More complex access logic
- ❌ Requires access management
- ❌ Can hinder collaboration
- ❌ Overhead of checking permissions

---

## 4. Context Propagation

### Description
Context automatically propagates through agent chain. Each agent adds/transforms context and passes it on.

### Implementation

```python
from typing import Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Context:
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def add(self, key: str, value: Any, agent_id: str):
        """Add context entry"""
        self.data[key] = {
            "value": value,
            "added_by": agent_id,
            "timestamp": datetime.now()
        }

    def get(self, key: str) -> Any:
        """Get context value"""
        entry = self.data.get(key)
        return entry["value"] if entry else None

    def get_metadata(self, key: str) -> Dict[str, Any]:
        """Get context metadata"""
        return self.data.get(key, {})

    def clone(self) -> 'Context':
        """Create a copy of context"""
        return Context(
            data=self.data.copy(),
            history=self.history.copy(),
            timestamp=datetime.now()
        )

class ContextAwareAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def process(self, context: Context, input_data: Dict[str, Any]) -> Context:
        """Process input with context, return updated context"""
        # Read from context
        previous_results = context.get("previous_results")

        # Do work
        result = self._do_work(input_data, previous_results)

        # Update context
        context.add(f"{self.agent_id}_result", result, self.agent_id)
        context.history.append({
            "agent": self.agent_id,
            "timestamp": datetime.now(),
            "input": input_data
        })

        return context

    def _do_work(self, input_data: Dict, previous_results: Any) -> Any:
        """Override in subclasses"""
        return {"output": f"Processed by {self.agent_id}"}

# Pipeline with context propagation
def run_pipeline(agents: List[ContextAwareAgent], initial_input: Dict) -> Context:
    context = Context()

    for agent in agents:
        print(f"Agent {agent.agent_id} processing...")
        context = agent.process(context, initial_input)

    return context

# Usage
agent1 = ContextAwareAgent("researcher")
agent2 = ContextAwareAgent("writer")
agent3 = ContextAwareAgent("editor")

final_context = run_pipeline(
    [agent1, agent2, agent3],
    {"topic": "quantum computing"}
)

print(f"Final context: {final_context.data}")
```

### Benefits
- ✅ Natural flow of information
- ✅ Maintains provenance
- ✅ Easy to trace
- ✅ Works well with pipelines

### Drawbacks
- ❌ Context can grow large
- ❌ May contain stale data
- ❌ Hard to prune
- ❌ Sequential dependency

---

## 5. Summarization and Compression

### Description
Compress context to fit token limits while preserving important information.

### Implementation

```python
from typing import Dict, Any, List
import heapq

class ContextCompressor:
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens

    def compress_by_importance(self, context: Dict[str, Any],
                               importance_scores: Dict[str, float]) -> Dict[str, Any]:
        """Compress context by keeping most important items"""
        # Score each context item
        scored_items = [
            (key, importance_scores.get(key, 0.0))
            for key in context.keys()
        ]

        # Sort by importance
        scored_items.sort(key=lambda x: x[1], reverse=True)

        # Keep items until token limit
        compressed = {}
        current_tokens = 0

        for key, score in scored_items:
            item_tokens = self._estimate_tokens(context[key])
            if current_tokens + item_tokens <= self.max_tokens:
                compressed[key] = context[key]
                current_tokens += item_tokens
            else:
                break

        return compressed

    def compress_by_recency(self, context_list: List[Dict],
                           keep_count: int = 10) -> List[Dict]:
        """Keep only most recent context items"""
        return context_list[-keep_count:]

    def summarize_context(self, context: Dict[str, Any],
                         llm_summarizer: callable = None) -> Dict[str, Any]:
        """Summarize context using LLM or rules"""
        if llm_summarizer:
            # Use LLM to summarize
            return llm_summarizer(context)
        else:
            # Rule-based summarization
            return self._rule_based_summarize(context)

    def _rule_based_summarize(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simple rule-based summarization"""
        summary = {}
        for key, value in context.items():
            if isinstance(value, dict):
                # Keep only top-level keys
                summary[key] = {k: v for k, v in value.items()
                               if k in ["status", "result", "error"]}
            elif isinstance(value, list):
                # Keep first and last items
                summary[key] = value[:1] + value[-1:] if len(value) > 2 else value
            else:
                summary[key] = str(value)[:100]  # Truncate
        return summary

    def _estimate_tokens(self, value: Any) -> int:
        """Estimate token count (rough approximation)"""
        return len(str(value)) // 4

# Usage
compressor = ContextCompressor(max_tokens=2000)

context = {
    "research_data": "..." * 1000,  # Large data
    "analysis": "..." * 500,
    "draft": "..." * 800,
    "metadata": "..." * 200
}

importance = {
    "research_data": 0.8,
    "analysis": 0.6,
    "draft": 0.9,
    "metadata": 0.3
}

compressed = compressor.compress_by_importance(context, importance)
```

### Benefits
- ✅ Reduces token usage
- ✅ Keeps relevant information
- ✅ Fits within limits
- ✅ Can use LLM for smart summarization

### Drawbacks
- ❌ May lose important details
- ❌ Requires importance scoring
- ❌ Adds computational overhead
- ❌ Quality depends on summarization method

---

## Best Practices

### ✅ DO:

1. **Minimize shared context**
   - Share only what's needed
   - Filter by relevance
   - Use references instead of copying

2. **Sanitize sensitive data**
   - Remove API keys, passwords
   - Anonymize user data
   - Apply access controls

3. **Track context provenance**
   - Who added what
   - When it was added
   - Source of information

4. **Version important context**
   - Track changes over time
   - Enable rollback if needed
   - Maintain audit trail

5. **Monitor context size**
   - Limit token usage
   - Compress when necessary
   - Prune stale data

### ❌ DON'T:

1. **Share raw user input**
   - Sanitize first
   - Remove PII
   - Check for malicious content

2. **Ignore token limits**
   - Context grows unbounded
   - Will hit API limits
   - Degrades performance

3. **Assume consistency**
   - Agents may have stale context
   - Network delays cause inconsistencies
   - Design for eventual consistency

4. **Forget access control**
   - Not all agents need all context
   - Security implications
   - Privacy requirements

---

## Choosing the Right Strategy

| Strategy | Use When |
|----------|----------|
| Message-Based | Explicit, traceable sharing needed |
| Shared Memory | Simple shared access, small scale |
| Partitioned | Security/access control required |
| Propagation | Pipeline workflows |
| Summarization | Token limits, large context |

**Next**: [Task Distribution Patterns](task-distribution.md) | [Back to README](../README.md)
