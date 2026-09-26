"""Filesystem locations used by the app (bundled binaries, config, output)."""

from __future__ import annotations
import os
import sys
from pathlib import Path

from app.i18n import t


def app_data_dir() -> Path:
    """Per-user folder where downloaded binaries/config live.
    Separate from the source tree so a PyInstaller build works the same way."""
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    d = base / "Triton"
    d.mkdir(parents=True, exist_ok=True)
    return d


def bin_dir() -> Path:
    d = app_data_dir() / "bin"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_output_dir() -> Path:
    """Suggested folder shown in the save dialog — not written to automatically."""
    d = Path.home() / "Desktop" / t("output_folder_name")
    d.mkdir(parents=True, exist_ok=True)
    return d


def staging_dir() -> Path:
    """Internal scratch folder where conversions land before the user
    explicitly downloads (saves) them somewhere. Not user-facing."""
    d = app_data_dir() / "staging"
    d.mkdir(parents=True, exist_ok=True)
    return d


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller extracts bundled data (assets/) to sys._MEIPASS, not
        # next to the exe — that only holds for --onedir builds, not --onefile.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def assets_dir() -> Path:
    return project_root() / "assets"
