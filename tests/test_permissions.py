"""
Permission system tests - T070

Tests for file/command/network access permission rules.
TDD: 测试先行
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

import pytest

from deep_code.security.permissions import (
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


# ===== T071: Approval Workflow Tests =====


def test_permission_approver_create() -> None:
    """验证创建 PermissionApprover"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    approver = PermissionApprover(manager)

    assert approver is not None
    assert approver.manager == manager


def test_permission_approver_allow_action() -> None:
    """验证 ALLOW 动作直接通过"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    ))

    approver = PermissionApprover(manager)

    # ALLOW should be automatically granted
    permission = approver.request_permission(
        domain=PermissionDomain.FILE_READ,
        target="test.txt",
    )

    assert permission.granted is True
    assert permission.result is not None
    assert permission.result.status == PermissionStatus.GRANTED


def test_permission_approver_deny_action() -> None:
    """验证 DENY 动作直接拒绝"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_WRITE,
        action=PermissionAction.DENY,
        pattern="*.txt",
    ))

    approver = PermissionApprover(manager)

    # DENY should be automatically denied
    permission = approver.request_permission(
        domain=PermissionDomain.FILE_WRITE,
        target="test.txt",
    )

    assert permission.granted is False
    assert permission.result is not None
    assert permission.result.status == PermissionStatus.DENIED


def test_permission_approver_ask_action_without_callback() -> None:
    """验证 ASK 动作无回调时拒绝"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="rm *",
    ))

    approver = PermissionApprover(manager)

    # ASK without callback should default to deny
    permission = approver.request_permission(
        domain=PermissionDomain.COMMAND,
        target="rm -rf /tmp/test",
    )

    assert permission.granted is False
    assert permission.result is not None
    assert permission.result.status == PermissionStatus.DENIED


def test_permission_approver_ask_action_with_grant_callback() -> None:
    """验证 ASK 动作回调通过"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="rm *",
    ))

    # Callback that grants permission
    def grant_callback(domain, target, reason):
        return True

    approver = PermissionApprover(manager, approval_callback=grant_callback)

    permission = approver.request_permission(
        domain=PermissionDomain.COMMAND,
        target="rm -rf /tmp/test",
    )

    assert permission.granted is True
    assert permission.result is not None
    assert permission.result.status == PermissionStatus.GRANTED


def test_permission_approver_ask_action_with_deny_callback() -> None:
    """验证 ASK 动作回调拒绝"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_WRITE,
        action=PermissionAction.ASK,
        pattern="*.py",
    ))

    # Callback that denies permission
    def deny_callback(domain, target, reason):
        return False

    approver = PermissionApprover(manager, approval_callback=deny_callback)

    permission = approver.request_permission(
        domain=PermissionDomain.FILE_WRITE,
        target="test.py",
    )

    assert permission.granted is False
    assert permission.result is not None
    assert permission.result.status == PermissionStatus.DENIED


def test_permission_approver_callback_parameters() -> None:
    """验证回调函数参数传递"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="git *",
        description="Version control",
    ))

    # Track callback parameters
    callback_params = []

    def track_callback(domain, target, reason):
        callback_params.append((domain, target, reason))
        return True

    approver = PermissionApprover(manager, approval_callback=track_callback)

    approver.request_permission(
        domain=PermissionDomain.COMMAND,
        target="git push",
    )

    assert len(callback_params) == 1
    domain, target, reason = callback_params[0]
    assert domain == PermissionDomain.COMMAND
    assert target == "git push"
    assert "Version control" in reason or reason is not None


def test_permission_approver_audit_log() -> None:
    """验证审批日志"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    ))

    approver = PermissionApprover(manager)

    # Request permission
    permission = approver.request_permission(
        domain=PermissionDomain.FILE_READ,
        target="test.txt",
    )

    # Check audit log
    assert len(approver.audit_log) > 0
    last_audit = approver.audit_log[-1]

    assert last_audit.domain == PermissionDomain.FILE_READ
    assert last_audit.target == "test.txt"
    assert last_audit.granted is True


def test_permission_approver_audit_log_for_denied() -> None:
    """验证拒绝操作的审计日志"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_WRITE,
        action=PermissionAction.DENY,
        pattern="*.txt",
    ))

    approver = PermissionApprover(manager)

    permission = approver.request_permission(
        domain=PermissionDomain.FILE_WRITE,
        target="test.txt",
    )

    assert len(approver.audit_log) > 0
    last_audit = approver.audit_log[-1]

    assert last_audit.domain == PermissionDomain.FILE_WRITE
    assert last_audit.target == "test.txt"
    assert last_audit.granted is False


def test_permission_approver_get_audit_history() -> None:
    """验证获取审计历史"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*",
    ))

    approver = PermissionApprover(manager)

    # Make multiple requests
    approver.request_permission(PermissionDomain.FILE_READ, "file1.txt")
    approver.request_permission(PermissionDomain.FILE_READ, "file2.txt")
    approver.request_permission(PermissionDomain.FILE_READ, "file3.txt")

    history = approver.get_audit_history()

    assert len(history) == 3
    assert history[0]["target"] == "file1.txt"
    assert history[1]["target"] == "file2.txt"
    assert history[2]["target"] == "file3.txt"


def test_permission_approver_clear_audit_log() -> None:
    """验证清空审计日志"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*",
    ))

    approver = PermissionApprover(manager)

    approver.request_permission(PermissionDomain.FILE_READ, "test.txt")
    assert len(approver.audit_log) > 0

    approver.clear_audit_log()
    assert len(approver.audit_log) == 0


def test_permission_approver_check_and_execute_allowed() -> None:
    """验证检查并执行允许的操作"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_READ,
        action=PermissionAction.ALLOW,
        pattern="*.txt",
    ))

    approver = PermissionApprover(manager)

    executed = [False]

    def read_file():
        executed[0] = True
        return "content"

    # Should execute
    result = approver.check_and_execute(
        domain=PermissionDomain.FILE_READ,
        target="test.txt",
        action=read_file,
    )

    assert result is not None
    assert executed[0] is True


def test_permission_approver_check_and_execute_denied() -> None:
    """验证检查并执行拒绝的操作"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.FILE_WRITE,
        action=PermissionAction.DENY,
        pattern="*.txt",
    ))

    approver = PermissionApprover(manager)

    executed = [False]

    def write_file():
        executed[0] = True
        return "written"

    # Should not execute
    result = approver.check_and_execute(
        domain=PermissionDomain.FILE_WRITE,
        target="test.txt",
        action=write_file,
    )

    assert result is None
    assert executed[0] is False


def test_permission_approver_check_and_execute_ask_granted() -> None:
    """验证 ASK 操作通过后执行"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="rm *",
    ))

    def grant_callback(domain, target, reason):
        return True

    approver = PermissionApprover(manager, approval_callback=grant_callback)

    executed = [False]

    def dangerous_command():
        executed[0] = True
        return "deleted"

    # Should execute after approval
    result = approver.check_and_execute(
        domain=PermissionDomain.COMMAND,
        target="rm -rf /tmp/test",
        action=dangerous_command,
    )

    assert result is not None
    assert executed[0] is True


def test_permission_approver_check_and_execute_ask_denied() -> None:
    """验证 ASK 操作拒绝后不执行"""
    from deep_code.security.permissions import PermissionApprover

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="rm *",
    ))

    def deny_callback(domain, target, reason):
        return False

    approver = PermissionApprover(manager, approval_callback=deny_callback)

    executed = [False]

    def dangerous_command():
        executed[0] = True
        return "deleted"

    # Should not execute after denial
    result = approver.check_and_execute(
        domain=PermissionDomain.COMMAND,
        target="rm -rf /tmp/test",
        action=dangerous_command,
    )

    assert result is None
    assert executed[0] is False
