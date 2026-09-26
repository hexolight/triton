"""Entry point for Triton."""

from app.utils.tcl_fix import fix_tcl_tk_env

fix_tcl_tk_env()

from app.ui.main_window import run  # noqa: E402  (must follow the env fix above)

if __name__ == "__main__":
    run()
