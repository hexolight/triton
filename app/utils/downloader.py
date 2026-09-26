"""Small streaming downloader + zip extractor with progress callbacks."""

from __future__ import annotations
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests

ProgressCB = Optional[Callable[[int, int], None]]  # (bytes_done, bytes_total)


def download_file(url: str, dest: Path, progress: ProgressCB = None, timeout: int = 30) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)

    tmp.replace(dest)
    return dest


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)
