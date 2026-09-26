"""Central format registry: which extensions exist, which category they
belong to, and which engine converts between them."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Engine(Enum):
    FFMPEG = "ffmpeg"
    IMAGE = "image"          # Pillow
    PDF_IMAGE = "pdf_image"  # PyMuPDF <-> Pillow/img2pdf
    PDF_DOCX = "pdf_docx"    # pdf2docx
    OFFICE = "office"        # LibreOffice headless


class Category(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"


@dataclass(frozen=True)
class Format:
    ext: str
    category: Category
    label: str


VIDEO_EXTS = ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "m4v", "mpg", "ts", "3gp"]
AUDIO_EXTS = ["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "opus", "aiff"]
IMAGE_EXTS = ["jpg", "jpeg", "png", "webp", "bmp", "gif", "tiff", "ico"]
DOC_TO_PDF_ONLY = ["doc", "docx", "odt", "rtf", "txt", "ppt", "pptx", "odp", "xls", "xlsx", "ods", "csv"]
PDF_EXT = "pdf"

FORMATS: dict[str, Format] = {}
for e in VIDEO_EXTS:
    FORMATS[e] = Format(e, Category.VIDEO, e.upper())
for e in AUDIO_EXTS:
    FORMATS[e] = Format(e, Category.AUDIO, e.upper())
for e in IMAGE_EXTS:
    FORMATS[e] = Format(e, Category.IMAGE, e.upper())
for e in DOC_TO_PDF_ONLY:
    FORMATS[e] = Format(e, Category.DOCUMENT, e.upper())
FORMATS[PDF_EXT] = Format(PDF_EXT, Category.DOCUMENT, "PDF")

OFFICE_NATIVE_EXTS = set(DOC_TO_PDF_ONLY)  # everything LibreOffice can read/write directly


def category_of(ext: str) -> Category | None:
    fmt = FORMATS.get(ext.lower().lstrip("."))
    return fmt.category if fmt else None


def targets_for(ext: str) -> list[str]:
    """Return the list of extensions `ext` can be converted into."""
    ext = ext.lower().lstrip(".")
    cat = category_of(ext)
    if cat is None:
        return []

    if cat == Category.VIDEO:
        out = [e for e in VIDEO_EXTS if e != ext] + AUDIO_EXTS
        return out

    if cat == Category.AUDIO:
        return [e for e in AUDIO_EXTS if e != ext]

    if cat == Category.IMAGE:
        out = [e for e in IMAGE_EXTS if e != ext]
        out.append(PDF_EXT)
        return out

    if cat == Category.DOCUMENT:
        if ext == PDF_EXT:
            return ["docx"] + [e for e in IMAGE_EXTS if e in ("png", "jpg")]
        if ext in ("jpg", "jpeg", "png"):
            return [PDF_EXT]
        # generic office document -> anything else in its LibreOffice group, plus PDF
        word_group = ("doc", "docx", "odt", "rtf", "txt")
        slides_group = ("ppt", "pptx", "odp")
        sheet_group = ("xls", "xlsx", "ods", "csv")

        out = [PDF_EXT]
        for group in (word_group, slides_group, sheet_group):
            if ext in group:
                out += [e for e in group if e != ext]
                break
        return out

    return []


def engine_for(src_ext: str, dst_ext: str) -> Engine | None:
    src_ext, dst_ext = src_ext.lower().lstrip("."), dst_ext.lower().lstrip(".")
    src_cat, dst_cat = category_of(src_ext), category_of(dst_ext)
    if src_cat is None or dst_cat is None:
        return None

    if src_cat in (Category.VIDEO, Category.AUDIO) and dst_cat in (Category.VIDEO, Category.AUDIO):
        return Engine.FFMPEG

    if src_cat == Category.IMAGE and dst_cat == Category.IMAGE:
        return Engine.IMAGE

    if src_cat == Category.IMAGE and dst_ext == PDF_EXT:
        return Engine.PDF_IMAGE

    if src_ext == PDF_EXT and dst_ext in ("png", "jpg", "jpeg"):
        return Engine.PDF_IMAGE

    if src_ext == PDF_EXT and dst_ext == "docx":
        return Engine.PDF_DOCX

    if src_cat == Category.DOCUMENT and dst_cat == Category.DOCUMENT:
        return Engine.OFFICE

    return None


def all_extensions() -> list[str]:
    return sorted(FORMATS.keys())
