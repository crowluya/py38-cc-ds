import json
import types


class _FakeAgent:
    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.calls = []

    def process(self, prompt: str):
        self.calls.append(prompt)
        if not self._outputs:
            return types.SimpleNamespace(content=json.dumps({"actions": [{"type": "done"}]}))
        return types.SimpleNamespace(content=self._outputs.pop(0))


def test_parse_auto_actions_accepts_fenced_json():
    from deep_code.cli.main import _parse_auto_actions

    out = "```json\n{\"actions\":[{\"type\":\"done\"}]}\n```"
    actions = _parse_auto_actions(out)
    assert actions == [{"type": "done"}]


def test_auto_mode_executes_mkdir_and_write(tmp_path, monkeypatch):
    from deep_code.cli import main as cli_main
    from deep_code.security.permissions import PermissionManager, PermissionRule, PermissionAction, PermissionDomain

    agent = _FakeAgent(
        [
            json.dumps(
                {
                    "actions": [
                        {"type": "mkdir", "path": "a/b"},
                        {"type": "write_file", "path": "a/b/t.txt", "content": "hello\n", "overwrite": True},
                        {"type": "done"},
                    ]
                }
            )
        ]
    )

    pm = PermissionManager()
    pm.add_rule(PermissionRule(domain=PermissionDomain.FILE_WRITE, action=PermissionAction.ALLOW, pattern="*"))
    pm.add_rule(PermissionRule(domain=PermissionDomain.FILE_READ, action=PermissionAction.ALLOW, pattern="*"))
    pm.add_rule(PermissionRule(domain=PermissionDomain.COMMAND, action=PermissionAction.ALLOW, pattern="*"))

    cli_main._process_input_auto(
        agent=agent,
        user_input="do it",
        project_root=str(tmp_path),
        auto_approve=True,
        permission_manager=pm,
        max_steps=5,
    )

    assert (tmp_path / "a" / "b").is_dir()
    assert (tmp_path / "a" / "b" / "t.txt").read_text(encoding="utf-8") == "hello\n"


def test_auto_mode_path_escape_is_denied(tmp_path):
    from deep_code.cli.main import _process_input_auto
    from deep_code.security.permissions import PermissionManager, PermissionRule, PermissionAction, PermissionDomain

    agent = _FakeAgent(
        [
            json.dumps(
                {
                    "actions": [
                        {"type": "read_file", "path": "..\\README.md"},
                        {"type": "done"},
                    ]
                }
            )
        ]
    )

    pm = PermissionManager()
    pm.add_rule(PermissionRule(domain=PermissionDomain.FILE_READ, action=PermissionAction.ALLOW, pattern="*"))

    _process_input_auto(
        agent=agent,
        user_input="read",
        project_root=str(tmp_path),
        auto_approve=True,
        permission_manager=pm,
        max_steps=3,
    )

    # The model should have been called at least once.
    assert agent.calls


def test_auto_mode_run_requires_approval_when_not_auto_approve(tmp_path, monkeypatch):
    from deep_code.cli import main as cli_main
    from deep_code.security.permissions import PermissionManager, PermissionRule, PermissionAction, PermissionDomain

    agent = _FakeAgent(
        [
            json.dumps(
                {
                    "actions": [
                        {"type": "run", "command": "python -c \"print(123)\""},
                        {"type": "done"},
                    ]
                }
            )
        ]
    )

    pm = PermissionManager()
    pm.add_rule(PermissionRule(domain=PermissionDomain.COMMAND, action=PermissionAction.ASK, pattern="*"))

    class _A:
        def confirm(self, message, default=False):
            return False

    monkeypatch.setattr(cli_main, "get_approval", lambda: _A())

    cli_main._process_input_auto(
        agent=agent,
        user_input="run",
        project_root=str(tmp_path),
        auto_approve=False,
        permission_manager=pm,
        max_steps=3,
    )

    assert agent.calls


def test_auto_collect_prompts_on_ask_and_allows(tmp_path):
    from deep_code.cli import main as cli_main
    from deep_code.security.permissions import PermissionManager, PermissionRule, PermissionAction, PermissionDomain

    agent = _FakeAgent(
        [
            json.dumps(
                {
                    "actions": [
                        {"type": "mkdir", "path": "a/b"},
                        {"type": "write_file", "path": "a/b/t.txt", "content": "hello\n", "overwrite": True},
                        {"type": "done"},
                    ]
                }
            )
        ]
    )

    pm = PermissionManager()
    pm.add_rule(PermissionRule(domain=PermissionDomain.FILE_WRITE, action=PermissionAction.ASK, pattern="*"))
    pm.add_rule(PermissionRule(domain=PermissionDomain.FILE_READ, action=PermissionAction.ALLOW, pattern="*"))

    asked = {"n": 0}

    def _cb(message: str) -> bool:
        asked["n"] += 1
        return True

    results = cli_main._process_input_auto_collect(
        agent=agent,
        user_input="do it",
        project_root=str(tmp_path),
        auto_approve=False,
        permission_manager=pm,
        mode="default",
        max_steps=3,
        approval_callback=_cb,
    )

    assert asked["n"] >= 1
    assert (tmp_path / "a" / "b").is_dir()
    assert (tmp_path / "a" / "b" / "t.txt").read_text(encoding="utf-8") == "hello\n"
    assert results


def test_auto_collect_prompts_on_ask_and_denies(tmp_path):
    from deep_code.cli import main as cli_main
    from deep_code.security.permissions import PermissionManager, PermissionRule, PermissionAction, PermissionDomain

    agent = _FakeAgent(
        [
            json.dumps(
                {
                    "actions": [
                        {"type": "write_file", "path": "a/b/t.txt", "content": "hello\n", "overwrite": True},
                        {"type": "done"},
                    ]
                }
            )
        ]
    )

    pm = PermissionManager()
    pm.add_rule(PermissionRule(domain=PermissionDomain.FILE_WRITE, action=PermissionAction.ASK, pattern="*"))

    asked = {"n": 0}

    def _cb(message: str) -> bool:
        asked["n"] += 1
        return False

    results = cli_main._process_input_auto_collect(
        agent=agent,
        user_input="do it",
        project_root=str(tmp_path),
        auto_approve=False,
        permission_manager=pm,
        mode="default",
        max_steps=3,
        approval_callback=_cb,
    )

    assert asked["n"] >= 1
    assert not (tmp_path / "a" / "b" / "t.txt").exists()
    assert results
    assert any(r.get("type") == "write_file" and not r.get("ok") for r in results)
