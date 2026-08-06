"""Windows Run-key autostart toggle (HKCU — no admin rights required)."""
from __future__ import annotations

import sys
import winreg
from pathlib import Path

from app.config.constants import APP_NAME
from app.core.logging_setup import get_logger

logger = get_logger(__name__)

_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _launch_command() -> str:
    repo_root = Path(__file__).resolve().parent.parent.parent
    launcher = repo_root / "run_hidden.pyw"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    python_exe = str(pythonw) if pythonw.exists() else sys.executable
    return f'"{python_exe}" "{launcher}"'


def set_autostart(enabled: bool) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                command = _launch_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
                logger.info("Autostart enabled: %s", command)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Autostart disabled")
                except FileNotFoundError:
                    pass
    except OSError as exc:
        logger.warning("Could not update autostart registry key: %s", exc)


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except OSError:
        return False
