"""Fit a string into a label's real pixel width with a middle ellipsis."""

from __future__ import annotations

import customtkinter as ctk


def fit_text(label: ctk.CTkLabel, text: str, max_px: int, head_ratio: float = 0.6, min_tail: int = 0) -> str:
    """Return `text`, or a middle-truncated version that fits in `max_px`.

    Middle truncation keeps both ends visible, which is what you want for
    file names (the extension) and paths (the drive and the last folder):
    end-truncation would make "report_final_v2.pdf" and "report_final_v3.pdf"
    look identical.
    """
    if max_px < 24 or not text:
        return text

    inner = label._label  # the real tk.Label; its font is what actually renders
    font = inner.cget("font")

    def px(s: str) -> int:
        return int(inner.tk.call("font", "measure", font, s))

    if px(text) <= max_px:
        return text

    best = "…"
    lo, hi = 1, len(text) - 1
    while lo <= hi:
        kept = (lo + hi) // 2
        tail = min(max(min_tail, int(kept * (1 - head_ratio))), kept - 1)
        head = kept - tail
        candidate = text[:head] + "…" + (text[-tail:] if tail else "")
        if px(candidate) <= max_px:
            best = candidate
            lo = kept + 1
        else:
            hi = kept - 1
    return best
