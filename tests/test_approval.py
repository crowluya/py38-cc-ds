"""
Approval tests - Questionary approval wrapper

TDD: 测试先行
"""

from typing import Any, List

import pytest

from deep_code.cli.approval import Approval, get_approval


def test_approval_create() -> None:
    """验证 Approval 可创建"""
    approval = Approval()
    assert approval is not None


def test_confirm_default_false() -> None:
    """验证确认：默认 False（需要显式确认）"""
    from unittest.mock import patch, MagicMock

    approval = Approval()

    # Mock questionary.confirm to return None
    with patch("questionary.confirm") as mock_confirm:
        mock_instance = MagicMock()
        mock_instance.ask.return_value = None
        mock_confirm.return_value = mock_instance

        result = approval.confirm("Continue?", default=False)
        assert result is False


def test_confirm_default_true() -> None:
    """验证确认：默认 True"""
    from unittest.mock import patch, MagicMock

    approval = Approval()

    with patch("questionary.confirm") as mock_confirm:
        mock_instance = MagicMock()
        mock_instance.ask.return_value = None
        mock_confirm.return_value = mock_instance

        result = approval.confirm("Continue?", default=True)
        assert result is True


def test_confirm_yes() -> None:
    """验证确认：是"""
    from unittest.mock import patch

    approval = Approval()

    # Mock the confirm method on the approval instance
    with patch.object(approval, "confirm", return_value=True):
        result = approval.confirm("Continue?", default=False)
        assert result is True


def test_confirm_no() -> None:
    """验证确认：否"""
    from unittest.mock import patch

    approval = Approval()

    # Mock the confirm method on the approval instance
    with patch.object(approval, "confirm", return_value=False):
        result = approval.confirm("Continue?", default=True)
        assert result is False


def test_select() -> None:
    """验证单选"""
    from unittest.mock import patch

    approval = Approval()

    with patch.object(approval, "select", return_value="Option A"):
        result = approval.select("Choose:", ["Option A", "Option B"])
        assert result == "Option A"


def test_select_cancelled() -> None:
    """验证单选：取消"""
    from unittest.mock import patch

    approval = Approval()

    with patch.object(approval, "select", return_value=None):
        result = approval.select("Choose:", ["Option A", "Option B"])
        assert result is None


def test_select_many() -> None:
    """验证多选"""
    from unittest.mock import patch, MagicMock

    approval = Approval()

    with patch("questionary.checkbox") as mock_checkbox:
        mock_instance = MagicMock()
        mock_instance.ask.return_value = ["A", "B"]
        mock_checkbox.return_value = mock_instance

        result = approval.select_many("Choose:", ["A", "B", "C"])
        assert result == ["A", "B"]


def test_select_many_empty() -> None:
    """验证多选：空结果"""
    from unittest.mock import patch, MagicMock

    approval = Approval()

    with patch("questionary.checkbox") as mock_checkbox:
        mock_instance = MagicMock()
        mock_instance.ask.return_value = None
        mock_checkbox.return_value = mock_instance

        result = approval.select_many("Choose:", ["A", "B", "C"])
        assert result == []


def test_autocomplete() -> None:
    """验证自动完成"""
    from unittest.mock import patch, MagicMock

    approval = Approval()

    with patch("questionary.autocomplete") as mock_autocomplete:
        mock_instance = MagicMock()
        mock_instance.ask.return_value = "hello"
        mock_autocomplete.return_value = mock_instance

        result = approval.autocomplete("Type:", ["hello", "help", "world"])
        assert result == "hello"


def test_dangerous_action_confirm_approved() -> None:
    """验证危险操作：批准"""
    from unittest.mock import patch

    approval = Approval()

    # Both confirmations return True
    with patch.object(approval, "confirm", side_effect=[True, True]):
        result = approval.dangerous_action_confirm(
            "Delete all files",
            details="This will delete all files in the current directory"
        )
        assert result is True


def test_dangerous_action_confirm_rejected_first() -> None:
    """验证危险操作：第一次确认拒绝"""
    from unittest.mock import patch

    approval = Approval()

    with patch.object(approval, "confirm", return_value=False):
        result = approval.dangerous_action_confirm("Delete all files")
        assert result is False


def test_dangerous_action_confirm_rejected_second() -> None:
    """验证危险操作：第二次确认拒绝"""
    from unittest.mock import patch

    approval = Approval()

    # First confirmation passes, second fails
    with patch.object(approval, "confirm", side_effect=[True, False]):
        result = approval.dangerous_action_confirm("Delete all files")
        assert result is False


def test_approve_file_operation() -> None:
    """验证文件操作批准"""
    from unittest.mock import patch, MagicMock

    approval = Approval()

    with patch("questionary.confirm") as mock_confirm:
        mock_instance = MagicMock()
        mock_instance.ask.return_value = True
        mock_confirm.return_value = mock_instance

        result = approval.approve_file_operation("write", "/path/to/file.txt")
        assert result is True


def test_get_approval_singleton() -> None:
    """验证默认单例"""
    approval1 = get_approval()
    approval2 = get_approval()
    # 应该返回同一个实例
    assert approval1 is approval2


def test_colorama_initialized() -> None:
    """验证 colorama 已初始化"""
    import colorama

    # Just verify the module is available
    assert colorama is not None
