"""
Command Executor tests - Shell command execution

TDD: 测试先行
"""

import sys
from tempfile import TemporaryDirectory
from pathlib import Path

import pytest

from deep_code.core.executor import (
    CommandExecutor,
    CommandResult,
    execute_command,
)


def test_executor_create() -> None:
    """验证创建 CommandExecutor"""
    executor = CommandExecutor()
    assert executor is not None


def test_execute_simple_command() -> None:
    """验证执行简单命令"""
    executor = CommandExecutor()

    # Use echo command which works on both platforms
    if sys.platform == "win32":
        result = executor.execute("echo hello")
    else:
        result = executor.execute("echo hello")

    assert result.return_code == 0
    assert "hello" in result.stdout
    assert result.stderr == ""


def test_execute_command_with_args() -> None:
    """验证执行带参数的命令"""
    executor = CommandExecutor()

    if sys.platform == "win32":
        result = executor.execute("echo", "hello", "world")
    else:
        result = executor.execute("echo", "hello", "world")

    assert result.return_code == 0
    assert "hello" in result.stdout or "world" in result.stdout


def test_execute_command_failure() -> None:
    """验证执行失败命令"""
    executor = CommandExecutor()

    # Command that should fail
    result = executor.execute("nonexistent_command_xyz123")

    assert result.return_code != 0


def test_execute_with_working_directory() -> None:
    """验证在指定工作目录执行"""
    with TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = Path(tmpdir, "test.txt")
        test_file.write_text("content")

        executor = CommandExecutor()

        # List files in tmpdir
        if sys.platform == "win32":
            result = executor.execute("dir", working_dir=tmpdir)
        else:
            result = executor.execute("ls", working_dir=tmpdir)

        assert result.return_code == 0
        assert "test.txt" in result.stdout


def test_execute_with_timeout() -> None:
    """验证带超时的命令执行"""
    executor = CommandExecutor()

    # Command that completes quickly
    result = executor.execute("echo test", timeout=5)

    assert result.return_code == 0
    assert result.timed_out is False


def test_execute_capture_stderr() -> None:
    """验证捕获 stderr"""
    executor = CommandExecutor()

    # Try to execute a non-existent command to get stderr
    result = executor.execute("nonexistent_cmd_xyz")

    # Should have non-zero return code
    assert result.return_code != 0


def test_command_result_str() -> None:
    """验证 CommandResult 字符串表示"""
    result = CommandResult(
        command="echo test",
        return_code=0,
        stdout="test\n",
        stderr="",
        timed_out=False,
    )

    s = str(result)
    assert "echo test" in s
    assert "0" in s


def test_command_result_success() -> None:
    """验证 CommandResult.success 属性"""
    result = CommandResult(
        command="echo test",
        return_code=0,
        stdout="test\n",
        stderr="",
        timed_out=False,
    )

    assert result.success is True

    result_fail = CommandResult(
        command="false",
        return_code=1,
        stdout="",
        stderr="",
        timed_out=False,
    )

    assert result_fail.success is False


def test_convenience_function() -> None:
    """验证便捷函数 execute_command"""
    result = execute_command("echo test")

    assert result.return_code == 0
    assert "test" in result.stdout


def test_execute_with_env_var() -> None:
    """验证带环境变量的命令执行"""
    executor = CommandExecutor()

    # Set an environment variable and read it back
    if sys.platform == "win32":
        result = executor.execute("echo %TEST_VAR%", env={"TEST_VAR": "hello"})
    else:
        result = executor.execute("sh -c 'echo $TEST_VAR'", env={"TEST_VAR": "hello"})

    assert result.return_code == 0
    # The environment variable should be in output
    assert "hello" in result.stdout


def test_execute_multiline_output() -> None:
    """验证多行输出处理"""
    executor = CommandExecutor()

    # Create multi-line output
    if sys.platform == "win32":
        result = executor.execute("echo line1 && echo line2 && echo line3")
    else:
        result = executor.execute("echo line1; echo line2; echo line3")

    assert result.return_code == 0
    assert "line1" in result.stdout
    assert "line2" in result.stdout
    assert "line3" in result.stdout


def test_execute_with_unicode_output() -> None:
    """验证 Unicode 输出处理"""
    executor = CommandExecutor()

    # Command with unicode output
    if sys.platform == "win32":
        result = executor.execute("echo hello世界")
    else:
        result = executor.execute("echo 'hello世界'")

    assert result.return_code == 0
    # Should handle unicode properly
    assert "hello" in result.stdout


def test_execute_python_command() -> None:
    """验证执行 Python 命令"""
    executor = CommandExecutor()

    # Execute a simple Python command
    result = executor.execute(sys.executable, "-c", "print('test')")

    assert result.return_code == 0
    assert "test" in result.stdout


def test_shell_detection() -> None:
    """验证 Shell 类型检测"""
    executor = CommandExecutor()

    if sys.platform == "win32":
        assert executor._get_shell_command()[0].endswith("powershell") or \
               executor._get_shell_command()[0].endswith("pwsh")
    else:
        assert "bash" in executor._get_shell_command()[0] or \
               "sh" in executor._get_shell_command()[0]


def test_combined_output() -> None:
    """验证合并输出（stdout + stderr）"""
    executor = CommandExecutor()

    result = executor.execute("echo test")

    combined = result.combined_output()
    assert "test" in combined


# ===== T071: Permission Integration Tests =====


def test_executor_with_permission_allow() -> None:
    """验证权限允许时执行命令"""
    from deep_code.security.permissions import (
        PermissionManager,
        PermissionRule,
        PermissionAction,
        PermissionDomain,
    )

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ALLOW,
        pattern="echo *",
    ))

    executor = CommandExecutor(permission_manager=manager)

    result = executor.execute("echo test")

    assert result.return_code == 0
    assert "test" in result.stdout


def test_executor_with_permission_deny() -> None:
    """验证权限拒绝时不执行命令"""
    from deep_code.security.permissions import (
        PermissionManager,
        PermissionRule,
        PermissionAction,
        PermissionDomain,
    )

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.DENY,
        pattern="echo *",
    ))

    executor = CommandExecutor(permission_manager=manager)

    result = executor.execute("echo test")

    # Should return error result
    assert result.return_code != 0
    assert "permission" in result.stderr.lower() or "denied" in result.stderr.lower()


def test_executor_with_permission_ask_granted() -> None:
    """验证 ASK 权限通过时执行命令"""
    from deep_code.security.permissions import (
        PermissionManager,
        PermissionRule,
        PermissionAction,
        PermissionDomain,
    )

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="echo *",
    ))

    # Callback that grants permission
    def grant_callback(domain, target, reason):
        return True

    executor = CommandExecutor(
        permission_manager=manager,
        approval_callback=grant_callback,
    )

    result = executor.execute("echo test")

    assert result.return_code == 0
    assert "test" in result.stdout


def test_executor_with_permission_ask_denied() -> None:
    """验证 ASK 权限拒绝时不执行命令"""
    from deep_code.security.permissions import (
        PermissionManager,
        PermissionRule,
        PermissionAction,
        PermissionDomain,
    )

    manager = PermissionManager()
    manager.add_rule(PermissionRule(
        domain=PermissionDomain.COMMAND,
        action=PermissionAction.ASK,
        pattern="echo *",
    ))

    # Callback that denies permission
    def deny_callback(domain, target, reason):
        return False

    executor = CommandExecutor(
        permission_manager=manager,
        approval_callback=deny_callback,
    )

    result = executor.execute("echo test")

    # Should return error result
    assert result.return_code != 0
    assert "permission" in result.stderr.lower() or "denied" in result.stderr.lower()


def test_executor_without_permission_manager() -> None:
    """验证没有权限管理器时正常执行"""
    executor = CommandExecutor()

    result = executor.execute("echo test")

    assert result.return_code == 0
    assert "test" in result.stdout
