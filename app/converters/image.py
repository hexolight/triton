"""Image <-> image conversion via Pillow."""

from __future__ import annotations
from pathlib import Path
from PIL import Image

from app.i18n import t

# Pillow needs RGB (no alpha) for these formats
_NO_ALPHA = {"jpg", "jpeg", "bmp"}

_SAVE_FORMAT = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "gif": "GIF",
    "tiff": "TIFF",
    "ico": "ICO",
}


def convert(src: Path, dst: Path) -> None:
    dst_ext = dst.suffix.lower().lstrip(".")
    fmt = _SAVE_FORMAT.get(dst_ext)
    if not fmt:
        raise RuntimeError(t("err_unsupported_image_format", ext=dst_ext))

    with Image.open(src) as im:
        if dst_ext in _NO_ALPHA and im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGB")
        elif im.mode == "P" and dst_ext not in ("gif", "ico"):
            im = im.convert("RGBA")

        save_kwargs = {}
        if fmt == "JPEG":
            save_kwargs["quality"] = 95
        if fmt == "ICO":
            save_kwargs["sizes"] = [(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]

        im.save(dst, fmt, **save_kwargs)
