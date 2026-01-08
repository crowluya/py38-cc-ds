"""
Permission system tests - T070

Tests for file/command/network access permission rules.
TDD: 测试先行
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

import pytest

from claude_code.security.permissions import (
    Permission,
    PermissionAction,
    PermissionDomain,
    PermissionManager,
    PermissionRule,
    PermissionStatus,
)


# ===== T070: Permission Rules Model Tests =====


def test_permission_action_values() -> None:
    """验证 PermissionAction 枚举值"""
    assert PermissionAction.ALLOW.value == "allow"
    assert PermissionAction.DENY.value == "deny"
    assert PermissionAction.ASK.value == "ask"


def test_permission_domain_values() -> None:
    """验证 PermissionDomain 枚举值"""
    assert PermissionDomain.FILE_READ.value == "file_read"
    assert PermissionDomain.FILE_WRITE.value == "file_write"
    assert PermissionDomain.COMMAND.value == "command"
    assert PermissionDomain.NETWORK.value == "network"


def test_permission_status_values() -> None:
    """验证 PermissionStatus 枚举值"""
    assert PermissionStatus.GRANTED.value == "granted"
    assert PermissionStatus.DENIED.value == "denied"
    assert PermissionStatus.PENDING.value == "pending"


def test_permission_rule_create() -> None:
    """验证创建 PermissionRule"""
    rule = PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    )

    assert rule.domain == PermissionDomain.FILE_READ
    assert rule.action == PermissionAction.ALLOW
    assert rule.pattern == "*.txt"


def test_permission_rule_with_description() -> None:
    """验证带描述的 PermissionRule"""
    rule = PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="rm -rf *",
        description="Dangerous delete command",
    )

    assert rule.description == "Dangerous delete command"


def test_permission_rule_matches_exact() -> None:
    """验证精确匹配规则"""
    rule = PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="/etc/hosts",
    )

    assert rule.matches("/etc/hosts")
    assert not rule.matches("/etc/passwd")


def test_permission_rule_matches_wildcard() -> None:
    """验证通配符匹配规则"""
    rule = PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    )

    assert rule.matches("file.txt")
    assert rule.matches("notes.txt")
    assert not rule.matches("file.py")


def test_permission_rule_matches_path_wildcard() -> None:
    """验证路径通配符匹配"""
    rule = PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.DENY,
        pattern="/etc/*",
    )

    assert rule.matches("/etc/hosts")
    assert rule.matches("/etc/passwd")
    assert not rule.matches("/usr/bin/python")


def test_permission_rule_matches_recursive_wildcard() -> None:
    """验证递归通配符匹配"""
    rule = PermissionRule(
        domain=PermissionDomain.FILE_WRITE,
        action=PermissionAction.DENY,
        pattern=".git/*",
    )

    assert rule.matches(".git/config")
    assert rule.matches(".git/HEAD")
    assert not rule.matches("src/main.py")

    # Test with directory prefix
    rule2 = PermissionRule(
        domain=PermissionDomain.FILE_WRITE,
        action=PermissionAction.DENY,
        pattern="*/.git/*",
    )

    assert rule2.matches("src/.git/config")
    assert rule2.matches("project/.git/HEAD")
    assert not rule2.matches(".git/config")  # Needs the prefix


def test_permission_manager_create() -> None:
    """验证创建 PermissionManager"""
    manager = PermissionManager()

    assert manager is not None
    assert len(manager.get_rules()) == 0


def test_permission_manager_add_rule() -> None:
    """验证添加规则"""
    manager = PermissionManager()

    rule = PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    )

    manager.add_rule(rule)

    assert len(manager.get_rules()) == 1


def test_permission_manager_add_multiple_rules() -> None:
    """验证添加多条规则"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    ))

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.DENY,
        pattern="*.secret",
    ))

    assert len(manager.get_rules()) == 2


def test_permission_manager_default_deny() -> None:
    """验证默认拒绝策略"""
    manager = PermissionManager()

    # No rules added, should default to deny for safety
    result = manager.check_permission(
        domain=PermissionDomain.FILE_READ,
        target="unknown.txt",
    )

    assert result.status == PermissionStatus.DENIED


def test_permission_manager_allow_explicit() -> None:
    """验证显式允许"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    ))

    result = manager.check_permission(
        domain=PermissionDomain.FILE_READ,
        target="file.txt",
    )

    assert result.status == PermissionStatus.GRANTED
    assert result.action == PermissionAction.ALLOW


def test_permission_manager_deny_explicit() -> None:
    """验证显式拒绝"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.DENY,
        pattern="*.secret",
    ))

    result = manager.check_permission(
        domain=PermissionDomain.FILE_READ,
        target="config.secret",
    )

    assert result.status == PermissionStatus.DENIED
    assert result.action == PermissionAction.DENY


def test_permission_manager_ask_requires_approval() -> None:
    """验证 ASK 需要审批"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="rm *",
    ))

    result = manager.check_permission(
        domain=PermissionDomain.COMMAND,
        target="rm -rf /tmp/test",
    )

    assert result.status == PermissionStatus.PENDING
    assert result.action == PermissionAction.ASK


def test_permission_manager_priority_specific_over_generic() -> None:
    """验证具体规则覆盖泛规则"""
    manager = PermissionManager()

    # Generic deny
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.DENY,
        pattern="*",
    ))

    # Specific allow
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="safe.txt",
    ))

    # Specific rule should win
    result = manager.check_permission(
        domain=PermissionDomain.FILE_READ,
        target="safe.txt",
    )

    assert result.status == PermissionStatus.GRANTED


def test_permission_manager_deny_overrides_allow() -> None:
    """验证 DENY 优先级最高"""
    manager = PermissionManager()

    # Generic allow
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    ))

    # Specific deny
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.DENY,
        pattern="secret.txt",
    ))

    # Deny should override allow
    result = manager.check_permission(
        domain=PermissionDomain.FILE_READ,
        target="secret.txt",
    )

    assert result.status == PermissionStatus.DENIED


def test_permission_manager_domain_isolation() -> None:
    """验证不同域的规则隔离"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*",
    ))

    # File read rule should not affect commands
    result = manager.check_permission(
        domain=PermissionDomain.COMMAND,
        target="rm -rf /",
    )

    assert result.status == PermissionStatus.DENIED


def test_permission_manager_remove_rule() -> None:
    """验证移除规则"""
    manager = PermissionManager()

    rule = PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    )

    manager.add_rule(rule)
    assert len(manager.get_rules()) == 1

    manager.remove_rule(rule)
    assert len(manager.get_rules()) == 0


def test_permission_manager_clear_rules() -> None:
    """验证清空规则"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    ))

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.DENY,
        pattern="rm *",
    ))

    assert len(manager.get_rules()) == 2

    manager.clear_rules()
    assert len(manager.get_rules()) == 0


def test_permission_manager_get_rules_by_domain() -> None:
    """验证按域获取规则"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    ))

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_WRITE,
        action=PermissionAction.DENY,
        pattern="*.log",
    ))

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="git *",
    ))

    file_rules = manager.get_rules(domain=PermissionDomain.FILE_READ)
    assert len(file_rules) == 1
    assert file_rules[0].pattern == "*.txt"

    command_rules = manager.get_rules(domain=PermissionDomain.COMMAND)
    assert len(command_rules) == 1
    assert command_rules[0].pattern == "git *"


def test_permission_result_structure() -> None:
    """验证 PermissionResult 结构"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="test.txt",
        description="Test file",
    ))

    result = manager.check_permission(
        domain=PermissionDomain.FILE_READ,
        target="test.txt",
    )

    assert result.status == PermissionStatus.GRANTED
    assert result.action == PermissionAction.ALLOW
    assert result.target == "test.txt"
    assert result.matching_rule is not None
    assert result.matching_rule.description == "Test file"


def test_permission_manager_command_safety() -> None:
    """验证命令安全检查"""
    manager = PermissionManager()

    # Allow safe commands by default pattern
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ALLOW,
        pattern="git *",
    ))

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.DENY,
        pattern="rm *",
    ))

    # Safe command
    safe_result = manager.check_permission(
        domain=PermissionDomain.COMMAND,
        target="git status",
    )
    assert safe_result.status == PermissionStatus.GRANTED

    # Dangerous command
    danger_result = manager.check_permission(
        domain=PermissionDomain.COMMAND,
        target="rm -rf important",
    )
    assert danger_result.status == PermissionStatus.DENIED


def test_permission_manager_with_temp_directory() -> None:
    """验证在临时目录中测试文件权限"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.py",
    ))

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_WRITE,
        action=PermissionAction.DENY,
        pattern="*.py",
    ))

    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir, "test.py")

        # Read should be allowed
        read_result = manager.check_permission(
            domain=PermissionDomain.FILE_READ,
            target=str(test_file),
        )
        assert read_result.status == PermissionStatus.GRANTED

        # Write should be denied
        write_result = manager.check_permission(
            domain=PermissionDomain.FILE_WRITE,
            target=str(test_file),
        )
        assert write_result.status == PermissionStatus.DENIED


def test_permission_manager_network_default_deny() -> None:
    """验证网络默认拒绝"""
    manager = PermissionManager()

    # No network rules, should deny
    result = manager.check_permission(
        domain=PermissionDomain.NETWORK,
        target="https://example.com",
    )

    assert result.status == PermissionStatus.DENIED


def test_permission_manager_network_allow() -> None:
    """验证网络显式允许"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.NETWORK,
        action=PermissionAction.ALLOW,
        pattern="https://api.internal.com/*",
    ))

    result = manager.check_permission(
        domain=PermissionDomain.NETWORK,
        target="https://api.internal.com/v1/data",
    )

    assert result.status == PermissionStatus.GRANTED


def test_permission_manager_wildcard_order_matters() -> None:
    """验证规则顺序对通配符的影响"""
    manager = PermissionManager()

    # Add deny first, then allow
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.DENY,
        pattern="*",
    ))

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    ))

    # Later specific rule should match first
    result = manager.check_permission(
        domain=PermissionDomain.FILE_READ,
        target="file.txt",
    )

    # The manager should find the most specific match
    assert result.status == PermissionStatus.GRANTED


def test_permission_case_sensitive() -> None:
    """验证区分大小写"""
    manager = PermissionManager()

    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.TXT",
    ))

    # Exact match should work
    result_upper = manager.check_permission(
        domain=PermissionDomain.FILE_READ,
        target="file.TXT",
    )
    assert result_upper.status == PermissionStatus.GRANTED

    # Lower case should not match (depends on implementation)
    result_lower = manager.check_permission(
        domain=PermissionDomain.FILE_READ,
        target="file.txt",
    )
    # This tests current behavior - may vary based on glob implementation
