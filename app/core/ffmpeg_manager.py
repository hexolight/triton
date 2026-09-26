"""Locates ffmpeg/ffprobe, downloading a portable Windows build into the
app's own data folder on first use. Never touches system PATH or installs
anything system-wide — just files under app_data_dir()/bin."""

from __future__ import annotations
import shutil
import platform
from pathlib import Path
from typing import Callable, Optional

from app.utils.paths import bin_dir
from app.utils.downloader import download_file, extract_zip
from app.i18n import t

FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

ProgressCB = Optional[Callable[[str], None]]


def _bundled_paths() -> tuple[Path, Path]:
    d = bin_dir()
    return d / "ffmpeg.exe", d / "ffprobe.exe"


def find_ffmpeg() -> tuple[Optional[Path], Optional[Path]]:
    """Return (ffmpeg, ffprobe) paths if available, else (None, None)."""
    ffmpeg, ffprobe = _bundled_paths()
    if ffmpeg.exists() and ffprobe.exists():
        return ffmpeg, ffprobe

    sys_ffmpeg = shutil.which("ffmpeg")
    sys_ffprobe = shutil.which("ffprobe")
    if sys_ffmpeg and sys_ffprobe:
        return Path(sys_ffmpeg), Path(sys_ffprobe)

    return None, None


def is_ready() -> bool:
    a, b = find_ffmpeg()
    return a is not None and b is not None


def ensure_ffmpeg(status_cb: ProgressCB = None) -> tuple[Path, Path]:
    """Return (ffmpeg, ffprobe), downloading+extracting a portable build
    into app_data_dir()/bin if neither a bundled nor system copy exists."""
    ffmpeg, ffprobe = find_ffmpeg()
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe

    if platform.system() != "Windows":
        raise RuntimeError(t("err_ffmpeg_windows_only"))

    if status_cb:
        status_cb(t("ffmpeg_downloading"))

    dest_dir = bin_dir()
    zip_path = dest_dir / "_ffmpeg_download.zip"

    def _progress(done: int, total: int) -> None:
        if status_cb and total:
            pct = int(done * 100 / total)
            status_cb(t("ffmpeg_downloading_pct", pct=pct))

    download_file(FFMPEG_ZIP_URL, zip_path, progress=_progress)

    if status_cb:
        status_cb(t("ffmpeg_extracting"))

    extract_root = dest_dir / "_ffmpeg_extract"
    extract_zip(zip_path, extract_root)

    found_ffmpeg = next(extract_root.rglob("ffmpeg.exe"), None)
    found_ffprobe = next(extract_root.rglob("ffprobe.exe"), None)
    if not found_ffmpeg or not found_ffprobe:
        raise RuntimeError(t("err_ffmpeg_bad_package"))

    target_ffmpeg, target_ffprobe = _bundled_paths()
    shutil.copy2(found_ffmpeg, target_ffmpeg)
    shutil.copy2(found_ffprobe, target_ffprobe)

    shutil.rmtree(extract_root, ignore_errors=True)
    zip_path.unlink(missing_ok=True)

    if status_cb:
        status_cb(t("ffmpeg_ready_status"))

    return target_ffmpeg, target_ffprobe
