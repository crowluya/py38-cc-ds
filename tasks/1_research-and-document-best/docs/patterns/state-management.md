# State Management Architectures

**Patterns for managing distributed state in multi-agent systems**

---

## Overview

State management in multi-agent systems involves maintaining consistent, accessible, and reliable state across distributed agents. Proper state management is crucial for coordination, recovery, and system reliability.

## Core Challenges

1. **Consistency**: All agents see consistent state
2. **Availability**: State accessible when needed
3. **Partition Tolerance**: Works despite network failures
4. **Scalability**: Handles many agents and operations
5. **Durability**: State survives failures

**CAP Tradeoff**: Can only guarantee 2 of Consistency, Availability, Partition Tolerance.

---

## 1. Centralized State Store

### Description
Single source of truth for all state. All agents read/write to central store.

### Architecture

```
┌────────────────────────────────────────┐
│       Centralized State Store          │
│  - Single source of truth              │
│  - All agents connect to it            │
│  - Handles all read/write operations   │
└────┬────┬────┬────┬────┬────┬────┬─────┘
     │    │    │    │    │    │    │
     ▼    ▼    ▼    ▼    ▼    ▼    ▼
   [A1] [A2] [A3] [A4] [A5] [A6] [A7]
```

### Implementation

```python
from typing import Dict, Any, Optional
import threading
from datetime import datetime
import json

class CentralizedStateStore:
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._timestamps: Dict[str, datetime] = {}
        self._version: int = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        with self._lock:
            return self._state.get(key)

    def set(self, key: str, value: Any) -> int:
        """Set value, return new version"""
        with self._lock:
            self._state[key] = value
            self._timestamps[key] = datetime.now()
            self._version += 1
            return self._version

    def get_all(self) -> Dict[str, Any]:
        """Get all state"""
        with self._lock:
            return self._state.copy()

    def update(self, updates: Dict[str, Any]) -> int:
        """Update multiple keys atomically"""
        with self._lock:
            for key, value in updates.items():
                self._state[key] = value
                self._timestamps[key] = datetime.now()
            self._version += 1
            return self._version

    def delete(self, key: str):
        """Delete key"""
        with self._lock:
            if key in self._state:
                del self._state[key]
                del self._timestamps[key]
                self._version += 1

    def get_version(self) -> int:
        """Get current version"""
        with self._lock:
            return self._version

    def get_versioned(self, key: str, version: int) -> Optional[Any]:
        """Get value as of specific version (requires history tracking)"""
        # Would need to implement version history
        return self.get(key)

    def snapshot(self) -> str:
        """Create JSON snapshot"""
        with self._lock:
            return json.dumps({
                "state": self._state,
                "version": self._version,
                "timestamps": {k: v.isoformat() for k, v in self._timestamps.items()}
            })

    def restore(self, snapshot: str):
        """Restore from snapshot"""
        with self._lock:
            data = json.loads(snapshot)
            self._state = data["state"]
            self._version = data["version"]
            self._timestamps = {
                k: datetime.fromisoformat(v)
                for k, v in data["timestamps"].items()
            }

# Usage
state_store = CentralizedStateStore()

# Agent 1 writes state
state_store.set("agent1.position", {"x": 10, "y": 20})

# Agent 2 reads state
position = state_store.get("agent1.position")

# Agent 3 updates multiple keys atomically
state_store.update({
    "agent1.position": {"x": 15, "y": 25},
    "agent1.status": "moving"
})
```

### Benefits
- ✅ Simple to understand
- ✅ Strong consistency
- ✅ Easy to debug
- ✅ Single source of truth

### Drawbacks
- ❌ Single point of failure
- ❌ Performance bottleneck
- ❌ Doesn't scale well
- ❌ Network latency for all operations

---

## 2. Distributed State with Event Sourcing

### Description
State stored as sequence of events. Current state derived by replaying events.

### Architecture

```
Events:
  [e1] -> [e2] -> [e3] -> [e4] -> [e5]
    │       │       │       │       │
    └───────┴───────┴───────┴───────┘
                │
         Event Log (immutable)
                │
         Replay to get state
                │
         Current State View
```

### Implementation

```python
from typing import List, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class Event:
    event_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    version: int

class EventStore:
    def __init__(self):
        self.events: List[Event] = []
        self.subscribers: Dict[str, List[Callable]] = {}
        self._version = 0

    def append(self, event_type: str, data: Dict[str, Any]) -> Event:
        """Append new event"""
        event = Event(
            event_id=f"{event_type}_{self._version}_{datetime.now().timestamp()}",
            event_type=event_type,
            data=data,
            timestamp=datetime.now(),
            version=self._version
        )
        self.events.append(event)
        self._version += 1

        # Notify subscribers
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(event)

        return event

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def get_events_since(self, version: int) -> List[Event]:
        """Get all events after version"""
        return self.events[version + 1:]

    def get_all_events(self) -> List[Event]:
        """Get all events"""
        return self.events.copy()

    def replay(self, event_type: str = None) -> Any:
        """Replay events to rebuild state"""
        events = self.events
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        state = {}
        for event in events:
            state = self._apply_event(state, event)

        return state

    def _apply_event(self, state: Dict, event: Event) -> Dict:
        """Apply event to state (override in subclass)"""
        state = state.copy()
        if event.event_type == "update_position":
            state["position"] = event.data
        elif event.event_type == "change_status":
            state["status"] = event.data["status"]
        return state

class StateView:
    """Read-only view of state derived from events"""
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self._cached_state = None
        self._cached_version = -1

    def get_state(self) -> Dict[str, Any]:
        """Get current state, cached if unchanged"""
        current_version = self.event_store._version - 1

        if self._cached_version != current_version:
            # Rebuild state from events
            self._cached_state = self.event_store.replay()
            self._cached_version = current_version

        return self._cached_state.copy()

# Usage
event_store = EventStore()

# Subscribe to events
def on_position_update(event: Event):
    print(f"Position updated: {event.data}")

event_store.subscribe("update_position", on_position_update)

# Append events (agents write state changes)
event_store.append("update_position", {"x": 10, "y": 20})
event_store.append("change_status", {"status": "moving"})
event_store.append("update_position", {"x": 15, "y": 25})

# Read current state
state_view = StateView(event_store)
current_state = state_view.get_state()
```

### Benefits
- ✅ Complete audit trail
- ✅ Can rebuild state at any point
- ✅ Natural support for temporal queries
- ✅ Good for replay/debugging

### Drawbacks
- ❌ More complex than simple state
- ❌ Replay can be expensive
- ❌ Requires event schema design
- ❌ eventual consistency

---

## 3. Partitioned State

### Description
State partitioned across multiple stores. Each partition handles subset of data.

### Architecture

```
        State Coordinator
              │
    ┌─────────┼─────────┐
    │         │         │
  Shard 1   Shard 2   Shard 3
  (Keys     (Keys     (Keys
   A-F)      G-P)     Q-Z)
```

### Implementation

```python
from typing import Dict, Any, List
import hashlib

class StatePartition:
    def __init__(self, partition_id: str):
        self.partition_id = partition_id
        self._state: Dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._state.get(key)

    def set(self, key: str, value: Any):
        self._state[key] = value

    def delete(self, key: str):
        if key in self._state:
            del self._state[key]

class PartitionedStateStore:
    def __init__(self, num_partitions: int = 3):
        self.partitions: List[StatePartition] = [
            StatePartition(f"partition_{i}")
            for i in range(num_partitions)
        ]
        self.num_partitions = num_partitions

    def _get_partition(self, key: str) -> StatePartition:
        """Hash key to determine partition"""
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        partition_idx = hash_value % self.num_partitions
        return self.partitions[partition_idx]

    def get(self, key: str) -> Any:
        """Get value from appropriate partition"""
        partition = self._get_partition(key)
        return partition.get(key)

    def set(self, key: str, value: Any):
        """Set value in appropriate partition"""
        partition = self._get_partition(key)
        partition.set(key, value)

    def delete(self, key: str):
        """Delete from appropriate partition"""
        partition = self._get_partition(key)
        partition.delete(key)

    def get_all(self) -> Dict[str, Any]:
        """Get all state from all partitions"""
        all_state = {}
        for partition in self.partitions:
            all_state.update(partition._state)
        return all_state

# Usage
store = PartitionedStateStore(num_partitions=3)

# These will go to different partitions
store.set("agent1_position", {"x": 10})
store.set("agent2_position", {"x": 20})
store.set("agent3_position", {"x": 30})

# Still accessed transparently
pos1 = store.get("agent1_position")
pos2 = store.get("agent2_position")
```

### Benefits
- ✅ Scales better than centralized
- ✅ Natural load distribution
- ✅ Can parallelize operations
- ✅ Fault isolation

### Drawbacks
- ❌ More complex architecture
- ❌ Cross-partition transactions hard
- ❌ Rebalancing needed
- ❌ Some operations require all partitions

---

## 4. Gossip Protocol (CRDTs)

### Description
State eventually consistent through gossip. Conflict-free Replicated Data Types (CRDTs) resolve conflicts.

### Implementation

```python
from typing import Dict, Any, Set, List
import random
from datetime import datetime

class GossipNode:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.state: Dict[str, Any] = {}
        self.version_vector: Dict[str, int] = {}
        self.peers: List['GossipNode'] = []

    def add_peer(self, peer: 'GossipNode'):
        """Add a peer to gossip with"""
        if peer.node_id != self.node_id:
            self.peers.append(peer)

    def write(self, key: str, value: Any):
        """Write to local state"""
        self.state[key] = value
        self.version_vector[key] = self.version_vector.get(key, 0) + 1

    def read(self, key: str) -> Any:
        """Read from local state"""
        return self.state.get(key)

    def gossip(self):
        """Share state with random peer"""
        if not self.peers:
            return

        peer = random.choice(self.peers)
        self._sync_with_peer(peer)

    def _sync_with_peer(self, peer: 'GossipNode'):
        """Merge state with peer"""
        # Merge version vectors
        for key in set(self.version_vector.keys()) | set(peer.version_vector.keys()):
            my_version = self.version_vector.get(key, 0)
            peer_version = peer.version_vector.get(key, 0)

            if peer_version > my_version:
                # Peer has newer version, accept it
                self.state[key] = peer.state[key]
                self.version_vector[key] = peer_version
            elif my_version > peer_version:
                # I have newer version, send to peer
                peer.state[key] = self.state[key]
                peer.version_vector[key] = my_version

class GossipCluster:
    def __init__(self, num_nodes: int):
        self.nodes = [GossipNode(f"node_{i}") for i in range(num_nodes)]
        self._connect_nodes()

    def _connect_nodes(self):
        """Connect nodes in mesh topology"""
        for node in self.nodes:
            for peer in self.nodes:
                if peer.node_id != node.node_id:
                    node.add_peer(peer)

    def run_gossip_round(self):
        """Execute one round of gossip"""
        for node in self.nodes:
            node.gossip()

    def get_converged_state(self) -> Dict[str, Any]:
        """Check if state has converged across all nodes"""
        # Use first node's state as reference
        reference = self.nodes[0].state

        for node in self.nodes[1:]:
            if node.state != reference:
                return None  # Not converged

        return reference

# Usage
cluster = GossipCluster(num_nodes=5)

# Node 0 writes
cluster.nodes[0].write("key1", "value1")

# Run gossip rounds to propagate
for i in range(10):
    cluster.run_gossip_round()

# Check convergence
converged = cluster.get_converged_state()
if converged:
    print("State converged!")
```

### Benefits
- ✅ No single point of failure
- ✅ Highly available
- ✅ Scales well
- ✅ Works despite network partitions

### Drawbacks
- ❌ Eventual consistency (not immediate)
- ❌ Complex conflict resolution
- ❌ High network traffic
- ❌ Convergence can be slow

---

## Comparison

| Pattern | Consistency | Availability | Scalability | Complexity |
|---------|-------------|--------------|-------------|------------|
| Centralized | Strong | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| Event Sourcing | Eventual | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Partitioned | Configurable | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Gossip/CRDT | Eventual | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Best Practices

### ✅ DO:

1. **Choose right consistency model**
   - Strong consistency when needed (financial, etc.)
   - Eventual consistency for scalability
   - Don't pay for consistency you don't need

2. **Implement health checks**
   - Monitor state store health
   - Detect failures early
   - Have fallback strategies

3. **Back up critical state**
   - Regular snapshots
   - Point-in-time recovery
   - Test restore procedures

4. **Version your state**
   - Track changes over time
   - Enable rollback
   - Audit trail

### ❌ DON'T:

1. **Ignore network latency**
   - Distributed state has delays
   - Design async operations
   - Don't assume immediate consistency

2. **Forget partition handling**
   - Cross-partition operations are complex
   - Design partitioning strategy carefully
   - Consider rebalancing

3. **Skip conflict resolution**
   - Conflicts will happen
   - Have clear resolution strategy
   - Test conflict scenarios

---

**Next**: [24/7 Operations](../operational-concerns/24-7-operations.md) | [Back to README](../README.md)
