"""Filesystem locations used by the app (bundled binaries, config, output)."""

from __future__ import annotations
import os
import shutil
import sys
import time
import uuid
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


def new_job_dir() -> Path:
    """A fresh, unique folder inside staging for one job's output, so jobs
    that share a file name (a/photo.png, b/photo.png) never overwrite each
    other and multi-file results (PDF pages) stay together."""
    d = staging_dir() / uuid.uuid4().hex
    d.mkdir(parents=True)
    return d


def purge_stale_staging(max_age_hours: float = 24) -> None:
    """Delete staging leftovers from earlier sessions (crashes, force-quits).
    Only entries older than `max_age_hours` are touched so a second running
    instance keeps its files."""
    cutoff = time.time() - max_age_hours * 3600
    for entry in staging_dir().iterdir():
        try:
            if entry.stat().st_mtime >= cutoff:
                continue
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)
        except OSError:
            pass


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
