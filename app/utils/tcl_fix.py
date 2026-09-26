"""Some Windows Python installs (notably python.org builds) put Tcl/Tk under
<install>/tcl/ instead of the usual <install>/lib/, which breaks tkinter's
own library lookup — both at runtime and during a PyInstaller build. This
points TCL_LIBRARY/TK_LIBRARY at sys.base_prefix (the real install, not a
venv) so tkinter finds them regardless of where the venv sits."""

from __future__ import annotations
import os
import sys
from pathlib import Path


def fix_tcl_tk_env() -> None:
    if os.environ.get("TCL_LIBRARY") and os.environ.get("TK_LIBRARY"):
        return

    base = Path(getattr(sys, "base_prefix", sys.prefix))
    for parent in (base / "tcl", base / "lib"):
        tcl_dirs = sorted(parent.glob("tcl8.*"))
        tk_dirs = sorted(parent.glob("tk8.*"))
        if tcl_dirs and tk_dirs:
            os.environ.setdefault("TCL_LIBRARY", str(tcl_dirs[-1]))
            os.environ.setdefault("TK_LIBRARY", str(tk_dirs[-1]))
            return
