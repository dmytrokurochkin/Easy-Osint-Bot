import sys

import core.bootstrap as bootstrap


def test_ensure_env_file_prompts_when_missing(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    monkeypatch.setattr(bootstrap, "ENV_PATH", env_path)

    answers = iter(["123:ABC", "999"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    bootstrap._ensure_env_file()

    content = env_path.read_text(encoding="utf-8")
    assert "BOT_TOKEN=123:ABC" in content
    assert "ADMIN_ID=999" in content


def test_ensure_env_file_skips_when_present(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("BOT_TOKEN=existing\nADMIN_ID=1\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "ENV_PATH", env_path)

    def _fail_input(prompt):
        raise AssertionError("should not prompt when .env already exists")

    monkeypatch.setattr("builtins.input", _fail_input)

    bootstrap._ensure_env_file()

    assert env_path.read_text(encoding="utf-8") == "BOT_TOKEN=existing\nADMIN_ID=1\n"


def test_ensure_dependencies_installs_when_module_missing(monkeypatch):
    monkeypatch.setattr(bootstrap.importlib.util, "find_spec", lambda name: None)
    calls = []
    monkeypatch.setattr(bootstrap.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))

    bootstrap._ensure_dependencies()

    assert len(calls) == 1
    assert calls[0][:4] == [sys.executable, "-m", "pip", "install"]


def test_ensure_dependencies_skips_when_all_present(monkeypatch):
    monkeypatch.setattr(bootstrap.importlib.util, "find_spec", lambda name: object())

    def _fail_run(cmd, **kwargs):
        raise AssertionError("should not install when all modules are present")

    monkeypatch.setattr(bootstrap.subprocess, "run", _fail_run)

    bootstrap._ensure_dependencies()


def test_ensure_ghunt_skips_when_already_installed(monkeypatch):
    monkeypatch.setattr(bootstrap.shutil, "which", lambda name: "/usr/bin/ghunt")

    def _fail_run(cmd, **kwargs):
        raise AssertionError("should not install when ghunt is already present")

    monkeypatch.setattr(bootstrap.subprocess, "run", _fail_run)

    bootstrap._ensure_ghunt()


def test_ensure_ghunt_installs_via_pipx_when_missing(monkeypatch):
    which_map = {"ghunt": None, "pipx": "/usr/bin/pipx"}
    monkeypatch.setattr(bootstrap.shutil, "which", lambda name: which_map.get(name))
    calls = []
    monkeypatch.setattr(bootstrap.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))

    bootstrap._ensure_ghunt()

    assert any("ghunt" in cmd for cmd in calls)


def test_ensure_ready_calls_all_steps_in_order_and_returns_config(monkeypatch):
    calls = []
    monkeypatch.setattr(bootstrap, "_ensure_dependencies", lambda: calls.append("deps"))
    monkeypatch.setattr(bootstrap, "_ensure_env_file", lambda: calls.append("env"))
    monkeypatch.setattr(bootstrap, "_load_env", lambda: calls.append("load_dotenv"))
    monkeypatch.setattr(bootstrap, "_ensure_ghunt", lambda: calls.append("ghunt"))
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("ADMIN_ID", "1")

    config = bootstrap.ensure_ready()

    assert calls == ["deps", "env", "load_dotenv", "ghunt"]
    assert config.bot_token == "123:ABC"
    assert config.admin_id == 1
