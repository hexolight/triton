"""Office document conversion (docx/doc/odt/rtf/txt/ppt/pptx/odp/xls/xlsx/ods/csv
<-> pdf and between each other) via LibreOffice headless."""

from __future__ import annotations
import subprocess
from pathlib import Path

from app.core.libreoffice_manager import find_libreoffice


def convert(src: Path, dst: Path) -> None:
    soffice = find_libreoffice()
    if not soffice:
        raise RuntimeError("LibreOffice bulunamadı. Önce Ayarlar sekmesinden kurun.")

    dst_ext = dst.suffix.lower().lstrip(".")
    outdir = dst.parent

    cmd = [
        str(soffice), "--headless", "--norestore",
        "--convert-to", dst_ext,
        "--outdir", str(outdir),
        str(src),
    ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode(errors="ignore")[-1200:]
        raise RuntimeError(f"LibreOffice hatası:\n{err}")

    # LibreOffice names its output after the source file stem, not dst's name
    produced = outdir / f"{src.stem}.{dst_ext}"
    if produced.exists() and produced != dst:
        produced.replace(dst)

    if not dst.exists():
        raise RuntimeError("LibreOffice çıktı dosyası oluşturmadı.")
