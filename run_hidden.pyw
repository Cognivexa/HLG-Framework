"""Windowless launcher used by the Windows autostart Run-key entry.

Registered (via app.core.autostart) as: pythonw.exe run_hidden.pyw — pythonw
has no console window, and inserting this file's own directory onto sys.path
means the app package resolves correctly regardless of the process's working
directory at Windows startup.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
