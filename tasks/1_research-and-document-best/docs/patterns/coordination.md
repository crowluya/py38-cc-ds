# Agent Coordination Patterns

**Architectural patterns for orchestrating multi-agent communication and collaboration**

---

## Overview

Coordination patterns define how agents interact, communicate, and work together to accomplish tasks. The right coordination pattern is crucial for system performance, reliability, and maintainability.

## Pattern Categories

1. **Centralized Orchestration** - Single coordinator directs all agents
2. **Peer-to-Peer** - Agents communicate directly without central authority
3. **Hierarchical** - Multi-level coordination with managers and workers
4. **Swarm Intelligence** - Decentralized, emergent coordination
5. **Consensus-Based** - Agents agree on decisions through voting

---

## 1. Centralized Orchestration

### Description
A central coordinator (orchestrator) manages all agent interactions, task distribution, and result aggregation.

### Architecture

```
┌─────────────────────────────────────────┐
│         Orchestrator Agent              │
│  - Receives tasks                       │
│  - Plans execution                      │
│  - Distributes work                     │
│  - Aggregates results                   │
└────┬────┬────┬────┬────┬────┬────┬─────┘
     │    │    │    │    │    │    │
     ▼    ▼    ▼    ▼    ▼    ▼    ▼
   [A1] [A2] [A3] [A4] [A5] [A6] [A7]
     │    │    │    │    │    │    │
     └────┴────┴────┴────┴────┴────┘
              │
         Results back
         to Orchestrator
```

### Implementation

```python
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    type: str
    data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: str = None
    result: Any = None
    dependencies: List[str] = None

class CentralizedOrchestrator:
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[str] = []
        self.results: Dict[str, Any] = {}

    def register_agent(self, agent_id: str, agent: Any, capabilities: List[str]):
        """Register an agent with its capabilities"""
        self.agents[agent_id] = {
            "agent": agent,
            "capabilities": capabilities,
            "busy": False
        }

    async def submit_task(self, task: Task) -> str:
        """Submit a task for execution"""
        self.tasks[task.id] = task
        self.task_queue.append(task.id)
        return task.id

    async def orchestrate(self):
        """Main orchestration loop"""
        while self.task_queue:
            task_id = self.task_queue.pop(0)
            task = self.tasks[task_id]

            # Check dependencies
            if task.dependencies:
                if not all(
                    self.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                ):
                    # Dependencies not met, requeue
                    self.task_queue.append(task_id)
                    continue

            # Find available agent
            agent_id = self._find_agent_for_task(task)
            if agent_id is None:
                # No agent available, requeue
                self.task_queue.append(task_id)
                await asyncio.sleep(0.1)
                continue

            # Assign task
            await self._execute_task(task_id, agent_id)

    def _find_agent_for_task(self, task: Task) -> str:
        """Find an available agent capable of executing the task"""
        for agent_id, agent_info in self.agents.items():
            if not agent_info["busy"] and task.type in agent_info["capabilities"]:
                return agent_id
        return None

    async def _execute_task(self, task_id: str, agent_id: str):
        """Execute a task on an agent"""
        task = self.tasks[task_id]
        agent = self.agents[agent_id]["agent"]

        task.status = TaskStatus.ASSIGNED
        task.assigned_agent = agent_id
        self.agents[agent_id]["busy"] = True

        try:
            result = await agent.execute(task.data)
            task.status = TaskStatus.COMPLETED
            task.result = result
            self.results[task_id] = result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.result = {"error": str(e)}
        finally:
            self.agents[agent_id]["busy"] = False

# Example usage
class MockAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    async def execute(self, task_data: dict) -> dict:
        await asyncio.sleep(0.1)  # Simulate work
        return {
            "agent": self.agent_id,
            "result": f"Processed {task_data.get('input')}"
        }

orchestrator = CentralizedOrchestrator()

# Register agents
orchestrator.register_agent("agent1", MockAgent("agent1"), ["research", "analysis"])
orchestrator.register_agent("agent2", MockAgent("agent2"), ["writing", "editing"])
orchestrator.register_agent("agent3", MockAgent("agent3"), ["analysis", "research"])

# Submit tasks
task1 = Task(id="t1", type="research", data={"query": "AI"})
task2 = Task(id="t2", type="writing", data={"topic": "ML"}, dependencies=["t1"])

await orchestrator.submit_task(task1)
await orchestrator.submit_task(task2)

# Orchestrate
await orchestrator.orchestrate()
```

### Benefits
- ✅ Simple to understand and implement
- ✅ Easy to debug and monitor
- ✅ Global optimization possible
- ✅ Straightforward error handling

### Drawbacks
- ❌ Single point of failure
- ❌ Bottleneck for scalability
- ❌ Orchestrator complexity grows with system size
- ❌ Can become a performance bottleneck

### When to Use
- Small to medium systems (2-20 agents)
- Tasks with clear dependencies
- Need for global coordination
- Simple linear or DAG workflows

---

## 2. Peer-to-Peer Coordination

### Description
Agents communicate directly with each other without a central coordinator. Each agent knows about others and can initiate communication.

### Architecture

```
     ┌──────────────────────────────────┐
     │                                  │
     ▼                                  ▼
┌─────────┐     ┌─────────┐     ┌─────────┐
│ Agent 1 │◄───►│ Agent 2 │◄───►│ Agent 3 │
└─────────┘     └─────────┘     └─────────┘
     ▲               ▲               ▲
     │               │               │
     └───────────────┴───────────────┘
           Direct communication
              between agents
```

### Implementation

```python
from typing import Dict, List, Callable, Any
import asyncio
from dataclasses import dataclass
import json

@dataclass
class Message:
    sender: str
    receiver: str
    content: Any
    message_id: str
    timestamp: float

class PeerToPeerAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.message_queue = asyncio.Queue()
        self.peers: Dict[str, 'PeerToPeerAgent'] = {}
        self.handlers: Dict[str, Callable] = {}
        self.running = False

    def add_peer(self, peer: 'PeerToPeerAgent'):
        """Add a peer agent"""
        self.peers[peer.agent_id] = peer

    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler"""
        self.handlers[message_type] = handler

    async def send(self, receiver_id: str, message_type: str, content: Any):
        """Send a message to a peer"""
        if receiver_id not in self.peers:
            raise ValueError(f"Unknown peer: {receiver_id}")

        message = Message(
            sender=self.agent_id,
            receiver=receiver_id,
            content={"type": message_type, "data": content},
            message_id=f"{self.agent_id}_{asyncio.get_event_loop().time()}",
            timestamp=asyncio.get_event_loop().time()
        )

        await self.peers[receiver_id].receive(message)

    async def receive(self, message: Message):
        """Receive a message"""
        await self.message_queue.put(message)

    async def start(self):
        """Start the agent's message processing loop"""
        self.running = True
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )

                message_type = message.content.get("type")
                handler = self.handlers.get(message_type)

                if handler:
                    await handler(message)
                else:
                    print(f"No handler for {message_type}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error processing message: {e}")

    def stop(self):
        self.running = False

class PeerToPeerNetwork:
    def __init__(self):
        self.agents: Dict[str, PeerToPeerAgent] = {}

    def add_agent(self, agent: PeerToPeerAgent):
        """Add an agent to the network"""
        self.agents[agent.agent_id] = agent
        # Connect to all existing agents
        for existing_agent in self.agents.values():
            if existing_agent.agent_id != agent.agent_id:
                agent.add_peer(existing_agent)
                existing_agent.add_peer(agent)

    async def broadcast(self, sender_id: str, message_type: str, content: Any):
        """Broadcast a message to all agents"""
        sender = self.agents.get(sender_id)
        if not sender:
            raise ValueError(f"Unknown sender: {sender_id}")

        tasks = [
            sender.send(peer_id, message_type, content)
            for peer_id in sender.peers.keys()
        ]
        await asyncio.gather(*tasks)

# Example usage
network = PeerToPeerNetwork()

# Create agents
agent1 = PeerToPeerAgent("researcher")
agent2 = PeerToPeerAgent("writer")
agent3 = PeerToPeerAgent("editor")

# Register handlers
async def handle_research_request(message: Message):
    print(f"Researcher received: {message.content['data']}")
    # Do research...
    await agent1.send(
        message.sender,
        "research_result",
        {"data": "Research results"}
    )

async def handle_research_result(message: Message):
    print(f"Writer received research results")
    # Write content...

agent1.register_handler("research_request", handle_research_request)
agent2.register_handler("research_result", handle_research_result)

# Add to network
network.add_agent(agent1)
network.add_agent(agent2)
network.add_agent(agent3)

# Start agents
await asyncio.gather(
    agent1.start(),
    agent2.start(),
    agent3.start()
)

# Send message
await agent2.send("researcher", "research_request", {"query": "AI"})
```

### Benefits
- ✅ No single point of failure
- ✅ Highly scalable
- ✅ Direct communication is fast
- ✅ Decentralized control

### Drawbacks
- ❌ Complex coordination logic
- ❌ Harder to debug and monitor
- ❌ No global view of system state
- ❌ Requires discovery mechanism for dynamic agents

### When to Use
- Large-scale systems (20+ agents)
- Fault tolerance is critical
- Agents need direct communication
- Decentralized control is desired

---

## 3. Hierarchical Coordination

### Description
Multi-level coordination where higher-level managers coordinate lower-level workers. Combines benefits of centralized and peer-to-peer patterns.

### Architecture

```
┌─────────────────────────────────────────┐
│           Level 3: Director             │
│      Coordinates team leads              │
└──────┬──────────────┬──────────────┬────┘
       │              │              │
       ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Level 2:    │ │ Level 2:    │ │ Level 2:    │
│ Team Lead 1 │ │ Team Lead 2 │ │ Team Lead 3 │
└──┬──────┬───┘ └──┬──────┬───┘ └──┬──────┬───┘
   │      │        │      │        │      │
   ▼      ▼        ▼      ▼        ▼      ▼
 [W1]   [W2]     [W3]   [W4]     [W5]   [W6]
 Level 1: Workers
```

### Implementation

```python
from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio

class AgentLevel(Enum):
    DIRECTOR = 3
    TEAM_LEAD = 2
    WORKER = 1

class HierarchicalAgent:
    def __init__(self, agent_id: str, level: AgentLevel):
        self.agent_id = agent_id
        self.level = level
        self.superior: Optional['HierarchicalAgent'] = None
        self.subordinates: List['HierarchicalAgent'] = []
        self.message_queue = asyncio.Queue()
        self.running = False

    def add_subordinate(self, agent: 'HierarchicalAgent'):
        """Add a subordinate agent"""
        self.subordinates.append(agent)
        agent.superior = self

    async def send_to_superior(self, message_type: str, content: Any):
        """Send a message up the hierarchy"""
        if self.superior:
            await self.superior.receive(self.agent_id, message_type, content)
        else:
            print(f"{self.agent_id} has no superior")

    async def send_to_subordinates(self, message_type: str, content: Any):
        """Send a message to all subordinates"""
        tasks = [
            subordinate.receive(self.agent_id, message_type, content)
            for subordinate in self.subordinates
        ]
        await asyncio.gather(*tasks)

    async def send_to_subordinate(self, subordinate_id: str,
                                   message_type: str, content: Any):
        """Send a message to a specific subordinate"""
        for subordinate in self.subordinates:
            if subordinate.agent_id == subordinate_id:
                await subordinate.receive(self.agent_id, message_type, content)
                return
        raise ValueError(f"Subordinate {subordinate_id} not found")

    async def receive(self, sender_id: str, message_type: str, content: Any):
        """Receive a message"""
        await self.message_queue.put((sender_id, message_type, content))

    async def start(self):
        """Start the agent's processing loop"""
        self.running = True
        while self.running:
            try:
                sender_id, message_type, content = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                await self.handle_message(sender_id, message_type, content)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error in {self.agent_id}: {e}")

    async def handle_message(self, sender_id: str, message_type: str, content: Any):
        """Handle incoming message - override in subclasses"""
        print(f"{self.agent_id} received {message_type} from {sender_id}")

    def stop(self):
        self.running = False

# Example specialized agents
class DirectorAgent(HierarchicalAgent):
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentLevel.DIRECTOR)
        self.project_status = {}

    async def handle_message(self, sender_id: str, message_type: str, content: Any):
        if message_type == "project_complete":
            print(f"Project {content['project_id']} completed!")
            self.project_status[content['project_id']] = "complete"
        elif message_type == "project_failed":
            print(f"Project {content['project_id']} failed: {content['error']}")
            self.project_status[content['project_id']] = "failed"

class TeamLeadAgent(HierarchicalAgent):
    def __init__(self, agent_id: str):
        super().__init__(agent_id, AgentLevel.TEAM_LEAD)
        self.current_tasks = {}

    async def handle_message(self, sender_id: str, message_type: str, content: Any):
        if message_type == "new_project":
            print(f"{self.agent_id} received project: {content['project_id']}")
            # Delegate to workers
            await self.send_to_subordinates("new_task", {
                "project_id": content['project_id'],
                "task": content['task']
            })
        elif message_type == "task_complete":
            print(f"Task completed by {sender_id}")
            # Check if project is complete
            project_id = content['project_id']
            # ... logic to track project completion ...

class WorkerAgent(HierarchicalAgent):
    def __init__(self, agent_id: str, specialty: str):
        super().__init__(agent_id, AgentLevel.WORKER)
        self.specialty = specialty

    async def handle_message(self, sender_id: str, message_type: str, content: Any):
        if message_type == "new_task":
            if content['task'].get('type') == self.specialty:
                print(f"{self.agent_id} working on task")
                await asyncio.sleep(0.1)  # Simulate work
                await self.send_to_superior("task_complete", {
                    "project_id": content['project_id'],
                    "worker": self.agent_id
                })

# Build hierarchy
director = DirectorAgent("director")
team_lead1 = TeamLeadAgent("team_lead1")
team_lead2 = TeamLeadAgent("team_lead2")

worker1 = WorkerAgent("worker1", "research")
worker2 = WorkerAgent("worker2", "writing")
worker3 = WorkerAgent("worker3", "editing")

director.add_subordinate(team_lead1)
director.add_subordinate(team_lead2)

team_lead1.add_subordinate(worker1)
team_lead1.add_subordinate(worker2)
team_lead2.add_subordinate(worker3)

# Start all agents
await asyncio.gather(
    director.start(),
    team_lead1.start(),
    team_lead2.start(),
    worker1.start(),
    worker2.start(),
    worker3.start()
)

# Send project to director
await director.send_to_subordinates("team_lead1", "new_project", {
    "project_id": "proj1",
    "task": {"type": "research", "query": "AI"}
})
```

### Benefits
- ✅ Clear chain of command
- ✅ Scales better than pure centralized
- ✅ Natural organization for complex systems
- ✅ Fault containment (failure doesn't propagate up)

### Drawbacks
- ❌ More complex than flat organization
- ❌ Communication latency through hierarchy
- ❌ Potential bottlenecks at higher levels
- ❌ Requires careful level design

### When to Use
- Medium to large systems (10-100 agents)
- Natural team/department structure
- Need for both coordination and autonomy
- Domain has hierarchical organization

---

## 4. Swarm Intelligence

### Description
Decentralized coordination where agents follow simple rules that lead to emergent collective behavior. No central authority or explicit coordination.

### Architecture

```
        ┌─────────────────────────────────┐
        │                                 │
    ┌───┴───┐   ┌───┴───┐   ┌───┴───┐     │
    │ Agent│   │ Agent│   │ Agent│     │
    │  1   │   │  2   │   │  3   │     │
    └───┬───┘   └───┬───┘   └───┬───┘     │
        │           │           │         │
        └───────────┴───────────┘         │
                   │                      │
            Local interactions            │
          (stigmergy, pheromones)         │
        │                                 │
        │   Emergent collective behavior  │
        └─────────────────────────────────┘
```

### Implementation

```python
import random
from typing import List, Dict, Any
from dataclasses import dataclass
import numpy as np

@dataclass
class EnvironmentState:
    """Shared environment with pheromone-like signals"""
    resource_density: Dict[str, float]
    pheromones: Dict[str, float]

class SwarmAgent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.position = (random.random(), random.random())  # 2D position
        self.state = "foraging"  # foraging, returning, resting
        self.carrying = None
        self.memory = []

    def perceive(self, environment: EnvironmentState) -> Dict[str, Any]:
        """Perceive local environment"""
        perception = {
            "position": self.position,
            "pheromones": self._sample_pheromones(environment),
            "resources": self._sample_resources(environment)
        }
        return perception

    def _sample_pheromones(self, env: EnvironmentState) -> Dict[str, float]:
        """Sample pheromones near current position"""
        # Simplified - in reality, would use distance-based sampling
        return {
            key: value * random.uniform(0.8, 1.2)
            for key, value in env.pheromones.items()
        }

    def _sample_resources(self, env: EnvironmentState) -> Dict[str, float]:
        """Sample resources near current position"""
        return {
            key: value * random.uniform(0.9, 1.1)
            for key, value in env.resource_density.items()
        }

    def decide(self, perception: Dict[str, Any]) -> str:
        """Decide next action based on perception"""
        if self.state == "foraging":
            # Follow pheromones to resources
            if perception["resources"]:
                best_resource = max(perception["resources"].items(),
                                   key=lambda x: x[1])[0]
                return f"move_to_{best_resource}"
            elif perception["pheromones"]:
                # Follow strongest pheromone
                strongest = max(perception["pheromones"].items(),
                              key=lambda x: x[1])[0]
                return f"follow_{strongest}"
            else:
                return "explore"

        elif self.state == "returning":
            return "return_to_base"

        return "wait"

    def act(self, action: str, environment: EnvironmentState):
        """Execute action, modifying environment"""
        if action.startswith("move_to_"):
            target = action.replace("move_to_", "")
            # Move towards target (simplified)
            self.position = (
                self.position[0] + random.uniform(-0.1, 0.1),
                self.position[1] + random.uniform(-0.1, 0.1)
            )

            # Deposit pheromone
            if "pheromones" not in environment.pheromones:
                environment.pheromones["trail"] = 0.0
            environment.pheromones["trail"] += 0.1

        elif action == "explore":
            # Random walk
            self.position = (
                max(0, min(1, self.position[0] + random.uniform(-0.2, 0.2))),
                max(0, min(1, self.position[1] + random.uniform(-0.2, 0.2)))
            )

        elif action == "return_to_base":
            # Return to origin
            self.position = (0.5, 0.5)  # Base position
            if self.carrying:
                # Deposit resource
                # ...
                self.carrying = None
                self.state = "foraging"

class Swarm:
    def __init__(self, num_agents: int):
        self.agents = [SwarmAgent(f"agent_{i}") for i in range(num_agents)]
        self.environment = EnvironmentState(
            resource_density={"source1": 1.0, "source2": 0.8},
            pheromones={}
        )

    def step(self):
        """Execute one step of swarm behavior"""
        for agent in self.agents:
            # Perceive
            perception = agent.perceive(self.environment)

            # Decide
            action = agent.decide(perception)

            # Act
            agent.act(action, self.environment)

        # Decay pheromones
        for key in self.environment.pheromones:
            self.environment.pheromones[key] *= 0.95

# Example usage
swarm = Swarm(num_agents=20)

for step in range(100):
    swarm.step()

    # Periodically check for convergence
    if step % 10 == 0:
        print(f"Step {step}")
        print(f"Pheromones: {swarm.environment.pheromones}")
```

### Benefits
- ✅ Highly scalable
- ✅ Robust to individual agent failures
- ✅ Emergent problem-solving
- ✅ Minimal coordination overhead

### Drawbacks
- ❌ Unpredictable behavior
- ❌ Hard to prove correctness
- ❌ May not converge to optimal solution
- ❌ Requires careful parameter tuning

### When to Use
- Very large systems (100+ agents)
- Fault tolerance is critical
- Optimization problems
- Exploration/discovery tasks

---

## Comparison Summary

| Pattern | Scalability | Complexity | Fault Tolerance | Predictability |
|---------|-------------|------------|-----------------|----------------|
| Centralized | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Peer-to-Peer | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Hierarchical | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Swarm | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## Choosing the Right Pattern

### Decision Tree

```
Start
  │
  ├─ Need strict control over execution order?
  │   ├─ Yes → Centralized Orchestration
  │   └─ No → Continue
  │
  ├─ System has natural hierarchy?
  │   ├─ Yes → Hierarchical Coordination
  │   └─ No → Continue
  │
  ├─ Fault tolerance critical?
  │   ├─ Yes → Peer-to-Peer or Swarm
  │   └─ No → Continue
  │
  ├─ Number of agents > 100?
  │   ├─ Yes → Swarm Intelligence
  │   └─ No → Peer-to-Peer
  │
  └─ Default: Centralized (simplest)
```

### Hybrid Approaches

Many production systems use hybrid patterns:

1. **Hierarchical + Centralized**: Each team has centralized coordinator, teams coordinate peer-to-peer
2. **Centralized + Swarm**: Central controller sets high-level goals, swarms execute locally
3. **Peer-to-Peer + Hierarchical**: Local peer groups, hierarchical coordination between groups

---

## Best Practices

### ✅ DO:

1. **Start simple**
   - Begin with centralized orchestration
   - Evolve to more complex patterns as needed
   - Add complexity only when justified

2. **Monitor coordination overhead**
   - Track message passing costs
   - Monitor agent idle time
   - Profile bottlenecks

3. **Design for failure**
   - No single point of failure (unless centralized)
   - Graceful degradation
   - Automatic recovery

4. **Document coordination protocol**
   - Clear message formats
   - Defined interaction patterns
   - Error handling procedures

### ❌ DON'T:

1. **Over-complicate**
   - Don't use swarm for 3 agents
   - Don't build 5-level hierarchy for small system
   - Keep it as simple as possible

2. **Ignore network reality**
   - Message passing has latency
   - Networks fail
   - Design async communication

3. **Skip testing**
   - Test coordination logic thoroughly
   - Simulate failures
   - Load test communication

---

## Resources

- [Coordination Patterns Research](https://www.researchgate.net/publication/228620566)
- [Swarm Intelligence](https://en.wikipedia.org/wiki/Swarm_intelligence)
- [Hierarchical Task Networks](https://en.wikipedia.org/wiki/Hierarchical_task_network)
- [Actor Model](https://en.wikipedia.org/wiki/Actor_model)

---

**Next**: [Context Sharing Patterns](context-sharing.md) | [Back to README](../README.md)
