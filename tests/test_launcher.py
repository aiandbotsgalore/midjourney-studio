import os
import shutil
import sys
from pathlib import Path

# Ensure repository root is importable for worker processes
sys.path.append(str(Path(__file__).resolve().parents[1]))

import launcher


def test_base_dir_prefers_meipass(tmp_path, monkeypatch):
    sentinel = tmp_path / "bundle"
    sentinel.mkdir()
    monkeypatch.setattr(sys, "_MEIPASS", str(sentinel), raising=False)
    try:
        assert launcher._base_dir() == sentinel
    finally:
        # Clean up to avoid side effects on other tests
        delattr(sys, "_MEIPASS")


def test_write_secrets_creates_file(tmp_path):
    secrets_dir = tmp_path / ".streamlit"
    secrets_dir.mkdir()
    path = launcher._write_secrets(secrets_dir, "api123", "disc456")
    assert path.exists()
    content = path.read_text()
    assert 'api_token = "api123"' in content
    assert 'discord_token = "disc456"' in content


def test_pick_port_is_bindable():
    port = launcher._pick_port()
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))
        # If bind succeeds, port was free. Close automatically.


def test_copy_assets_copies_app_and_config(tmp_path, monkeypatch):
    # Arrange a fake bundle root
    bundle_root = tmp_path / "bundle"
    streamlit_dir = bundle_root / ".streamlit"
    streamlit_dir.mkdir(parents=True)
    (bundle_root / "app.py").write_text("print('hello')", encoding="utf-8")
    (streamlit_dir / "config.toml").write_text("test=true", encoding="utf-8")

    monkeypatch.setattr(launcher, "_base_dir", lambda: bundle_root)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    app_path, secrets_dir = launcher._copy_assets(runtime_dir)

    assert app_path.exists()
    assert secrets_dir.exists()
    assert (secrets_dir / "config.toml").exists()
    assert "hello" in app_path.read_text()
    assert "test=true" in (secrets_dir / "config.toml").read_text()


def test_prompt_secret_env_override(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "env-api")
    # Should short-circuit to env and not prompt
    assert launcher._prompt_secret("api_token") == "env-api"
