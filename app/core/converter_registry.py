"""Routes a (src, dst) conversion job to the right converter module."""

from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional

from app.core.formats import Engine, engine_for
from app.converters import video_audio, image, pdf, pdf_docx, office
from app.i18n import t

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


def convert_file(src: Path, dst: Path, progress_cb: Optional[Callable[[float], None]] = None) -> list[Path]:
    """Convert src to dst and return every file produced. That is [dst]
    except when a converter writes extra files next to it (PDF pages)."""
    src_ext = src.suffix.lstrip(".")
    dst_ext = dst.suffix.lstrip(".")
    engine = engine_for(src_ext, dst_ext)
    if engine is None:
        raise RuntimeError(t("err_unsupported_conversion", src=src_ext.upper(), dst=dst_ext.upper()))

    fn = _DISPATCH[engine]
    dst.parent.mkdir(parents=True, exist_ok=True)
    if engine in _SUPPORTS_PROGRESS:
        produced = fn(src, dst, progress_cb=progress_cb)
    else:
        produced = fn(src, dst)
    return list(produced) if produced else [dst]
