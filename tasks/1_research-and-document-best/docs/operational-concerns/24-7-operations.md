# 24/7 Autonomous Operations

**Patterns and practices for continuous, reliable multi-agent system operation**

---

## Overview

Running multi-agent systems 24/7 requires special attention to fault tolerance, self-healing, monitoring, and recovery. This document covers operational patterns for autonomous, long-running systems.

## Key Requirements

- **Fault Tolerance**: System continues despite failures
- **Self-Healing**: Automatic recovery from failures
- **Monitoring**: Real-time health visibility
- **Graceful Degradation**: Reduced capability vs total failure
- **Recovery**: Return to normal operation after issues

---

## 1. Circuit Breaker Pattern

### Description
Prevent cascading failures by failing fast when external service is down.

### Implementation

```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(self,
                 failure_threshold: int = 5,
                 timeout: int = 60,
                 half_open_attempts: int = 1):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds to wait before trying again
        self.half_open_attempts = half_open_attempts

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = None
        self.half_open_success_count = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery"""
        if self.last_failure_time is None:
            return True
        return datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout)

    def _on_success(self):
        """Handle successful call"""
        self.failures = 0

        if self.state == CircuitState.HALF_OPEN:
            self.half_open_success_count += 1
            if self.half_open_success_count >= self.half_open_attempts:
                self.state = CircuitState.CLOSED
                print("Circuit breaker CLOSED - service recovered")

    def _on_failure(self):
        """Handle failed call"""
        self.failures += 1
        self.last_failure_time = datetime.now()

        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            print(f"Circuit breaker OPEN - {self.failures} failures")

    def get_state(self) -> dict:
        """Get current state"""
        return {
            "state": self.state.value,
            "failures": self.failures,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }

# Usage
async def unreliable_service():
    # Simulate service that fails sometimes
    import random
    if random.random() < 0.3:
        raise Exception("Service unavailable")
    await asyncio.sleep(0.1)
    return {"result": "success"}

circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=10)

for i in range(20):
    try:
        result = await circuit_breaker.call(unreliable_service)
        print(f"Call {i}: Success")
    except Exception as e:
        print(f"Call {i}: Failed - {e}")

    await asyncio.sleep(0.5)
```

### Benefits
- ✅ Prevents cascading failures
- ✅ Fast fail when service is down
- ✅ Automatic recovery testing
- ✅ Protects downstream systems

---

## 2. Health Monitoring and Self-Healing

### Description
Continuous health monitoring with automatic recovery actions.

### Implementation

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Callable
import asyncio

@dataclass
class HealthStatus:
    component_id: str
    is_healthy: bool
    last_check: datetime
    consecutive_failures: int
    last_error: str = None

class HealthMonitor:
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.components: Dict[str, HealthStatus] = {}
        self.health_checks: Dict[str, Callable] = {}
        self.recovery_actions: Dict[str, Callable] = {}
        self.running = False

    def register_component(self,
                          component_id: str,
                          health_check: Callable,
                          recovery_action: Callable = None):
        """Register a component to monitor"""
        self.health_checks[component_id] = health_check
        self.recovery_actions[component_id] = recovery_action
        self.components[component_id] = HealthStatus(
            component_id=component_id,
            is_healthy=True,
            last_check=datetime.now(),
            consecutive_failures=0
        )

    async def start(self):
        """Start continuous health monitoring"""
        self.running = True
        while self.running:
            await self._check_all_components()
            await asyncio.sleep(self.check_interval)

    def stop(self):
        self.running = False

    async def _check_all_components(self):
        """Run health checks for all components"""
        for component_id in self.components.keys():
            await self._check_component(component_id)

    async def _check_component(self, component_id: str):
        """Check individual component"""
        health_check = self.health_checks.get(component_id)
        if not health_check:
            return

        status = self.components[component_id]

        try:
            # Run health check
            is_healthy = await health_check() if asyncio.iscoroutinefunction(health_check) else health_check()

            if is_healthy:
                status.is_healthy = True
                status.consecutive_failures = 0
                status.last_check = datetime.now()
            else:
                await self._handle_unhealthy(component_id, "Health check returned False")

        except Exception as e:
            await self._handle_unhealthy(component_id, str(e))

    async def _handle_unhealthy(self, component_id: str, error: str):
        """Handle unhealthy component"""
        status = self.components[component_id]
        status.is_healthy = False
        status.consecutive_failures += 1
        status.last_error = error
        status.last_check = datetime.now()

        print(f"Component {component_id} unhealthy: {error}")

        # Attempt recovery if configured
        if status.consecutive_failures >= 3:
            recovery_action = self.recovery_actions.get(component_id)
            if recovery_action:
                print(f"Attempting recovery for {component_id}")
                try:
                    await recovery_action() if asyncio.iscoroutinefunction(recovery_action) else recovery_action()
                    status.consecutive_failures = 0  # Reset after recovery attempt
                except Exception as e:
                    print(f"Recovery failed for {component_id}: {e}")

    def get_health_report(self) -> Dict[str, dict]:
        """Get health status of all components"""
        return {
            comp_id: {
                "healthy": status.is_healthy,
                "last_check": status.last_check.isoformat(),
                "failures": status.consecutive_failures,
                "error": status.last_error
            }
            for comp_id, status in self.components.items()
        }

# Usage
async def check_agent_health(agent_id: str) -> bool:
    """Health check for an agent"""
    # In reality, would ping agent, check if responsive
    import random
    return random.random() > 0.2  # 80% healthy

async def restart_agent(agent_id: str):
    """Recovery action: restart agent"""
    print(f"Restarting agent {agent_id}")
    # In reality, would restart the agent
    await asyncio.sleep(1)

monitor = HealthMonitor(check_interval=10)

monitor.register_component(
    "agent_1",
    lambda: check_agent_health("agent_1"),
    lambda: restart_agent("agent_1")
)

monitor.register_component(
    "agent_2",
    lambda: check_agent_health("agent_2"),
    lambda: restart_agent("agent_2")
)

# Start monitoring
await monitor.start()
```

### Benefits
- ✅ Proactive issue detection
- ✅ Automatic recovery
- ✅ Reduced downtime
- ✅ Visibility into system health

---

## 3. Graceful Degradation

### Description
System continues with reduced functionality instead of complete failure.

### Implementation

```python
from enum import Enum
from typing import Dict, Any, List

class DegradationLevel(Enum):
    FULL = "full"           # All functionality
    REDUCED = "reduced"     # Limited functionality
    MINIMAL = "minimal"     # Critical only
    EMERGENCY = "emergency" # Survival mode

class DegradationManager:
    def __init__(self):
        self.current_level = DegradationLevel.FULL
        self.capabilities: Dict[str, List[str]] = {
            DegradationLevel.FULL: ["research", "analysis", "writing", "editing"],
            DegradationLevel.REDUCED: ["research", "writing"],
            DegradationLevel.MINIMAL: ["research"],
            DegradationLevel.EMERGENCY: []
        }

    def set_degradation_level(self, level: DegradationLevel):
        """Set current degradation level"""
        old_level = self.current_level
        self.current_level = level
        print(f"Degradation level: {old_level.value} -> {level.value}")

    def can_perform(self, capability: str) -> bool:
        """Check if capability is available at current level"""
        available = self.capabilities[self.current_level]
        return capability in available

    def get_available_capabilities(self) -> List[str]:
        """Get list of available capabilities"""
        return self.capabilities[self.current_level].copy()

    def auto_degrade(self, health_metrics: Dict[str, float]):
        """Automatically adjust degradation based on health"""
        # Example: if < 50% agents healthy, degrade to REDUCED
        agent_health = health_metrics.get("agent_health_percentage", 100)

        if agent_health < 20:
            self.set_degradation_level(DegradationLevel.EMERGENCY)
        elif agent_health < 40:
            self.set_degradation_level(DegradationLevel.MINIMAL)
        elif agent_health < 70:
            self.set_degradation_level(DegradationLevel.REDUCED)
        else:
            self.set_degradation_level(DegradationLevel.FULL)

class DegradedAgent:
    """Agent that respects degradation levels"""
    def __init__(self, agent_id: str, capabilities: List[str],
                 degradation_manager: DegradationManager):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.degradation_manager = degradation_manager

    def can_perform_task(self, task_type: str) -> bool:
        """Check if task can be performed given current degradation"""
        return self.degradation_manager.can_perform(task_type)

    async def execute_task(self, task_type: str, task_data: dict) -> dict:
        """Execute task if possible"""
        if not self.can_perform_task(task_type):
            return {
                "error": f"Capability {task_type} not available at degradation level {self.degradation_manager.current_level.value}"
            }

        # Execute task normally
        return await self._do_work(task_type, task_data)

    async def _do_work(self, task_type: str, task_data: dict) -> dict:
        """Actual work implementation"""
        await asyncio.sleep(0.1)
        return {"result": f"{task_type} completed"}

# Usage
degradation_mgr = DegradationManager()

agent = DegradedAgent(
    "agent_1",
    ["research", "analysis", "writing"],
    degradation_mgr
)

# Normal operation
print(agent.can_perform_task("analysis"))  # True

# System degrades due to failures
degradation_mgr.set_degradation_level(DegradationLevel.REDUCED)

# Check capabilities
print(agent.can_perform_task("analysis"))  # False
print(agent.can_perform_task("research"))  # True
```

### Benefits
- ✅ System stays operational
- ✅ Better than total failure
- ✅ Automatic adaptation
- ✅ Prioritizes critical functions

---

## 4. Checkpoint and Recovery

### Description
Save system state periodically, recover from last checkpoint on failure.

### Implementation

```python
import pickle
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
import hashlib

class CheckpointManager:
    def __init__(self, checkpoint_dir: str = "./checkpoints",
                 max_checkpoints: int = 10):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.max_checkpoints = max_checkpoints

    def save_checkpoint(self, state: dict, checkpoint_id: str = None) -> str:
        """Save system state as checkpoint"""
        if checkpoint_id is None:
            checkpoint_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "state": state,
            "checksum": self._compute_checksum(state)
        }

        filepath = self.checkpoint_dir / f"checkpoint_{checkpoint_id}.pkl"

        with open(filepath, 'wb') as f:
            pickle.dump(checkpoint_data, f)

        # Cleanup old checkpoints
        self._cleanup_old_checkpoints()

        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> dict:
        """Load checkpoint by ID"""
        filepath = self.checkpoint_dir / f"checkpoint_{checkpoint_id}.pkl"

        if not filepath.exists():
            raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")

        with open(filepath, 'rb') as f:
            checkpoint_data = pickle.load(f)

        # Verify checksum
        if checkpoint_data["checksum"] != self._compute_checksum(checkpoint_data["state"]):
            raise ValueError("Checkpoint corrupted - checksum mismatch")

        return checkpoint_data["state"]

    def load_latest_checkpoint(self) -> dict:
        """Load most recent checkpoint"""
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            raise FileNotFoundError("No checkpoints available")

        latest = max(checkpoints)
        return self.load_checkpoint(latest)

    def list_checkpoints(self) -> List[str]:
        """List all available checkpoint IDs"""
        checkpoints = []
        for filepath in self.checkpoint_dir.glob("checkpoint_*.pkl"):
            checkpoint_id = filepath.stem.replace("checkpoint_", "")
            checkpoints.append(checkpoint_id)
        return checkpoints

    def _cleanup_old_checkpoints(self):
        """Remove oldest checkpoints if超过 max"""
        checkpoints = self.list_checkpoints()
        if len(checkpoints) > self.max_checkpoints:
            # Sort by name (which includes timestamp)
            checkpoints.sort()
            # Remove oldest
            for old_id in checkpoints[:-self.max_checkpoints]:
                filepath = self.checkpoint_dir / f"checkpoint_{old_id}.pkl"
                filepath.unlink()

    def _compute_checksum(self, state: dict) -> str:
        """Compute checksum of state"""
        state_str = str(sorted(state.items()))
        return hashlib.md5(state_str.encode()).hexdigest()

class RecoverableAgent:
    """Agent that can be checkpointed and recovered"""
    def __init__(self, agent_id: str, checkpoint_manager: CheckpointManager):
        self.agent_id = agent_id
        self.checkpoint_manager = checkpoint_manager
        self.state = {
            "agent_id": agent_id,
            "tasks_completed": [],
            "current_task": None,
            "context": {}
        }

    async def do_work(self, task: dict):
        """Do work, periodically checkpointing"""
        self.state["current_task"] = task

        # Checkpoint before starting
        self.checkpoint_manager.save_checkpoint(
            self.state,
            f"{self.agent_id}_pre_task"
        )

        # Do the work
        await asyncio.sleep(0.5)  # Simulate work

        # Update state
        self.state["tasks_completed"].append(task)
        self.state["current_task"] = None

        # Checkpoint after completing
        self.checkpoint_manager.save_checkpoint(
            self.state,
            f"{self.agent_id}_post_task"
        )

    def recover(self):
        """Recover from latest checkpoint"""
        try:
            self.state = self.checkpoint_manager.load_latest_checkpoint()
            print(f"Agent {self.agent_id} recovered from checkpoint")
        except FileNotFoundError:
            print(f"No checkpoint found for {self.agent_id}, starting fresh")

# Usage
checkpoint_mgr = CheckpointManager()

agent = RecoverableAgent("agent_1", checkpoint_mgr)

# Do work
await agent.do_work({"task": "research"})

# Later, if agent crashes...
agent.recover()  # Restore from checkpoint
```

### Benefits
- ✅ Recovery from failures
- ✅ Resume work, don't restart
- ✅ Prevents data loss
- ✅ Audit trail

---

## Best Practices

### ✅ DO:

1. **Implement comprehensive monitoring**
   - Health checks for all components
   - Metrics collection
   - Alert on anomalies

2. **Design for failure**
   - Assume components will fail
   - Have fallback strategies
   - Test failure scenarios

3. **Graceful degradation**
   - Better than total failure
   - Prioritize critical functions
   - Auto-scale capabilities

4. **Regular checkpoints**
   - Save state frequently
   - Test recovery procedures
   - Manage checkpoint storage

5. **Automatic recovery**
   - Detect and recover without human intervention
   - Self-healing systems
   - Minimal manual intervention

### ❌ DON'T:

1. **Ignore health monitoring**
   - Can't detect problems
   - Late response to failures
   - Poor uptime

2. **Hardcode everything**
   - Can't adapt to failures
   - Brittle systems
   - Difficult recovery

3. **Skip checkpointing**
   - Lose work on failure
   - Must restart from beginning
   - Data loss

4. **Assume perfect reliability**
   - Networks fail
   - Processes crash
   - Design for chaos

---

**Next**: [Budget Management](budget-management.md) | [Back to README](../README.md)
