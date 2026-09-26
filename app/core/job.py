from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

STATUS_PENDING = "pending"
STATUS_CONVERTING = "converting"
STATUS_DONE = "done"
STATUS_ERROR = "error"


@dataclass
class Job:
    src: Path
    target_ext: str
    status: str = STATUS_PENDING
    error: Optional[str] = None
    dst: Optional[Path] = None

    @property
    def src_ext(self) -> str:
        return self.src.suffix.lower().lstrip(".")

    def output_path(self, out_dir: Path) -> Path:
        return out_dir / f"{self.src.stem}.{self.target_ext}"
