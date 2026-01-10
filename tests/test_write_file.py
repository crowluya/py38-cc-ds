"""
write-file command tests - strict file generation without prose contamination

TDD: 测试先行
"""

from pathlib import Path

from click.testing import CliRunner


def test_cli_write_file_command_exists() -> None:
    """验证 write-file 子命令存在"""
    from deep_code.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["write-file", "--help"])

    assert result.exit_code == 0
    assert "write-file" in result.output.lower()


def test_write_file_sanitizes_requirements(monkeypatch) -> None:
    """验证 requirements 输出会被清洗为可被 pip 解析的内容"""

    from deep_code.cli.main import cli

    class DummyTurn:
        def __init__(self, content: str):
            self.content = content

    class DummyAgent:
        def __init__(self, *_args, **_kwargs):
            pass

        def process(self, _prompt: str):
            # Intentionally include prose + code fences + invalid lines
            return DummyTurn(
                "以下是 requirements.txt：\n\n"
                "```\n"
                "# comment\n"
                "Flask==2.2.5\n"
                "pytest==7.2.2\n"
                "not a requirement\n"
                "```\n"
            )

    # Patch LLM creation path so no network is used
    monkeypatch.setattr("deep_code.cli.main.create_llm_client", lambda _settings: object())
    monkeypatch.setattr("deep_code.cli.main.Agent", DummyAgent)

    runner = CliRunner()
    with runner.isolated_filesystem():
        target = "requirements.txt"
        result = runner.invoke(
            cli,
            [
                "write-file",
                target,
                "Generate requirements for a Flask app",
                "--type",
                "requirements",
                "--overwrite",
            ],
        )

        assert result.exit_code == 0
        assert target in result.output

        content = Path(target).read_text(encoding="utf-8")
        assert "Flask==2.2.5" in content
        assert "pytest==7.2.2" in content
        assert "not a requirement" not in content
        assert "以下是" not in content
        assert "```" not in content
