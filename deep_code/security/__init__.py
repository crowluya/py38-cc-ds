"""
Security module for Claude Code

Contains permission system, sandbox controls, and checkpoint management.
"""

from deep_code.security.checkpoint import (
    Checkpoint,
    CheckpointError,
    CheckpointExistsError,
    CheckpointManager,
    CheckpointNotFoundError,
)
from deep_code.security.permissions import (
    Permission,
    PermissionAction,
    PermissionDomain,
    PermissionManager,
    PermissionResult,
    PermissionRule,
    PermissionStatus,
    create_default_manager,
)

__all__ = [
    # Checkpoint
    "Checkpoint",
    "CheckpointError",
    "CheckpointExistsError",
    "CheckpointManager",
    "CheckpointNotFoundError",
    # Permissions
    "Permission",
    "PermissionAction",
    "PermissionDomain",
    "PermissionManager",
    "PermissionResult",
    "PermissionRule",
    "PermissionStatus",
    "create_default_manager",
]
