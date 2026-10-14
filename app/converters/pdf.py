"""PDF <-> image conversion. No external binary needed (PyMuPDF + Pillow)."""

from __future__ import annotations
from pathlib import Path
from PIL import Image
import pymupdf as fitz

from app.converters.image import flatten_to_rgb, prepare
from app.i18n import t

RENDER_DPI = 200


def image_to_pdf(src: Path, dst: Path) -> None:
    with Image.open(src) as opened:
        im = flatten_to_rgb(prepare(opened))
        im.save(dst, "PDF")


def pdf_to_image(src: Path, dst: Path) -> list[Path]:
    """Renders every page of the PDF to an image. If there is more than one
    page, extra pages are written alongside dst as name_2.ext, name_3.ext...
    Returns every file written, first page first."""
    dst_ext = dst.suffix.lower().lstrip(".")
    pil_fmt = "JPEG" if dst_ext in ("jpg", "jpeg") else "PNG"

    outputs: list[Path] = []
    doc = fitz.open(src)
    try:
        zoom = RENDER_DPI / 72
        matrix = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            out_path = dst if i == 0 else dst.with_stem(f"{dst.stem}_{i + 1}")
            if pil_fmt == "PNG":
                pix.save(str(out_path))
            else:
                Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(out_path, "JPEG", quality=95)
            outputs.append(out_path)
    finally:
        doc.close()
    return outputs


def convert(src: Path, dst: Path) -> list[Path]:
    src_ext = src.suffix.lower().lstrip(".")
    dst_ext = dst.suffix.lower().lstrip(".")

    if src_ext == "pdf":
        return pdf_to_image(src, dst)
    elif dst_ext == "pdf":
        image_to_pdf(src, dst)
        return [dst]
    else:
        raise RuntimeError(t("err_unsupported_pdf_conversion", src=src_ext, dst=dst_ext))
