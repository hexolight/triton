from __future__ import annotations

import queue
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from app.core import formats
from app.core.job import Job, STATUS_PENDING, STATUS_CONVERTING, STATUS_DONE, STATUS_ERROR
from app.core.converter_registry import convert_file
from app.core import ffmpeg_manager, libreoffice_manager
from app.converters import docs
from app.utils.paths import default_output_dir, staging_dir, assets_dir
from app.ui import theme, icons
from app.ui.textfit import fit_text
from app.ui.tooltip import Tooltip
from app.i18n import t, tn, LANG

ctk.set_appearance_mode("dark")

# Each row is ~6 canvas-backed widgets and costs 30-50 ms to first paint, and
# the cost grows with the number of mapped rows. So only a page of rows is ever
# on screen; the rest live as plain Job objects until the user asks for more.
PAGE_SIZE = 40
ROWS_PER_TICK = 2  # rows built per 10 ms tick, so adding files never freezes the window

# --- optional drag & drop -------------------------------------------------
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    class _BaseWindow(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.TkdndVersion = TkinterDnD._require(self)

    DND_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _BaseWindow = ctk.CTk
    DND_AVAILABLE = False


# --- button vocabulary: one primary at a time, everything else recedes -------
def _primary() -> dict:
    return dict(fg_color=theme.CHAMPAGNE, hover_color=theme.CHAMPAGNE_HOVER, text_color=theme.INK,
                text_color_disabled=theme.TEXT_MUTED, border_width=0)


def _secondary() -> dict:
    return dict(fg_color=theme.INK_HOVER, hover_color=theme.INK_LINE, text_color=theme.TEXT,
                text_color_disabled=theme.TEXT_MUTED, border_width=0)


def _ghost() -> dict:
    return dict(fg_color="transparent", hover_color=theme.INK_HOVER, text_color=theme.TEXT_MUTED,
                text_color_disabled=theme.TEXT_MUTED, border_width=0)


def _disabled_primary() -> dict:
    return dict(fg_color=theme.INK_HOVER, hover_color=theme.INK_HOVER, text_color=theme.TEXT_MUTED,
                text_color_disabled=theme.TEXT_MUTED, border_width=0)


def _fmt_size(n: int) -> str:
    v = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if v < 1024 or unit == "GB":
            s = f"{v:.0f}" if unit == "B" else f"{v:.1f}"
            return (s.replace(".", ",") if LANG == "tr" else s) + f" {unit}"
        v /= 1024
    return ""


def _unique_dest(folder: Path, name: str) -> Path:
    """Never overwrite a file the user already has in the destination."""
    dest = folder / name
    n = 2
    while dest.exists():
        dest = folder / f"{Path(name).stem} ({n}){Path(name).suffix}"
        n += 1
    return dest


class JobRow(ctk.CTkFrame):
    def __init__(self, master, job: Job, on_remove, on_target_change, on_download):
        super().__init__(master, fg_color=theme.INK_RAISED, corner_radius=12)
        self.job = job
        self._on_remove = on_remove
        self._on_target_change = on_target_change
        self._on_download = on_download

        try:
            size = _fmt_size(job.src.stat().st_size)
        except OSError:
            size = ""
        folder = job.src.parent.name or str(job.src.parent)
        self._full_name = job.src.name
        self._full_meta = "  ·  ".join(p for p in (job.src_ext.upper(), size, folder) if p)
        self._name_shown = self._full_name
        self._meta_shown = self._full_meta
        self._name_w = self._meta_w = -1

        self.grid_columnconfigure(0, weight=1)

        self.name_lbl = ctk.CTkLabel(
            self, text=self._full_name, anchor="w",
            text_color=theme.TEXT, font=(theme.FONT_STRONG, 13),
        )
        self.name_lbl.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=(11, 0))

        self.meta_lbl = ctk.CTkLabel(
            self, text=self._full_meta, anchor="w",
            text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 11),
        )
        self.meta_lbl.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=(0, 11))

        ctk.CTkLabel(self, text="", image=icons.icon("arrow_right", theme.TEXT_MUTED, 16)).grid(
            row=0, column=1, rowspan=2, padx=(8, 8))

        targets = formats.targets_for(job.src_ext)
        self.target_menu = ctk.CTkOptionMenu(
            self, values=targets or ["-"], width=88, height=30, corner_radius=8,
            fg_color=theme.INK_HOVER, button_color=theme.INK_HOVER, button_hover_color=theme.INK_LINE,
            text_color=theme.TEXT, dropdown_fg_color=theme.INK_RAISED, dropdown_hover_color=theme.INK_HOVER,
            dropdown_text_color=theme.TEXT, font=(theme.FONT_FAMILY, 12), dropdown_font=(theme.FONT_FAMILY, 12),
            command=self._target_changed,
        )
        if job.target_ext in targets:
            self.target_menu.set(job.target_ext)
        self.target_menu.grid(row=0, column=2, rowspan=2, padx=(0, 14))

        self.status_btn = ctk.CTkButton(
            self, text="", width=136, height=30, corner_radius=8, font=(theme.FONT_FAMILY, 12),
            command=self._on_status_click,
        )
        self.status_btn.grid(row=0, column=3, rowspan=2, padx=(0, 4))

        remove_btn = ctk.CTkButton(
            self, text="", image=icons.icon("close", theme.TEXT_MUTED, 14), width=30, height=30,
            corner_radius=8, **_ghost(), command=lambda: self._on_remove(self),
        )
        remove_btn.grid(row=0, column=4, rowspan=2, padx=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            self, height=4, progress_color=theme.CHAMPAGNE, fg_color=theme.INK_LINE,
        )
        self.progress_bar.set(0)

        self.name_lbl.bind("<Configure>", lambda _e: self._refit_name())
        self.meta_lbl.bind("<Configure>", lambda _e: self._refit_meta())
        Tooltip(self.name_lbl, lambda: self._full_name if self._name_shown != self._full_name else "")
        Tooltip(self.meta_lbl, lambda: str(self.job.src))
        Tooltip(remove_btn, lambda: t("tooltip_remove"))
        Tooltip(self.status_btn, lambda: (self.job.error or "").strip().splitlines()[0][:200]
                if self.job.status == STATUS_ERROR and self.job.error else "")

        # a row built late (paged in mid-conversion) must show the job's real state
        self.set_status(job.status, job.error)

    def _refit_name(self) -> None:
        w = self.name_lbl.winfo_width()
        if w == self._name_w:
            return
        self._name_w = w
        shown = fit_text(self.name_lbl, self._full_name, w - 8, head_ratio=0.65, min_tail=len(self.job.src.suffix) + 3)
        if shown != self._name_shown:
            self._name_shown = shown
            self.name_lbl.configure(text=shown)

    def _refit_meta(self) -> None:
        w = self.meta_lbl.winfo_width()
        if w == self._meta_w:
            return
        self._meta_w = w
        shown = fit_text(self.meta_lbl, self._full_meta, w - 8, head_ratio=0.7)
        if shown != self._meta_shown:
            self._meta_shown = shown
            self.meta_lbl.configure(text=shown)

    def _target_changed(self, value: str) -> None:
        self._on_target_change(self.job, value)

    def set_status(self, status: str, error: str | None = None) -> None:
        self.job.status = status
        self.job.error = error
        btn = self.status_btn
        if status == STATUS_DONE:
            btn.configure(
                state="normal", text=t("status_save"), image=icons.icon("save", theme.CHAMPAGNE, 16), compound="left",
                fg_color="transparent", hover_color=theme.INK_HOVER, text_color=theme.CHAMPAGNE,
                border_width=1, border_color=theme.CHAMPAGNE_DIM,
            )
        elif status == STATUS_ERROR:
            btn.configure(
                state="normal", text=t("status_error"), image=icons.icon("alert", theme.ERROR, 16), compound="left",
                fg_color="transparent", hover_color=theme.INK_HOVER, text_color=theme.ERROR, border_width=0,
            )
        elif status == STATUS_CONVERTING:
            btn.configure(
                state="disabled", text=t("status_converting"), image=None, fg_color="transparent",
                text_color_disabled=theme.CHAMPAGNE_DIM, border_width=0,
            )
        else:
            btn.configure(
                state="disabled", text=t("status_pending"), image=None, fg_color="transparent",
                text_color_disabled=theme.TEXT_MUTED, border_width=0,
            )

        if status == STATUS_CONVERTING:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.grid(row=2, column=0, columnspan=5, sticky="ew", padx=16, pady=(0, 12))
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            self.progress_bar.grid_forget()

    def set_progress(self, fraction: float) -> None:
        if self.job.status != STATUS_CONVERTING:
            return
        fraction = max(0.0, min(1.0, fraction))
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(fraction)
        self.status_btn.configure(text=f"{int(fraction * 100)}%")

    def _on_status_click(self) -> None:
        if self.job.status == STATUS_ERROR:
            if self.job.error:
                messagebox.showerror(t("conversion_error_title", name=self.job.src.name), self.job.error)
        elif self.job.status == STATUS_DONE:
            self._on_download(self.job)


class App(_BaseWindow):
    def __init__(self):
        super().__init__()
        self.title(t("app_title"))
        self.geometry("980x680")
        self.minsize(820, 560)
        self.configure(fg_color=theme.INK)

        self.jobs: list[Job] = []                  # every file the user added
        self.rows: list[JobRow] = []               # widgets for jobs[:len(rows)]
        self._row_by_job: dict[int, JobRow] = {}
        self._paths: set[str] = set()
        self._visible_limit = PAGE_SIZE
        self._materialize_job = None
        self._note = ""
        self._run_jobs: list[Job] = []

        self.out_dir = default_output_dir()
        self._out_dir_w = -1
        self._ui_queue: queue.Queue = queue.Queue()
        self._converting = False
        self._view = "main"

        self._set_window_icon()
        self._build_layout()
        self._refresh_engine_status()
        self._sync_empty_state()
        self._refresh_ui_state()
        self._poll_ui_queue()

        self.bind("<Control-o>", lambda _e: self._add_files())
        self.bind("<Escape>", lambda _e: self._show_view("main"))
        if DND_AVAILABLE:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<DropEnter>>", self._on_drop_enter)
            self.dnd_bind("<<DropLeave>>", self._on_drop_leave)
            self.dnd_bind("<<Drop>>", self._on_drop)

    # ------------------------------------------------------------------ shell
    def _set_window_icon(self) -> None:
        ico_path = assets_dir() / "app.ico"
        if ico_path.exists():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:  # noqa: BLE001 - icon is cosmetic, never fatal
                pass

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 14))

        logo_path = assets_dir() / "logo.png"
        if logo_path.exists():
            logo_img = ctk.CTkImage(light_image=Image.open(logo_path), size=(38, 38))
            ctk.CTkLabel(header, image=logo_img, text="").pack(side="left", padx=(0, 12))

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left")
        ctk.CTkLabel(
            title_col, text=t("app_title"), text_color=theme.TEXT,
            font=(theme.FONT_BRAND, 24), anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_col, text=t("app_tagline"), text_color=theme.TEXT_MUTED,
            font=(theme.FONT_FAMILY, 11), anchor="w",
        ).pack(anchor="w", pady=(0, 0))

        chips = ctk.CTkFrame(header, fg_color="transparent")
        chips.pack(side="right")
        self.chip_lo = ctk.CTkButton(
            chips, text=t("engine_libreoffice_name"), image=icons.dot(theme.TEXT_MUTED), compound="left",
            width=112, height=30, corner_radius=8, font=(theme.FONT_FAMILY, 12),
            command=lambda: self._show_view("engines"), **_ghost(),
        )
        self.chip_lo.pack(side="right")
        self.chip_ffmpeg = ctk.CTkButton(
            chips, text=t("engine_ffmpeg_name"), image=icons.dot(theme.TEXT_MUTED), compound="left",
            width=92, height=30, corner_radius=8, font=(theme.FONT_FAMILY, 12),
            command=lambda: self._show_view("engines"), **_ghost(),
        )
        self.chip_ffmpeg.pack(side="right", padx=(0, 2))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 22))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.main_view = ctk.CTkFrame(body, fg_color="transparent")
        self.engines_view = ctk.CTkFrame(body, fg_color="transparent")
        self.main_view.grid(row=0, column=0, sticky="nsew")
        self.engines_view.grid(row=0, column=0, sticky="nsew")

        self._build_main(self.main_view)
        self._build_engines(self.engines_view)
        self._show_view("main")

    def _show_view(self, name: str) -> None:
        self._view = name
        (self.engines_view if name == "engines" else self.main_view).tkraise()

    # ------------------------------------------------------------- main view
    def _build_main(self, mv) -> None:
        mv.grid_columnconfigure(0, weight=1)
        mv.grid_rowconfigure(2, weight=1)

        toolbar = ctk.CTkFrame(mv, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew")
        self.add_files_btn = ctk.CTkButton(
            toolbar, text=t("btn_add_files"), command=self._add_files, width=124, height=38,
            corner_radius=10, font=(theme.FONT_STRONG, 13),
        )
        self.add_files_btn.pack(side="left", padx=(0, 8))
        self.add_folder_btn = ctk.CTkButton(
            toolbar, text=t("btn_add_folder"), command=self._add_folder, width=124, height=38,
            corner_radius=10, font=(theme.FONT_STRONG, 13), **_secondary(),
        )
        self.add_folder_btn.pack(side="left")
        self.clear_btn = ctk.CTkButton(
            toolbar, text=t("btn_clear_list"), command=self._clear_all, height=38, width=120,
            corner_radius=10, font=(theme.FONT_FAMILY, 12), **_ghost(),
        )

        # list-level information and the one list-level control
        self.list_header = ctk.CTkFrame(mv, fg_color="transparent")
        self.list_header.grid(row=1, column=0, sticky="ew", pady=(18, 8))
        self.summary_lbl = ctk.CTkLabel(
            self.list_header, text="", text_color=theme.TEXT_MUTED, anchor="w", font=(theme.FONT_FAMILY, 12),
        )
        self.summary_lbl.pack(side="left", padx=(2, 0))
        self.bulk_menu = ctk.CTkOptionMenu(
            self.list_header, values=["-"], width=128, height=30, corner_radius=8,
            fg_color=theme.INK_HOVER, button_color=theme.INK_HOVER, button_hover_color=theme.INK_LINE,
            text_color=theme.TEXT, dropdown_fg_color=theme.INK_RAISED, dropdown_hover_color=theme.INK_HOVER,
            dropdown_text_color=theme.TEXT, font=(theme.FONT_FAMILY, 12), dropdown_font=(theme.FONT_FAMILY, 12),
            command=self._apply_bulk,
        )
        self.bulk_menu.pack(side="right")
        ctk.CTkLabel(
            self.list_header, text=t("bulk_label"), text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 12),
        ).pack(side="right", padx=(0, 8))

        # The border is the drag-over affordance: invisible until a drag enters.
        self.drop_zone = ctk.CTkFrame(
            mv, fg_color="transparent", border_width=2, border_color=theme.INK, corner_radius=14,
        )
        self.drop_zone.grid(row=2, column=0, sticky="nsew")

        self.scroll = ctk.CTkScrollableFrame(
            self.drop_zone, fg_color="transparent", scrollbar_button_color=theme.INK_LINE,
            scrollbar_button_hover_color=theme.CHAMPAGNE_DIM,
        )
        self.scroll.pack(fill="both", expand=True, padx=2, pady=2)
        self.scroll.grid_columnconfigure(0, weight=1)

        self.empty_frame = self._build_empty_state(self.scroll)
        self.empty_frame.grid(row=0, column=0, pady=(48, 0))

        self.more_btn = ctk.CTkButton(
            self.scroll, text="", command=self._show_more, height=34, corner_radius=10, **_secondary(),
        )

        footer = ctk.CTkFrame(mv, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        footer.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            footer, text=t("save_folder_label"), text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 12),
        ).grid(row=0, column=0, sticky="w", padx=(2, 0))

        # label and "Change" sit together; the cell is what flexes, and the path truncates inside it
        self.out_dir_cell = ctk.CTkFrame(footer, fg_color="transparent", height=30)
        self.out_dir_cell.grid(row=0, column=1, sticky="ew", padx=(8, 12))
        self.out_dir_lbl = ctk.CTkLabel(
            self.out_dir_cell, text=str(self.out_dir), text_color=theme.TEXT, anchor="w", font=(theme.FONT_FAMILY, 12),
        )
        self.out_dir_lbl.pack(side="left")
        self.change_btn = ctk.CTkButton(
            self.out_dir_cell, text=t("change"), width=70, height=30, corner_radius=8, command=self._choose_out_dir,
            font=(theme.FONT_FAMILY, 12), **_ghost(),
        )
        self.change_btn.pack(side="left", padx=(6, 0))

        self.save_ready_btn = ctk.CTkButton(
            footer, text="", width=210, height=42, corner_radius=10, font=(theme.FONT_STRONG, 13),
            command=self._download_all, **_secondary(),
        )
        self.primary_btn = ctk.CTkButton(
            footer, text=t("convert"), width=190, height=42, corner_radius=10, font=(theme.FONT_STRONG, 14),
            command=self._start_conversion,
        )
        self.primary_btn.grid(row=0, column=3)

        self.out_dir_cell.bind("<Configure>", lambda _e: self._refit_out_dir())
        Tooltip(self.out_dir_lbl, lambda: str(self.out_dir))

    def _build_empty_state(self, parent) -> ctk.CTkFrame:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(box, text="", image=icons.drop_hero(72)).pack(pady=(0, 14))
        ctk.CTkLabel(
            box, text=t("empty_title"), text_color=theme.TEXT, font=(theme.FONT_STRONG, 17),
        ).pack()
        ctk.CTkLabel(
            box, text=t("empty_hint"), text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 12),
        ).pack(pady=(4, 14))
        ctk.CTkLabel(
            box, text=t("empty_formats"), text_color=theme.CHAMPAGNE_DIM, font=(theme.FONT_FAMILY, 11),
        ).pack()
        return box

    # ---------------------------------------------------------- engines view
    def _build_engines(self, ev) -> None:
        ev.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(ev, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            top, text=t("back"), image=icons.icon("chevron_left", theme.TEXT_MUTED, 16), compound="left",
            width=84, height=34, corner_radius=8, font=(theme.FONT_FAMILY, 13),
            command=lambda: self._show_view("main"), **_ghost(),
        ).pack(side="left")
        ctk.CTkLabel(
            top, text=t("engines_title"), text_color=theme.TEXT, font=(theme.FONT_STRONG, 18),
        ).pack(side="left", padx=(12, 0))

        panel = ctk.CTkFrame(ev, fg_color="transparent")
        panel.grid(row=1, column=0, sticky="new", pady=(22, 0))
        panel.grid_columnconfigure(0, weight=1)

        self.ffmpeg_status_lbl, self.ffmpeg_btn = self._build_engine_row(
            panel, 0, t("engine_ffmpeg_name"), t("engine_ffmpeg_desc"), self._install_ffmpeg)
        ctk.CTkFrame(panel, height=1, fg_color=theme.INK_LINE).grid(row=1, column=0, sticky="ew")
        self.docs_status_lbl, _ = self._build_engine_row(
            panel, 2, t("engine_docs_name"), t("engine_docs_desc"), None)
        ctk.CTkFrame(panel, height=1, fg_color=theme.INK_LINE).grid(row=3, column=0, sticky="ew")
        self.lo_status_lbl, self.lo_btn = self._build_engine_row(
            panel, 4, t("engine_libreoffice_name"), t("engine_libreoffice_desc"), self._install_libreoffice)

    def _build_engine_row(self, parent, grid_row: int, title: str, desc: str, command) -> tuple:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=grid_row, column=0, sticky="ew", pady=0)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            row, text=title, text_color=theme.TEXT, font=(theme.FONT_STRONG, 15), anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(20, 0), padx=(2, 0))
        status = ctk.CTkLabel(
            row, text="", compound="left", text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 12),
            anchor="w",
        )
        status.grid(row=1, column=0, sticky="w", pady=(4, 0), padx=(2, 0))
        ctk.CTkLabel(
            row, text=desc, text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 12), anchor="w",
            justify="left", wraplength=520,
        ).grid(row=2, column=0, sticky="w", pady=(8, 20), padx=(2, 0))
        btn = None
        if command is not None:  # the built-in engine has nothing to install
            btn = ctk.CTkButton(
                row, text="", width=150, height=36, corner_radius=10, font=(theme.FONT_STRONG, 13),
                command=command, **_secondary(),
            )
            btn.grid(row=0, column=1, rowspan=3, padx=(24, 2))
        return status, btn

    # ---------------------------------------------------------------- list
    def _add_paths(self, paths: list[str]) -> None:
        # A dropped/selected folder contributes its files (one level deep).
        candidates: list[Path] = []
        for p in paths:
            pp = Path(p)
            if pp.is_dir():
                try:
                    candidates.extend(sorted(x for x in pp.iterdir() if x.is_file()))
                except OSError:
                    pass
            else:
                candidates.append(pp)

        added = skipped = 0
        for path in candidates:
            key = str(path)
            targets = formats.targets_for(path.suffix.lower().lstrip(".")) if path.is_file() else []
            if not targets or key in self._paths:
                skipped += 1
                continue
            self.jobs.append(Job(src=path, target_ext=targets[0]))
            self._paths.add(key)
            added += 1

        self._note = t("skipped_files", count=skipped) if skipped else ""
        if added:
            self._show_view("main")
            self._materialize_next()
        self._refresh_ui_state()

    def _materialize_next(self) -> None:
        """Build a couple of rows, then yield to the event loop. Keeps the
        window responsive and gives the list a short cascade as it fills."""
        self._materialize_job = None
        made = 0
        target = min(len(self.jobs), self._visible_limit)
        while len(self.rows) < target and made < ROWS_PER_TICK:
            job = self.jobs[len(self.rows)]
            row = JobRow(self.scroll, job, self._remove_row, self._retarget, self._download_one)
            self.rows.append(row)
            self._row_by_job[id(job)] = row
            row.grid(row=len(self.rows) - 1, column=0, sticky="ew", pady=3, padx=2)
            made += 1
        self._sync_empty_state()
        self._place_more_button()
        if len(self.rows) < target:
            self._materialize_job = self.after(10, self._materialize_next)

    def _place_more_button(self) -> None:
        hidden = len(self.jobs) - len(self.rows)
        if hidden > 0 and len(self.rows) >= self._visible_limit:
            self.more_btn.configure(text=t("show_more", step=min(PAGE_SIZE, hidden), hidden=hidden))
            self.more_btn.grid(row=len(self.rows), column=0, sticky="ew", pady=(8, 4), padx=2)
        else:
            self.more_btn.grid_forget()

    def _show_more(self) -> None:
        self._visible_limit += PAGE_SIZE
        self._materialize_next()

    def _sync_empty_state(self) -> None:
        # an empty list has nothing to scroll, so its scrollbar shouldn't be drawn either
        track = theme.INK_LINE if self.jobs else theme.INK
        self.scroll._scrollbar.configure(button_color=track, button_hover_color=track if not self.jobs else theme.CHAMPAGNE_DIM)
        if self.jobs:
            self.empty_frame.grid_forget()
        else:
            self.empty_frame.grid(row=0, column=0, pady=(48, 0))
            # the list may have been scrolled down; without this the empty state sits above the viewport
            self.scroll._parent_canvas.yview_moveto(0)

    def _relayout_rows(self) -> None:
        for i, row in enumerate(self.rows):
            row.grid(row=i, column=0, sticky="ew", pady=3, padx=2)

    def _live_row(self, job: Job) -> JobRow | None:
        row = self._row_by_job.get(id(job))
        return row if row is not None and row.winfo_exists() else None

    def _remove_row(self, row: JobRow) -> None:
        job = row.job
        job.removed = True
        self._row_by_job.pop(id(job), None)
        self._paths.discard(str(job.src))
        row.destroy()
        self.rows.remove(row)
        self.jobs.remove(job)
        self._relayout_rows()
        self._materialize_next()  # a hidden job may now fit
        self._note = ""
        self._refresh_ui_state()

    def _clear_all(self) -> None:
        if self._materialize_job is not None:
            self.after_cancel(self._materialize_job)
            self._materialize_job = None
        for job in self.jobs:
            job.removed = True
        for row in self.rows:
            row.destroy()
        self.rows.clear()
        self.jobs.clear()
        self._row_by_job.clear()
        self._paths.clear()
        self._visible_limit = PAGE_SIZE
        self._note = ""
        self._place_more_button()
        self._sync_empty_state()
        self._refresh_ui_state()

    def _add_files(self) -> None:
        exts = " ".join(f"*.{e}" for e in formats.all_extensions())
        paths = filedialog.askopenfilenames(
            title=t("dialog_select_file"),
            filetypes=[(t("dialog_supported_files"), exts), (t("dialog_all_files"), "*.*")],
        )
        self._add_paths(list(paths))

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title=t("dialog_select_folder"))
        if folder:
            self._add_paths([folder])

    # --------------------------------------------------- target format changes
    def _retarget(self, job: Job, value: str, refresh: bool = True) -> None:
        """Set a job's target format. A finished or failed job's output is for
        the old format, so it goes back to waiting instead of being saved stale."""
        job.target_ext = value
        if job.status in (STATUS_DONE, STATUS_ERROR):
            job.status, job.error, job.dst = STATUS_PENDING, None, None
        row = self._live_row(job)
        if row:
            row.target_menu.set(value)
            row.set_status(job.status, job.error)
        if refresh:
            self._refresh_footer()

    def _refresh_bulk_values(self) -> None:
        seen: list[str] = []
        for ext in dict.fromkeys(j.src_ext for j in self.jobs):
            for target in formats.targets_for(ext):
                if target not in seen:
                    seen.append(target)
        self.bulk_menu.configure(values=seen or ["-"])
        self.bulk_menu.set(t("bulk_placeholder"))

    def _apply_bulk(self, value: str) -> None:
        applied = 0
        for job in self.jobs:
            if value in formats.targets_for(job.src_ext):
                if job.target_ext != value or job.status in (STATUS_DONE, STATUS_ERROR):
                    self._retarget(job, value, refresh=False)
                applied += 1
        self._note = t("bulk_applied", applied=applied, total=len(self.jobs), fmt=value)
        self.bulk_menu.set(t("bulk_placeholder"))
        self._refresh_ui_state()

    # ------------------------------------------------------------ drag & drop
    def _set_drop_highlight(self, on: bool) -> None:
        self.drop_zone.configure(border_color=theme.CHAMPAGNE if on else theme.INK)

    def _on_drop_enter(self, event):
        self._set_drop_highlight(True)
        return event.action

    def _on_drop_leave(self, event):
        self._set_drop_highlight(False)
        return event.action

    def _on_drop(self, event):
        self._set_drop_highlight(False)
        self._add_paths(list(self.tk.splitlist(event.data)))
        return event.action

    # ---------------------------------------------------------- output folder
    def _refit_out_dir(self) -> None:
        w = self.out_dir_cell.winfo_width()
        if w == self._out_dir_w:
            return
        self._out_dir_w = w
        room = w - self.change_btn.winfo_reqwidth() - 14  # keep "Change" visible next to the path
        self.out_dir_lbl.configure(text=fit_text(self.out_dir_lbl, str(self.out_dir), room, head_ratio=0.3))

    def _set_out_dir(self, folder: Path) -> None:
        self.out_dir = folder
        self._out_dir_w = -1
        self._refit_out_dir()

    def _choose_out_dir(self) -> None:
        folder = filedialog.askdirectory(title=t("dialog_select_default_folder"), initialdir=str(self.out_dir))
        if folder:
            self._set_out_dir(Path(folder))

    def _reveal_in_explorer(self, path: Path) -> None:
        try:
            if path.is_file():
                subprocess.Popen(["explorer", "/select,", str(path)])
            else:
                subprocess.Popen(["explorer", str(path)])
        except OSError:
            pass

    def _download_one(self, job) -> None:
        if job.status != STATUS_DONE or not job.dst or not job.dst.exists():
            return
        path = filedialog.asksaveasfilename(
            title=t("dialog_save_as"),
            initialdir=str(self.out_dir),
            initialfile=job.dst.name,
            defaultextension=f".{job.target_ext}",
        )
        if not path:
            return
        dest = Path(path)
        shutil.copy2(job.dst, dest)
        self._set_out_dir(dest.parent)
        self._reveal_in_explorer(dest)

    def _download_all(self) -> None:
        completed = [j for j in self.jobs if j.status == STATUS_DONE and j.dst and j.dst.exists()]
        if not completed:
            messagebox.showinfo(t("app_title"), t("no_files_to_download"))
            return

        folder = filedialog.askdirectory(title=t("dialog_select_download_folder"), initialdir=str(self.out_dir))
        if not folder:
            return

        dest_dir = Path(folder)
        for job in completed:
            shutil.copy2(job.dst, _unique_dest(dest_dir, job.dst.name))

        self._set_out_dir(dest_dir)
        self._reveal_in_explorer(dest_dir)

    # ------------------------------------------------------- state -> widgets
    def _refresh_ui_state(self) -> None:
        has = bool(self.jobs)
        self.add_files_btn.configure(**(_secondary() if has else _primary()))
        if has:
            self.clear_btn.pack(side="right")
            self.list_header.grid()
        else:
            self.clear_btn.pack_forget()
            self.list_header.grid_remove()
        text = tn("file_count", len(self.jobs))
        if self._note:
            text += f"  ·  {self._note}"
        self.summary_lbl.configure(text=text)
        self._refresh_bulk_values()
        self._refresh_footer()

    def _refresh_footer(self) -> None:
        """One primary action at a time: convert -> (progress) -> save."""
        runnable = [j for j in self.jobs if j.status in (STATUS_PENDING, STATUS_ERROR)]
        done = [j for j in self.jobs if j.status == STATUS_DONE and j.dst and j.dst.exists()]
        show_secondary = False

        if self._converting:
            live = [j for j in self._run_jobs if not j.removed]
            finished = sum(1 for j in live if j.status in (STATUS_DONE, STATUS_ERROR))
            self.primary_btn.configure(
                state="disabled", text=t("converting_progress", done=finished, total=len(live)), **_disabled_primary())
        elif not self.jobs:
            self.primary_btn.configure(state="disabled", text=t("convert"), **_disabled_primary())
        elif runnable:
            self.primary_btn.configure(
                state="normal", text=t("convert_n", count=len(runnable)), command=self._start_conversion, **_primary())
            show_secondary = bool(done)
        else:
            self.primary_btn.configure(
                state="normal", text=t("save_all", count=len(done)), command=self._download_all, **_primary())

        if show_secondary:
            self.save_ready_btn.configure(text=t("save_ready", count=len(done)))
            self.save_ready_btn.grid(row=0, column=2, padx=(0, 10))
        else:
            self.save_ready_btn.grid_forget()

    # ---------------------------------------------------------- conversion
    def _start_conversion(self) -> None:
        if self._converting:
            return
        runnable = [j for j in self.jobs if j.status in (STATUS_PENDING, STATUS_ERROR)]
        if not runnable:
            return

        for job in runnable:
            job.status, job.error = STATUS_PENDING, None
            row = self._live_row(job)
            if row:
                row.set_status(STATUS_PENDING, None)

        self._run_jobs = runnable
        self._converting = True
        self._note = ""
        self._refresh_ui_state()

        stage_dir = staging_dir()

        def worker():
            done, failed = 0, 0
            seen: dict[str, int] = {}  # two "a.png" from different folders must not share one output file
            for job in runnable:
                if job.removed:
                    continue
                self._ui_queue.put(("status", job, STATUS_CONVERTING, None))
                try:
                    dst = job.output_path(stage_dir)
                    key = dst.name.lower()
                    n = seen.get(key, 0)
                    seen[key] = n + 1
                    if n:
                        dst = dst.with_stem(f"{dst.stem} ({n + 1})")
                    if dst.exists():
                        dst.unlink()

                    def progress_cb(fraction: float, _job=job) -> None:
                        self._ui_queue.put(("progress", _job, fraction))

                    convert_file(job.src, dst, progress_cb=progress_cb)
                    job.dst = dst
                    self._ui_queue.put(("status", job, STATUS_DONE, None))
                    done += 1
                except Exception as exc:  # noqa: BLE001
                    self._ui_queue.put(("status", job, STATUS_ERROR, str(exc)))
                    failed += 1
            self._ui_queue.put(("finished", None, done, failed))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_ui_queue(self) -> None:
        # try/finally: one bad message must never stop the poll loop, or every
        # status/progress update for the rest of the session is lost.
        latest_progress: dict[int, tuple[Job, float]] = {}
        try:
            while True:
                try:
                    item = self._ui_queue.get_nowait()
                except queue.Empty:
                    break
                if item[0] == "progress":
                    # a long video emits thousands of updates; only the newest per job is worth drawing
                    latest_progress[id(item[1])] = (item[1], item[2])
                    continue
                try:
                    self._handle_ui_item(item)
                except tk.TclError:
                    pass  # the row was removed while a message for it was in flight
            for job, fraction in latest_progress.values():
                row = self._live_row(job)
                if row:
                    try:
                        row.set_progress(fraction)
                    except tk.TclError:
                        pass
        finally:
            self.after(120, self._poll_ui_queue)

    def _handle_ui_item(self, item) -> None:
        kind = item[0]
        if kind == "status":
            _, job, status, error = item
            job.status, job.error = status, error  # the model is the source of truth, even with no row on screen
            row = self._live_row(job)
            if row:
                row.set_status(status, error)
            self._refresh_footer()
        elif kind == "finished":
            _, _, done, failed = item
            self._converting = False
            self._note = t("summary_result", done=done, failed=failed)
            self._refresh_ui_state()
        elif kind == "engine_status":
            self._refresh_engine_status()
        elif kind == "text_status":
            _, target, text = item
            (self.ffmpeg_status_lbl if target == "ffmpeg" else self.lo_status_lbl).configure(text=text)
        elif kind == "error_popup":
            _, title, text = item
            messagebox.showerror(title, text)

    # ------------------------------------------------------------- engines
    def _set_engine_ui(self, ready: bool, status_lbl, action_btn, chip, ready_text: str, idle_text: str,
                       missing_label: str, missing_colour: str) -> None:
        colour = theme.EMERALD_TEXT if ready else missing_colour
        status_lbl.configure(
            text="  " + (t("engine_ready") if ready else missing_label),
            text_color=colour, image=icons.dot(colour),
        )
        chip.configure(image=icons.dot(colour))
        action_btn.configure(text=ready_text if ready else idle_text)

    def _refresh_engine_status(self) -> None:
        # FFmpeg is needed for any video/audio job, so absence is a warning.
        self._set_engine_ui(
            ffmpeg_manager.is_ready(), self.ffmpeg_status_lbl, self.ffmpeg_btn, self.chip_ffmpeg,
            t("engine_recheck"), t("engine_download"), t("engine_not_ready"), theme.WARNING)
        # LibreOffice is optional: not having it is a normal state, not a problem to flag.
        self._set_engine_ui(
            libreoffice_manager.is_ready(), self.lo_status_lbl, self.lo_btn, self.chip_lo,
            t("engine_recheck"), t("engine_install"), t("engine_optional_missing"), theme.TEXT_MUTED)
        has_browser = docs.find_browser() is not None
        colour = theme.EMERALD_TEXT if has_browser else theme.WARNING
        self.docs_status_lbl.configure(
            text="  " + t("engine_docs_status" if has_browser else "engine_docs_status_nobrowser"),
            text_color=colour, image=icons.dot(colour))

    def _install_ffmpeg(self) -> None:
        self.ffmpeg_btn.configure(state="disabled")

        def status_cb(text: str) -> None:
            self._ui_queue.put(("text_status", "ffmpeg", text))

        def worker():
            try:
                ffmpeg_manager.ensure_ffmpeg(status_cb)
            except Exception as exc:  # noqa: BLE001
                status_cb(f"{t('ffmpeg_download_failed_title')}: {exc}")
                self._ui_queue.put(("error_popup", t("ffmpeg_download_failed_title"), str(exc)))
            self._ui_queue.put(("engine_status",))
            self.ffmpeg_btn.configure(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    def _install_libreoffice(self) -> None:
        if libreoffice_manager.is_ready():
            self._refresh_engine_status()
            messagebox.showinfo(t("app_title"), t("libreoffice_already_ready"))
            return

        libreoffice_manager.open_download_page()
        self.lo_btn.configure(text=t("engine_recheck"))
        messagebox.showinfo(t("libreoffice_setup_title"), t("libreoffice_setup_body"))


def run() -> None:
    app = App()
    app.mainloop()
