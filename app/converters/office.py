"""Office document conversion (docx/doc/odt/rtf/txt/ppt/pptx/odp/xls/xlsx/ods/csv
<-> pdf and between each other) via LibreOffice headless."""

from __future__ import annotations
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.libreoffice_manager import find_libreoffice
from app.i18n import t


def convert(src: Path, dst: Path) -> None:
    soffice = find_libreoffice()
    if not soffice:
        raise RuntimeError(t("err_libreoffice_missing"))

    dst_ext = dst.suffix.lower().lstrip(".")

    # LibreOffice always names its output <source stem>.<ext>. Converting into a
    # private folder keeps two sources with the same stem (a.docx from two
    # directories) from overwriting each other's finished output.
    work = Path(tempfile.mkdtemp(prefix="triton_lo_", dir=dst.parent))
    try:
        cmd = [
            str(soffice), "--headless", "--norestore",
            "--convert-to", dst_ext,
            "--outdir", str(work),
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
            raise RuntimeError(t("err_libreoffice_failed", detail=err))

        produced = work / f"{src.stem}.{dst_ext}"
        if not produced.exists():
            raise RuntimeError(t("err_libreoffice_no_output"))
        produced.replace(dst)
    finally:
        shutil.rmtree(work, ignore_errors=True)
