"""Tests for the deterministic secret-to-.env remediation (Issue Sidebar's
"Move to .env" action) — never invoked automatically, only on explicit
user click, so correctness here matters a lot."""
from __future__ import annotations

from app.pipelines.loop.env_remediation import move_secret_to_env


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_moves_simple_string_secret_to_env(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    code_file = _write(tmp_path / "app.py", 'DB_PASSWORD = "SuperSecret123!"\n\nprint("hi")\n')

    result = move_secret_to_env(str(code_file), 1)

    assert result.success
    assert result.variable_name == "DB_PASSWORD"
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "DB_PASSWORD=SuperSecret123!" in env_text

    new_code = code_file.read_text(encoding="utf-8")
    assert 'os.environ.get("DB_PASSWORD", "")' in new_code
    assert "SuperSecret123!" not in new_code
    assert "import os" in new_code


def test_preserves_indentation_and_trailing_comment(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    code_file = _write(
        tmp_path / "app.py",
        "class Config:\n    API_KEY = \"sk-abc123\"  # TODO rotate\n",
    )

    result = move_secret_to_env(str(code_file), 2)

    assert result.success
    new_code = code_file.read_text(encoding="utf-8")
    assert '    API_KEY = os.environ.get("API_KEY", "")  # TODO rotate' in new_code


def test_creates_env_file_when_missing(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    code_file = _write(tmp_path / "app.py", 'TOKEN = "abc"\n')
    assert not (tmp_path / ".env").exists()

    result = move_secret_to_env(str(code_file), 1)

    assert result.success
    assert (tmp_path / ".env").exists()


def test_appends_to_existing_env_file_without_clobbering_it(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    (tmp_path / ".env").write_text("EXISTING_VAR=keep-me\n")
    code_file = _write(tmp_path / "app.py", 'TOKEN = "abc"\n')

    move_secret_to_env(str(code_file), 1)

    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "EXISTING_VAR=keep-me" in env_text
    assert "TOKEN=abc" in env_text


def test_adds_env_to_gitignore(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    code_file = _write(tmp_path / "app.py", 'TOKEN = "abc"\n')

    move_secret_to_env(str(code_file), 1)

    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore.split()


def test_does_not_duplicate_import_os_if_already_present(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    code_file = _write(tmp_path / "app.py", 'import os\n\nTOKEN = "abc"\n')

    result = move_secret_to_env(str(code_file), 3)

    assert result.success
    new_code = code_file.read_text(encoding="utf-8")
    assert new_code.count("import os") == 1


def test_backs_up_original_file_before_modifying(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    code_file = _write(tmp_path / "app.py", 'TOKEN = "abc"\n')

    result = move_secret_to_env(str(code_file), 1)

    assert result.backup_path
    from pathlib import Path
    assert Path(result.backup_path).read_text(encoding="utf-8") == 'TOKEN = "abc"\n'


def test_fails_gracefully_on_non_assignment_line(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    code_file = _write(tmp_path / "app.py", "def f():\n    return 1\n")

    result = move_secret_to_env(str(code_file), 2)

    assert not result.success
    assert "    return 1\n" == code_file.read_text(encoding="utf-8").splitlines(keepends=True)[1]


def test_fails_gracefully_on_out_of_range_line(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest\n")
    code_file = _write(tmp_path / "app.py", 'TOKEN = "abc"\n')

    result = move_secret_to_env(str(code_file), 99)

    assert not result.success
