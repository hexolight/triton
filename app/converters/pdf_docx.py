"""PDF -> DOCX via pdf2docx (pure Python, no external binary)."""

from __future__ import annotations
from pathlib import Path
from pdf2docx import Converter


def convert(src: Path, dst: Path) -> None:
    cv = Converter(str(src))
    try:
        cv.convert(str(dst))
    finally:
        cv.close()
