"""
Permission system - T070

Python 3.8.10 compatible
Windows 7 + Internal Network (DeepSeek R1 70B)

Handles:
- File access permissions (read/write)
- Command execution permissions
- Network access permissions
- Allow/deny/ask actions
- Rule priority and matching
"""

from dataclasses import dataclass, field
from enum import Enum
from fnmatch import fnmatch
from typing import List, Optional


class PermissionAction(Enum):
    """Permission action types."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionDomain(Enum):
    """Permission domains."""

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    COMMAND = "command"
    NETWORK = "network"


class PermissionStatus(Enum):
    """Permission check result status."""

    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"  # Waiting for user approval (ASK action)


@dataclass
class PermissionRule:
    """
    A single permission rule.

    Rules are matched using glob patterns against targets.
    """

    domain: PermissionDomain
    action: PermissionAction
    pattern: str
    description: Optional[str] = None
    priority: int = 0  # Higher priority rules are checked first

    def matches(self, target: str) -> bool:
        """
        Check if this rule matches the target.

        Args:
            target: Target path/command to check

        Returns:
            True if the pattern matches the target
        """
        # Handle recursive wildcard ** by converting to *
        pattern = self.pattern.replace("**", "*")

        return fnmatch(target, pattern)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.action.value} {self.domain.value} {self.pattern}"


@dataclass
class PermissionResult:
    """
    Result of a permission check.

    Contains the status, action that was taken, and the rule that matched.
    """

    status: PermissionStatus
    action: PermissionAction
    target: str
    domain: PermissionDomain
    matching_rule: Optional[PermissionRule] = None
    reason: Optional[str] = None

    def is_allowed(self) -> bool:
        """Check if permission was granted."""
        return self.status == PermissionStatus.GRANTED

    def is_denied(self) -> bool:
        """Check if permission was denied."""
        return self.status == PermissionStatus.DENIED

    def is_pending(self) -> bool:
        """Check if permission is pending user approval."""
        return self.status == PermissionStatus.PENDING


@dataclass
class Permission:
    """
    Permission request and response wrapper.

    Used for tracking permission checks through the approval workflow.
    """

    domain: PermissionDomain
    target: str
    result: Optional[PermissionResult] = None
    granted: bool = False

    def grant(self) -> None:
        """Mark this permission as granted."""
        self.granted = True
        if self.result:
            self.result.status = PermissionStatus.GRANTED

    def deny(self) -> None:
        """Mark this permission as denied."""
        self.granted = False
        if self.result:
            self.result.status = PermissionStatus.DENIED


class PermissionManager:
    """
    Manages permission rules and checks.

    Features:
    - Default-deny for safety
    - Rule priority (specific > generic)
    - DENY overrides ALLOW
    - Domain isolation
    """

    def __init__(self) -> None:
        """Initialize PermissionManager."""
        self._rules: List[PermissionRule] = []

    def add_rule(self, rule: PermissionRule) -> None:
        """
        Add a permission rule.

        Args:
            rule: Rule to add
        """
        self._rules.append(rule)

    def remove_rule(self, rule: PermissionRule) -> None:
        """
        Remove a permission rule.

        Args:
            rule: Rule to remove
        """
        if rule in self._rules:
            self._rules.remove(rule)

    def clear_rules(self) -> None:
        """Clear all rules."""
        self._rules = []

    def get_rules(self, domain: Optional[PermissionDomain] = None) -> List[PermissionRule]:
        """
        Get all rules, optionally filtered by domain.

        Args:
            domain: Optional domain filter

        Returns:
            List of rules
        """
        if domain is None:
            return list(self._rules)
        return [r for r in self._rules if r.domain == domain]

    def check_permission(
        self,
        domain: PermissionDomain,
        target: str,
    ) -> PermissionResult:
        """
        Check if an action is permitted.

        Rules are evaluated in order:
        1. Find all rules matching the domain and target
        2. DENY rules always take precedence over ALLOW
        3. More specific patterns (fewer wildcards) take precedence

        Args:
            domain: Permission domain
            target: Target path/command to check

        Returns:
            PermissionResult with status and matching rule
        """
        # Get all matching rules for this domain and target
        domain_rules = [r for r in self._rules if r.domain == domain]
        matching_rules = [r for r in domain_rules if r.matches(target)]

        if not matching_rules:
            # Default deny for safety
            return PermissionResult(
                status=PermissionStatus.DENIED,
                action=PermissionAction.DENY,
                target=target,
                domain=domain,
                reason="No matching rule (default deny)",
            )

        # Find the best matching rule
        # Priority: DENY > ASK > ALLOW, then specificity
        best_rule = self._find_best_rule(matching_rules)

        # Map action to status
        if best_rule.action == PermissionAction.DENY:
            status = PermissionStatus.DENIED
        elif best_rule.action == PermissionAction.ASK:
            status = PermissionStatus.PENDING
        else:  # ALLOW
            status = PermissionStatus.GRANTED

        return PermissionResult(
            status=status,
            action=best_rule.action,
            target=target,
            domain=domain,
            matching_rule=best_rule,
        )

    def _find_best_rule(self, rules: List[PermissionRule]) -> PermissionRule:
        """
        Find the best rule from a list of matching rules.

        Priority:
        1. More specific patterns (fewer wildcards, longer strings)
        2. If specificity is equal, DENY > ASK > ALLOW (safety first)

        Args:
            rules: List of matching rules

        Returns:
            The best rule
        """
        # First, group by action priority within specificity level
        # Sort by specificity first (most specific = fewest wildcards, longest)
        # Then within same specificity, DENY > ASK > ALLOW
        def specificity_score(rule: PermissionRule) -> tuple:
            # Fewer wildcards = more specific
            # Longer pattern = more specific
            # Higher priority value = more specific (from rule.priority)
            wildcard_count = rule.pattern.count("*") + rule.pattern.count("?")
            return (
                wildcard_count,  # Lower is better
                -len(rule.pattern),  # Higher (less negative) is better
                -rule.priority,  # Higher is better
            )

        # Sort by specificity
        rules_by_specificity = sorted(rules, key=specificity_score)

        # Get the most specific group
        most_specific_score = specificity_score(rules_by_specificity[0])
        most_specific_rules = [
            r for r in rules_by_specificity
            if specificity_score(r) == most_specific_score
        ]

        # Among equally specific rules, DENY wins
        deny_rules = [r for r in most_specific_rules if r.action == PermissionAction.DENY]
        if deny_rules:
            return deny_rules[0]

        # Then ASK
        ask_rules = [r for r in most_specific_rules if r.action == PermissionAction.ASK]
        if ask_rules:
            return ask_rules[0]

        # Finally ALLOW
        allow_rules = [r for r in most_specific_rules if r.action == PermissionAction.ALLOW]
        if allow_rules:
            return allow_rules[0]

        # Fallback
        return rules_by_specificity[0]

    def _find_most_specific(self, rules: List[PermissionRule]) -> PermissionRule:
        """
        Find the most specific rule (fewest wildcards).

        Args:
            rules: List of rules

        Returns:
            The most specific rule
        """
        def count_wildcards(pattern: str) -> int:
            return pattern.count("*") + pattern.count("?")

        # Sort by wildcard count (ascending), then by length (descending)
        # Longer patterns with fewer wildcards are more specific
        sorted_rules = sorted(
            rules,
            key=lambda r: (count_wildcards(r.pattern), -len(r.pattern))
        )

        return sorted_rules[0]

    def request_permission(
        self,
        domain: PermissionDomain,
        target: str,
    ) -> Permission:
        """
        Create a permission request.

        For ASK actions, this creates a pending permission that can be
        granted or denied by the user.

        Args:
            domain: Permission domain
            target: Target path/command

        Returns:
            Permission object with result
        """
        result = self.check_permission(domain, target)

        return Permission(
            domain=domain,
            target=target,
            result=result,
            granted=(result.status == PermissionStatus.GRANTED),
        )


# Convenience functions for common permission scenarios


def create_default_manager() -> PermissionManager:
    """
    Create a PermissionManager with sensible default rules.

    Defaults:
    - All file reads: ASK
    - All file writes: DENY
    - Safe commands (git, ls, echo, cat): ALLOW
    - Dangerous commands (rm, del, format): ASK
    - Network: DENY

    Returns:
        Configured PermissionManager
    """
    manager = PermissionManager()

    # File rules - conservative by default
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ASK,
        pattern="*",
        description="Default file read policy",
    ))

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_WRITE,
        action=PermissionAction.DENY,
        pattern="*",
        description="Default file write policy (dangerous)",
    ))

    # Safe commands
    safe_commands = [
        "git *",
        "git",
        "ls *",
        "ls",
        "echo *",
        "cat *",
        "pwd",
        "cd *",
        "dir",
        "type *",
    ]

    for cmd_pattern in safe_commands:
        manager.add_rule(PermissionRule(
            domain=PermissionDomain.COMMAND,
            action=PermissionAction.ALLOW,
            pattern=cmd_pattern,
            description=f"Safe command: {cmd_pattern}",
        ))

    # Dangerous commands
    dangerous_patterns = [
        "rm *",
        "rmdir *",
        "del *",
        "format *",
        "shutdown *",
        "reboot *",
    ]

    for pattern in dangerous_patterns:
        manager.add_rule(PermissionRule(
            domain=PermissionDomain.COMMAND,
            action=PermissionAction.ASK,
            pattern=pattern,
            description=f"Dangerous command: {pattern}",
        ))

    # Network - deny by default
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.NETWORK,
        action=PermissionAction.DENY,
        pattern="*",
        description="Default network deny",
    ))

    return manager
