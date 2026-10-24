"""Small tooltip: delayed on first hover, instant on neighbours, quick fade."""

from __future__ import annotations

import time
import tkinter as tk
from typing import Callable

from app.ui import theme


class Tooltip:
    DELAY_MS = 450
    GRACE_S = 0.4  # after one closes, the next opens with no delay and no fade
    _closed_at = 0.0
    _open: "Tooltip | None" = None

    def __init__(self, widget, text_fn: Callable[[], str]):
        self._widget = widget
        self._text_fn = text_fn
        self._show_job = None
        self._hide_job = None
        self._top: tk.Toplevel | None = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_press, add="+")
        widget.bind("<Destroy>", self._on_press, add="+")

    def _instant(self) -> bool:
        return Tooltip._open is not None or (time.monotonic() - Tooltip._closed_at) < self.GRACE_S

    def _on_enter(self, _e=None) -> None:
        if self._hide_job is not None:
            self._widget.after_cancel(self._hide_job)
            self._hide_job = None
        if self._top is not None or self._show_job is not None:
            return
        text = self._text_fn()
        if not text:
            return
        instant = self._instant()
        self._show_job = self._widget.after(0 if instant else self.DELAY_MS, lambda: self._show(text, instant))

    def _on_leave(self, _e=None) -> None:
        # CTk widgets bind both a canvas and an inner label, so moving between
        # them fires Leave+Enter; the short debounce stops the flicker.
        self._cancel_show()
        if self._top is not None and self._hide_job is None:
            self._hide_job = self._widget.after(40, self._hide)

    def _on_press(self, _e=None) -> None:
        self._cancel_show()
        self._hide()

    def _cancel_show(self) -> None:
        if self._show_job is not None:
            try:
                self._widget.after_cancel(self._show_job)
            except tk.TclError:
                pass
            self._show_job = None

    def _show(self, text: str, instant: bool) -> None:
        self._show_job = None
        try:
            if not self._widget.winfo_exists():
                return
            top = tk.Toplevel(self._widget)
            top.withdraw()
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            tk.Label(
                top, text=text, bg=theme.INK_HOVER, fg=theme.TEXT, justify="left", wraplength=520,
                font=(theme.FONT_FAMILY, 10), padx=9, pady=5, bd=0,
                highlightthickness=1, highlightbackground=theme.INK_LINE,
            ).pack()
            top.update_idletasks()
            px, py = self._widget.winfo_pointerxy()
            w, h = top.winfo_reqwidth(), top.winfo_reqheight()
            x = min(px + 12, top.winfo_screenwidth() - w - 8)
            y = py + 20
            if y + h > top.winfo_screenheight() - 8:
                y = py - h - 10
            top.geometry(f"+{max(x, 0)}+{max(y, 0)}")
            top.attributes("-alpha", 1.0 if instant else 0.0)
            top.deiconify()
        except tk.TclError:
            return
        self._top = top
        Tooltip._open = self
        if not instant:
            self._fade(top, (0.4, 0.75, 1.0))

    def _fade(self, top: tk.Toplevel, steps: tuple[float, ...]) -> None:
        if not steps or top is not self._top:
            return
        try:
            top.attributes("-alpha", steps[0])
            top.after(35, self._fade, top, steps[1:])
        except tk.TclError:
            pass

    def _hide(self) -> None:
        self._hide_job = None
        if self._top is not None:
            try:
                self._top.destroy()
            except tk.TclError:
                pass
            self._top = None
            if Tooltip._open is self:
                Tooltip._open = None
            Tooltip._closed_at = time.monotonic()
