from __future__ import annotations
import shutil
from dataclasses import dataclass, field
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
    # every file the conversion produced (more than one for PDF -> image),
    # all living in work_dir until the user downloads them
    outputs: list[Path] = field(default_factory=list)
    work_dir: Optional[Path] = None

    @property
    def src_ext(self) -> str:
        return self.src.suffix.lower().lstrip(".")

    def output_path(self, out_dir: Path) -> Path:
        return out_dir / f"{self.src.stem}.{self.target_ext}"

    def cleanup(self) -> None:
        """Delete this job's staged output and forget it."""
        if self.work_dir:
            shutil.rmtree(self.work_dir, ignore_errors=True)
        self.work_dir = None
        self.dst = None
        self.outputs = []
