"""
Launcher for the bundled Midjourney v3 Studio Streamlit app.

Responsibilities
- Prompt user for UseAPI and Discord tokens (no secrets baked into binary).
- Materialize a runtime .streamlit/secrets.toml in a temp working directory.
- Copy the app assets into that runtime dir so relative paths still work.
- Run Streamlit headlessly on a random localhost port and present it inside a
  native window via pywebview (no external browser required).
"""

import os
import shutil
import socket
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional, Tuple


def _base_dir() -> Path:
    """Return directory where bundled assets live (PyInstaller-aware)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def _copy_assets(runtime_dir: Path) -> Tuple[Path, Path]:
    """
    Copy app.py and .streamlit assets into runtime_dir.

    Returns tuple of (app_path, secrets_dir_path).
    """
    src_root = _base_dir()
    app_src = src_root / "app.py"
    app_dst = runtime_dir / "app.py"
    shutil.copy2(app_src, app_dst)

    secrets_dir = runtime_dir / ".streamlit"
    secrets_dir.mkdir(parents=True, exist_ok=True)

    config_src = src_root / ".streamlit" / "config.toml"
    if config_src.exists():
        config_dst = secrets_dir / "config.toml"
        shutil.copy2(config_src, config_dst)

    return app_dst, secrets_dir


def _prompt_secret(label: str, default: str = "") -> str:
    """Prompt user for a secret token with GUI fallback to console."""
    # Prefer environment variable first to support automated launches.
    env_val = os.getenv(label.upper())
    if env_val:
        return env_val

    # GUI prompt using tkinter simpledialog.
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        value = simpledialog.askstring("Midjourney v3 Studio", label, initialvalue=default, show="*")
        root.destroy()
        if value:
            return value.strip()
    except Exception:
        pass

    # Fallback to console input (only visible if run in console mode).
    try:
        return input(f"Enter {label}: ").strip()
    except EOFError:
        return ""


def _write_secrets(secrets_dir: Path, api_token: str, discord_token: str) -> Path:
    """Write secrets.toml into the provided directory."""
    secrets_path = secrets_dir / "secrets.toml"
    content = f'api_token = "{api_token}"\ndiscord_token = "{discord_token}"\n'
    secrets_path.write_text(content, encoding="utf-8")
    return secrets_path


def _pick_port() -> int:
    """Grab an available localhost port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run_streamlit(app_path: Path, port: int, workdir: Path) -> None:
    """Launch Streamlit CLI inside a daemon thread."""
    def _runner() -> None:
        # Ensure Streamlit reads secrets/config from runtime workdir.
        os.chdir(workdir)
        sys.argv = [
            "streamlit",
            "run",
            str(app_path),
            "--server.headless",
            "true",
            "--server.port",
            str(port),
            "--server.address",
            "127.0.0.1",
            "--browser.gatherUsageStats",
            "false",
        ]
        from streamlit.web.cli import main

        main()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()


def main() -> None:
    runtime_dir = Path(tempfile.mkdtemp(prefix="mjstudio_runtime_"))
    app_path, secrets_dir = _copy_assets(runtime_dir)

    api_token = _prompt_secret("api_token")
    discord_token = _prompt_secret("discord_token")
    _write_secrets(secrets_dir, api_token, discord_token)

    port = _pick_port()
    _run_streamlit(app_path, port, runtime_dir)

    import webview  # pywebview

    window = webview.create_window(
        "Midjourney v3 Studio",
        url=f"http://127.0.0.1:{port}",
        width=1280,
        height=900,
        resizable=True,
        confirm_close=True,
    )

    def _on_closed() -> None:
        # Attempt cleanup; Streamlit server is daemonized and exits with process.
        try:
            shutil.rmtree(runtime_dir, ignore_errors=True)
        except Exception:
            pass

    webview.start(func=None, gui="tkinter", debug=False, http_server=False, shutdown=_on_closed, windows=[window])


if __name__ == "__main__":
    main()
