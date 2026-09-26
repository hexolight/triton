"""PDF <-> image conversion. No external binary needed (PyMuPDF + Pillow)."""

from __future__ import annotations
from pathlib import Path
from PIL import Image
import pymupdf as fitz

from app.i18n import t

RENDER_DPI = 200


def image_to_pdf(src: Path, dst: Path) -> None:
    with Image.open(src) as im:
        if im.mode in ("RGBA", "P", "LA"):
            im = im.convert("RGB")
        im.save(dst, "PDF")


def pdf_to_image(src: Path, dst: Path) -> None:
    """Renders every page of the PDF to an image. If there is more than one
    page, extra pages are written alongside dst as name_2.ext, name_3.ext..."""
    dst_ext = dst.suffix.lower().lstrip(".")
    pil_fmt = "JPEG" if dst_ext in ("jpg", "jpeg") else "PNG"

    doc = fitz.open(src)
    try:
        zoom = RENDER_DPI / 72
        matrix = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            out_path = dst if i == 0 else dst.with_stem(f"{dst.stem}_{i + 1}")
            pix.save(str(out_path)) if pil_fmt == "PNG" else \
                Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(out_path, "JPEG", quality=95)
    finally:
        doc.close()


def convert(src: Path, dst: Path) -> None:
    src_ext = src.suffix.lower().lstrip(".")
    dst_ext = dst.suffix.lower().lstrip(".")

    if src_ext == "pdf":
        pdf_to_image(src, dst)
    elif dst_ext == "pdf":
        image_to_pdf(src, dst)
    else:
        raise RuntimeError(t("err_unsupported_pdf_conversion", src=src_ext, dst=dst_ext))
