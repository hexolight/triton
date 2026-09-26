"""Builds dist/Triton.exe via PyInstaller. Run with the project's venv:
    .venv\\Scripts\\python build.py
"""

import subprocess
import sys

from app.utils.tcl_fix import fix_tcl_tk_env

fix_tcl_tk_env()

subprocess.run(
    [sys.executable, "-m", "PyInstaller", "Triton.spec", "--noconfirm"],
    check=True,
)
