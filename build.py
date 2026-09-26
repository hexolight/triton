"""Builds dist/Triton.exe (or dist/Triton-EN.exe) via PyInstaller.

    .venv\\Scripts\\python build.py            # Turkish build (default)
    .venv\\Scripts\\python build.py --lang en  # English build
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from app.utils.tcl_fix import fix_tcl_tk_env

parser = argparse.ArgumentParser()
parser.add_argument("--lang", choices=["tr", "en"], default="tr")
args = parser.parse_args()

fix_tcl_tk_env()

# Baked into the exe so it defaults to the right language without the end
# user needing to set an environment variable. See app/i18n.py.
Path("app/_lang_default.py").write_text(f'DEFAULT_LANG = "{args.lang}"\n', encoding="utf-8")

exe_name = "Triton" if args.lang == "tr" else "Triton-EN"
env = os.environ.copy()
env["TRITON_EXE_NAME"] = exe_name

subprocess.run(
    [sys.executable, "-m", "PyInstaller", "Triton.spec", "--noconfirm"],
    check=True, env=env,
)

print(f"\nBuilt dist\\{exe_name}.exe ({args.lang})")
