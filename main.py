"""Entry point for Triton."""

import sys

from app.utils.tcl_fix import fix_tcl_tk_env

fix_tcl_tk_env()

if "--selftest" in sys.argv:
    # headless end-to-end check of the engines; see app/selftest.py
    from app.selftest import run as _selftest

    sys.exit(_selftest(sys.argv[sys.argv.index("--selftest") + 1]))

from app.ui.main_window import run  # noqa: E402  (must follow the env fix above)

if __name__ == "__main__":
    run()
