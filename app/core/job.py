from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Job:
    src: Path
    target_ext: str
    status: str = "Bekliyor"
    error: Optional[str] = None
    dst: Optional[Path] = None

    @property
    def src_ext(self) -> str:
        return self.src.suffix.lower().lstrip(".")

    def output_path(self, out_dir: Path) -> Path:
        return out_dir / f"{self.src.stem}.{self.target_ext}"
