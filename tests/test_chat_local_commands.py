import types


class _FakeAgent:
    def __init__(self, content: str):
        self._content = content

    def process(self, prompt: str):
        return types.SimpleNamespace(content=self._content)


def test_local_mkdir_and_read_dir(tmp_path, capsys):
    from claude_code.cli.main import _handle_local_command

    agent = _FakeAgent("")
    root = str(tmp_path)

    _handle_local_command(agent, "/mkdir a/b", root)
    assert (tmp_path / "a" / "b").is_dir()

    (tmp_path / "a" / "b" / "x.txt").write_text("hi", encoding="utf-8")

    _handle_local_command(agent, "/read-dir a --recursive --max 50", root)
    out = capsys.readouterr().out
    assert "b" in out
    assert "x.txt" in out


def test_local_read_file(tmp_path, capsys):
    from claude_code.cli.main import _handle_local_command

    agent = _FakeAgent("")
    (tmp_path / "t.txt").write_text("hello\n", encoding="utf-8")

    _handle_local_command(agent, "/read-file t.txt", str(tmp_path))
    out = capsys.readouterr().out
    assert "hello" in out


def test_local_gen_file_python(tmp_path):
    from claude_code.cli.main import _handle_local_command

    agent = _FakeAgent("def add(a, b):\n    return a + b\n")
    root = str(tmp_path)

    _handle_local_command(
        agent,
        "/gen-file gen.py --type python --overwrite -- Write a tiny module",
        root,
    )

    p = tmp_path / "gen.py"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "def add" in content


def test_local_path_escape_denied(tmp_path, capsys):
    from claude_code.cli.main import _handle_local_command

    agent = _FakeAgent("")

    _handle_local_command(agent, "/read-file ..\\README.md", str(tmp_path))
    out = capsys.readouterr().out
    assert "path escapes project_root" in out
