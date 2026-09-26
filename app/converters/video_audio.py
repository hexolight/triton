"""Video/audio conversion via ffmpeg, with real progress reporting."""

from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

from app.core.ffmpeg_manager import find_ffmpeg

# formats where re-encoding the video stream is pointless/lossy to skip when possible
AUDIO_ONLY_EXTS = {"mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "opus", "aiff"}

_CREATIONFLAGS = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0

ProgressCB = Optional[Callable[[float], None]]


def _duration_seconds(ffprobe: Path, src: Path) -> Optional[float]:
    try:
        proc = subprocess.run(
            [str(ffprobe), "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(src)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=15, creationflags=_CREATIONFLAGS,
        )
        return float(proc.stdout.decode().strip())
    except (ValueError, subprocess.SubprocessError):
        return None


def convert(src: Path, dst: Path, progress_cb: ProgressCB = None) -> None:
    ffmpeg, ffprobe = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg bulunamadı. Önce Ayarlar sekmesinden indirin.")

    dst_ext = dst.suffix.lower().lstrip(".")
    cmd = [str(ffmpeg), "-y", "-i", str(src)]

    if dst_ext in AUDIO_ONLY_EXTS:
        cmd += ["-vn"]  # strip video stream when target is audio-only

    cmd += ["-progress", "pipe:1", "-nostats", str(dst)]

    duration = _duration_seconds(ffprobe, src) if progress_cb else None

    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="ignore") as stderr_file:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=stderr_file,
            text=True, creationflags=_CREATIONFLAGS,
        )
        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                key, _, value = line.strip().partition("=")
                if key == "out_time" and progress_cb and duration:
                    try:
                        h, m, s = value.split(":")
                        seconds = int(h) * 3600 + int(m) * 60 + float(s)
                        progress_cb(min(seconds / duration, 0.99))
                    except ValueError:
                        pass
                elif key == "progress" and value == "end" and progress_cb:
                    progress_cb(1.0)
        finally:
            proc.wait()

        if proc.returncode != 0:
            stderr_file.seek(0)
            err = stderr_file.read()[-1200:]
            raise RuntimeError(f"FFmpeg hatası:\n{err}")
