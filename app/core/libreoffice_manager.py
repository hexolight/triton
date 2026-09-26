"""Locates LibreOffice (soffice.exe).

An earlier version of this module tried to scrape the LibreOffice mirror
index for the latest version number and silently download+launch the MSI.
That's fragile — version numbers and mirror URL layouts change, so the
guessed URL can 404 with no visible feedback. Sending the user to
LibreOffice's own official download page is slower to click through but
always resolves the current version and a working mirror correctly."""

from __future__ import annotations
import shutil
import webbrowser
from pathlib import Path
from typing import Optional

DOWNLOAD_PAGE = "https://www.libreoffice.org/download/download-libreoffice/"

COMMON_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]


def find_libreoffice() -> Optional[Path]:
    for p in COMMON_PATHS:
        path = Path(p)
        if path.exists():
            return path

    sys_soffice = shutil.which("soffice")
    if sys_soffice:
        return Path(sys_soffice)

    return None


def is_ready() -> bool:
    return find_libreoffice() is not None


def open_download_page() -> None:
    webbrowser.open(DOWNLOAD_PAGE)
