"""Routes a (src, dst) conversion job to the right converter module."""

from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional

from app.core.formats import Engine, engine_for
from app.converters import video_audio, image, pdf, pdf_docx, office

_DISPATCH = {
    Engine.FFMPEG: video_audio.convert,
    Engine.IMAGE: image.convert,
    Engine.PDF_IMAGE: pdf.convert,
    Engine.PDF_DOCX: pdf_docx.convert,
    Engine.OFFICE: office.convert,
}

# only ffmpeg exposes real incremental progress; other engines run as a
# single blocking call so the caller falls back to an indeterminate spinner
_SUPPORTS_PROGRESS = {Engine.FFMPEG}


def convert_file(src: Path, dst: Path, progress_cb: Optional[Callable[[float], None]] = None) -> None:
    src_ext = src.suffix.lstrip(".")
    dst_ext = dst.suffix.lstrip(".")
    engine = engine_for(src_ext, dst_ext)
    if engine is None:
        raise RuntimeError(f"{src_ext.upper()} -> {dst_ext.upper()} dönüşümü desteklenmiyor.")

    fn = _DISPATCH[engine]
    dst.parent.mkdir(parents=True, exist_ok=True)
    if engine in _SUPPORTS_PROGRESS:
        fn(src, dst, progress_cb=progress_cb)
    else:
        fn(src, dst)
