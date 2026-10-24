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
from app.utils.paths import default_output_dir, staging_dir, assets_dir
from app.ui import theme
from app.ui.textfit import fit_text
from app.ui.tooltip import Tooltip
from app.i18n import t, tn

ctk.set_appearance_mode("dark")

# Each row is ~7 canvas-backed widgets and costs 30-50 ms to first paint, and
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


class JobRow(ctk.CTkFrame):
    def __init__(self, master, job: Job, on_remove, on_target_change, on_download):
        super().__init__(master, fg_color=theme.BG_ROW, corner_radius=10)
        self.job = job
        self._on_remove = on_remove
        self._on_target_change = on_target_change
        self._on_download = on_download

        self._full_name = job.src.name
        self._full_path = str(job.src.parent)
        self._name_shown = self._full_name
        self._path_shown = self._full_path
        self._name_w = self._path_w = -1

        self.grid_columnconfigure(0, weight=1)

        self.name_lbl = ctk.CTkLabel(
            self, text=self._full_name, anchor="w",
            text_color=theme.TEXT, font=(theme.FONT_FAMILY, 13, "bold"),
        )
        self.name_lbl.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=(10, 0))

        badge = ctk.CTkLabel(
            self, text=job.src_ext.upper(), text_color=theme.ACCENT,
            fg_color=theme.ACCENT_SOFT, corner_radius=6, width=54,
            font=(theme.FONT_FAMILY, 11, "bold"),
        )
        badge.grid(row=0, column=1, padx=(0, 6), pady=(10, 0))

        arrow = ctk.CTkLabel(self, text="→", text_color=theme.TEXT_MUTED)
        arrow.grid(row=0, column=2, padx=4, pady=(10, 0))

        targets = formats.targets_for(job.src_ext)
        self.target_menu = ctk.CTkOptionMenu(
            self, values=targets or ["-"], width=100,
            fg_color=theme.BG_PANEL, button_color=theme.ACCENT,
            button_hover_color=theme.ACCENT_HOVER,
            command=self._target_changed,
        )
        if job.target_ext in targets:
            self.target_menu.set(job.target_ext)
        self.target_menu.grid(row=0, column=3, padx=(0, 10), pady=(10, 0))

        self.status_lbl = ctk.CTkLabel(
            self, text=t("status_label_pending"), width=110,
            text_color=theme.STATUS_COLORS.get(job.status, theme.TEXT_MUTED),
            font=(theme.FONT_FAMILY, 12),
        )
        self.status_lbl.grid(row=0, column=4, padx=(0, 10), pady=(10, 0))
        self.status_lbl.bind("<Button-1>", lambda _e: self._on_status_click())

        remove_btn = ctk.CTkButton(
            self, text="✕", width=28, height=28, fg_color="transparent",
            hover_color="#3a1f22", text_color=theme.TEXT_MUTED,
            command=lambda: self._on_remove(self),
        )
        remove_btn.grid(row=0, column=5, padx=(0, 10), pady=(10, 0))

        self.path_lbl = ctk.CTkLabel(
            self, text=self._full_path, anchor="w",
            text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 10),
        )
        self.path_lbl.grid(row=1, column=0, columnspan=6, sticky="ew", padx=(14, 10), pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            self, height=6, progress_color=theme.ACCENT, fg_color=theme.BG_PANEL,
        )
        self.progress_bar.set(0)

        self.name_lbl.bind("<Configure>", lambda _e: self._refit_name())
        self.path_lbl.bind("<Configure>", lambda _e: self._refit_path())
        Tooltip(self.name_lbl, lambda: self._full_name if self._name_shown != self._full_name else "")
        Tooltip(self.path_lbl, lambda: self._full_path if self._path_shown != self._full_path else "")
        Tooltip(remove_btn, lambda: t("tooltip_remove"))

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

    def _refit_path(self) -> None:
        w = self.path_lbl.winfo_width()
        if w == self._path_w:
            return
        self._path_w = w
        shown = fit_text(self.path_lbl, self._full_path, w - 8, head_ratio=0.3)
        if shown != self._path_shown:
            self._path_shown = shown
            self.path_lbl.configure(text=shown)

    def _target_changed(self, value: str) -> None:
        self.job.target_ext = value
        self._on_target_change()

    def set_status(self, status: str, error: str | None = None) -> None:
        self.job.status = status
        self.job.error = error
        if status == STATUS_ERROR:
            label = t("status_error_action")
        elif status == STATUS_DONE:
            label = t("status_done_action")
        else:
            label = t(f"status_label_{status}")
        cursor = "hand2" if status in (STATUS_ERROR, STATUS_DONE) else ""
        self.status_lbl.configure(
            text=label, text_color=theme.STATUS_COLORS.get(status, theme.TEXT_MUTED), cursor=cursor,
        )

        if status == STATUS_CONVERTING:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.grid(row=2, column=0, columnspan=6, sticky="ew", padx=14, pady=(0, 10))
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            self.progress_bar.grid_forget()

    def set_progress(self, fraction: float) -> None:
        if self.job.status != STATUS_CONVERTING:
            return
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(max(0.0, min(1.0, fraction)))

    def _on_status_click(self) -> None:
        if self.job.status == STATUS_ERROR:
            self._show_error()
        elif self.job.status == STATUS_DONE:
            self._on_download(self.job)

    def _show_error(self) -> None:
        if self.job.error:
            messagebox.showerror(t("conversion_error_title", name=self.job.src.name), self.job.error)


class App(_BaseWindow):
    def __init__(self):
        super().__init__()
        self.title(t("app_title"))
        self.geometry("980x680")
        self.minsize(820, 560)
        self.configure(fg_color=theme.BG)

        self.jobs: list[Job] = []                  # every file the user added
        self.rows: list[JobRow] = []               # widgets for jobs[:len(rows)]
        self._row_by_job: dict[int, JobRow] = {}
        self._paths: set[str] = set()
        self._visible_limit = PAGE_SIZE
        self._materialize_job = None
        self._skipped_note = ""

        self.out_dir = default_output_dir()
        self._ui_queue: queue.Queue = queue.Queue()
        self._converting = False

        self._set_window_icon()
        self._build_layout()
        self._poll_ui_queue()

        if DND_AVAILABLE:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<DropEnter>>", self._on_drop_enter)
            self.dnd_bind("<<DropLeave>>", self._on_drop_leave)
            self.dnd_bind("<<Drop>>", self._on_drop)

    # ------------------------------------------------------------------ UI
    def _set_window_icon(self) -> None:
        ico_path = assets_dir() / "app.ico"
        if ico_path.exists():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:  # noqa: BLE001 - icon is cosmetic, never fatal
                pass

    def _build_layout(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(22, 10))

        logo_path = assets_dir() / "logo.png"
        if logo_path.exists():
            logo_img = ctk.CTkImage(light_image=Image.open(logo_path), size=(46, 46))
            ctk.CTkLabel(header, image=logo_img, text="").pack(side="left", padx=(0, 12))

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left")

        ctk.CTkLabel(
            title_col, text=t("app_title"), text_color=theme.TEXT,
            font=(theme.FONT_FAMILY, 25, "bold"), anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_col, text=t("app_tagline"), text_color=theme.ACCENT,
            font=(theme.FONT_FAMILY, 12, "bold"), anchor="w",
        ).pack(anchor="w")

        divider = ctk.CTkFrame(self, fg_color=theme.ACCENT_SOFT, height=2, corner_radius=0)
        divider.pack(fill="x", padx=24, pady=(0, 4))

        self.tabview = ctk.CTkTabview(
            self, fg_color=theme.BG_PANEL, segmented_button_fg_color=theme.BG_PANEL,
            segmented_button_selected_color=theme.ACCENT,
            segmented_button_selected_hover_color=theme.ACCENT_HOVER,
            corner_radius=14,
        )
        self.tabview.pack(fill="both", expand=True, padx=24, pady=(12, 20))
        self.tab_convert = self.tabview.add(t("tab_convert"))
        self.tab_settings = self.tabview.add(t("tab_settings"))

        self._build_convert_tab(self.tab_convert)
        self._build_settings_tab(self.tab_settings)

    def _build_convert_tab(self, tab) -> None:
        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.pack(fill="x", padx=12, pady=(14, 6))

        ctk.CTkButton(
            toolbar, text=t("btn_add_files"), command=self._add_files,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, width=120,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            toolbar, text=t("btn_add_folder"), command=self._add_folder,
            fg_color=theme.BG_ROW, hover_color=theme.BG_ROW_HOVER, width=120,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            toolbar, text=t("btn_clear_list"), command=self._clear_all,
            fg_color=theme.BG_ROW, hover_color=theme.BG_ROW_HOVER, width=120,
        ).pack(side="left")

        self.drop_hint = ctk.CTkLabel(
            toolbar,
            text=t("drop_hint") if DND_AVAILABLE else "",
            text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 11, "italic"),
        )
        self.drop_hint.pack(side="right")

        # The border is the drag-over affordance: transparent until a drag enters.
        self.drop_zone = ctk.CTkFrame(
            tab, fg_color="transparent", border_width=2, border_color=theme.BG_PANEL, corner_radius=12,
        )
        self.drop_zone.pack(fill="both", expand=True, padx=12, pady=6)

        self.scroll = ctk.CTkScrollableFrame(self.drop_zone, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=2, pady=2)
        self.scroll.grid_columnconfigure(0, weight=1)

        self.empty_frame = self._build_empty_state(self.scroll)
        self.empty_frame.grid(row=0, column=0, pady=30)

        self.more_btn = ctk.CTkButton(
            self.scroll, text="", command=self._show_more,
            fg_color=theme.BG_ROW, hover_color=theme.BG_ROW_HOVER, height=34,
        )

        # status line (own row, so it can never be squeezed by the controls)
        self.summary_lbl = ctk.CTkLabel(tab, text="", text_color=theme.TEXT_MUTED, anchor="w")
        self.summary_lbl.pack(fill="x", padx=16, pady=(2, 0))

        bottom = ctk.CTkFrame(tab, fg_color="transparent")
        bottom.pack(fill="x", padx=12, pady=(4, 14))
        bottom.grid_columnconfigure(1, weight=1)  # the folder path flexes; the buttons never shrink

        ctk.CTkLabel(bottom, text=t("default_download_folder"), text_color=theme.TEXT_MUTED).grid(
            row=0, column=0, sticky="w")
        self.out_dir_lbl = ctk.CTkLabel(
            bottom, text=str(self.out_dir), text_color=theme.TEXT, anchor="w",
            font=(theme.FONT_FAMILY, 11),
        )
        self.out_dir_lbl.grid(row=0, column=1, sticky="ew", padx=(6, 8))
        ctk.CTkButton(
            bottom, text=t("browse"), width=70, command=self._choose_out_dir,
            fg_color=theme.BG_ROW, hover_color=theme.BG_ROW_HOVER,
        ).grid(row=0, column=2, padx=(0, 18))

        self.download_all_btn = ctk.CTkButton(
            bottom, text=t("download_all"), command=self._download_all,
            fg_color=theme.BG_ROW, hover_color=theme.BG_ROW_HOVER, width=130, height=36,
        )
        self.download_all_btn.grid(row=0, column=3, padx=(0, 10))

        self.convert_btn = ctk.CTkButton(
            bottom, text=t("convert"), command=self._start_conversion,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, width=140, height=36,
            font=(theme.FONT_FAMILY, 14, "bold"),
        )
        self.convert_btn.grid(row=0, column=4)

        self._out_dir_w = -1
        self.out_dir_lbl.bind("<Configure>", lambda _e: self._refit_out_dir())
        Tooltip(self.out_dir_lbl, lambda: str(self.out_dir))

        self._update_summary()

    def _build_empty_state(self, parent) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=theme.BG_ROW, corner_radius=16)
        ctk.CTkLabel(
            card, text="⬇", text_color=theme.ACCENT, font=(theme.FONT_FAMILY, 34),
        ).pack(padx=70, pady=(26, 4))
        ctk.CTkLabel(
            card, text=t("empty_title"), text_color=theme.TEXT, font=(theme.FONT_FAMILY, 16, "bold"),
        ).pack()
        ctk.CTkLabel(
            card, text=t("empty_hint"), text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 12),
        ).pack(pady=(2, 10))
        ctk.CTkLabel(
            card, text=t("empty_formats"), text_color=theme.ACCENT, fg_color=theme.ACCENT_SOFT,
            corner_radius=8, font=(theme.FONT_FAMILY, 11, "bold"), padx=12, pady=3,
        ).pack(pady=(0, 26))
        return card

    def _build_engine_card(self, parent, title: str, subtitle: str, button_command) -> tuple:
        card = ctk.CTkFrame(parent, fg_color=theme.BG_ROW, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)

        dot = ctk.CTkLabel(
            card, text="●", text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 14), width=20,
        )
        dot.grid(row=0, column=0, rowspan=2, sticky="w", padx=(16, 0), pady=14)

        text_col = ctk.CTkFrame(card, fg_color="transparent")
        text_col.grid(row=0, column=0, sticky="w", padx=(40, 10), pady=(14, 0))
        ctk.CTkLabel(
            text_col, text=title, text_color=theme.TEXT,
            font=(theme.FONT_FAMILY, 14, "bold"), anchor="w",
        ).pack(anchor="w")

        status_lbl = ctk.CTkLabel(
            card, text="", text_color=theme.TEXT_MUTED, anchor="w", font=(theme.FONT_FAMILY, 11),
        )
        status_lbl.grid(row=1, column=0, sticky="w", padx=(40, 10), pady=(0, 14))

        ctk.CTkLabel(
            card, text=subtitle, text_color=theme.TEXT_MUTED, anchor="w",
            font=(theme.FONT_FAMILY, 11), justify="left", wraplength=460,
        ).grid(row=2, column=0, sticky="w", padx=(40, 10), pady=(0, 14))

        btn = ctk.CTkButton(
            card, text="", width=130, height=34, command=button_command,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, corner_radius=8,
        )
        btn.grid(row=0, column=1, rowspan=3, padx=16, pady=14, sticky="e")

        return dot, status_lbl, btn

    def _build_settings_tab(self, tab) -> None:
        wrap = ctk.CTkFrame(tab, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            wrap, text=t("engines_title"), text_color=theme.TEXT,
            font=(theme.FONT_FAMILY, 17, "bold"), anchor="w",
        ).pack(anchor="w", pady=(0, 14))

        self.ffmpeg_dot, self.ffmpeg_status_lbl, self.ffmpeg_btn = self._build_engine_card(
            wrap, t("engine_ffmpeg_name"), t("engine_ffmpeg_desc"), self._install_ffmpeg,
        )
        self.lo_dot, self.lo_status_lbl, self.lo_btn = self._build_engine_card(
            wrap, t("engine_libreoffice_name"), t("engine_libreoffice_desc"), self._install_libreoffice,
        )

        self._refresh_engine_status()

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

        self._skipped_note = t("skipped_files", count=skipped) if skipped else ""
        if added:
            self._materialize_next()
        self._sync_empty_state()
        self._update_summary()

    def _materialize_next(self) -> None:
        """Build a couple of rows, then yield to the event loop. Keeps the
        window responsive and gives the list a short cascade as it fills."""
        self._materialize_job = None
        made = 0
        target = min(len(self.jobs), self._visible_limit)
        while len(self.rows) < target and made < ROWS_PER_TICK:
            job = self.jobs[len(self.rows)]
            row = JobRow(self.scroll, job, self._remove_row, self._update_summary, self._download_one)
            self.rows.append(row)
            self._row_by_job[id(job)] = row
            row.grid(row=len(self.rows) - 1, column=0, sticky="ew", pady=4, padx=2)
            made += 1
        self._sync_empty_state()
        self._place_more_button()
        if len(self.rows) < target:
            self._materialize_job = self.after(10, self._materialize_next)

    def _place_more_button(self) -> None:
        hidden = len(self.jobs) - len(self.rows)
        if hidden > 0 and len(self.rows) >= self._visible_limit:
            self.more_btn.configure(text=t("show_more", step=min(PAGE_SIZE, hidden), hidden=hidden))
            self.more_btn.grid(row=len(self.rows), column=0, sticky="ew", pady=(6, 4), padx=2)
        else:
            self.more_btn.grid_forget()

    def _show_more(self) -> None:
        self._visible_limit += PAGE_SIZE
        self._materialize_next()

    def _sync_empty_state(self) -> None:
        if self.jobs:
            self.empty_frame.grid_forget()
        else:
            self.empty_frame.grid(row=0, column=0, pady=30)
            # the list may have been scrolled down; without this the card sits above the viewport
            self.scroll._parent_canvas.yview_moveto(0)

    def _relayout_rows(self) -> None:
        for i, row in enumerate(self.rows):
            row.grid(row=i, column=0, sticky="ew", pady=4, padx=2)

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
        self._update_summary()

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
        self._skipped_note = ""
        self._place_more_button()
        self._sync_empty_state()
        self._update_summary()

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

    # ------------------------------------------------------------ drag & drop
    def _set_drop_highlight(self, on: bool) -> None:
        self.drop_zone.configure(border_color=theme.ACCENT if on else theme.BG_PANEL)

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
        w = self.out_dir_lbl.winfo_width()
        if w == self._out_dir_w:
            return
        self._out_dir_w = w
        self.out_dir_lbl.configure(text=fit_text(self.out_dir_lbl, str(self.out_dir), w - 8, head_ratio=0.3))

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
            shutil.copy2(job.dst, dest_dir / job.dst.name)

        self._set_out_dir(dest_dir)
        self._reveal_in_explorer(dest_dir)

    def _update_summary(self) -> None:
        text = tn("file_count", len(self.jobs))
        if self._skipped_note:
            text += f"  ·  {self._skipped_note}"
        self.summary_lbl.configure(text=text)

    # ---------------------------------------------------------- conversion
    def _start_conversion(self) -> None:
        if self._converting:
            return
        if not self.jobs:
            messagebox.showinfo(t("app_title"), t("add_files_first"))
            return

        missing = self._missing_engines()
        if missing:
            messagebox.showwarning(
                t("missing_engine_title"),
                t("missing_engine_body", engines=", ".join(missing)),
            )

        self._converting = True
        self.convert_btn.configure(state="disabled", text=t("converting_btn"))

        jobs = list(self.jobs)
        stage_dir = staging_dir()

        def worker():
            done, failed = 0, 0
            seen: dict[str, int] = {}  # two "a.png" from different folders must not share one output file
            for job in jobs:
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

    def _missing_engines(self) -> list[str]:
        need_ffmpeg = any(j.target_ext in formats.VIDEO_EXTS + formats.AUDIO_EXTS for j in self.jobs)
        need_office = any(
            formats.category_of(j.target_ext) == formats.Category.DOCUMENT and j.target_ext != "pdf"
            or (formats.category_of(j.src_ext) == formats.Category.DOCUMENT and j.src_ext not in ("pdf", "jpg", "jpeg", "png"))
            for j in self.jobs
        )
        missing = []
        if need_ffmpeg and not ffmpeg_manager.is_ready():
            missing.append("FFmpeg")
        if need_office and not libreoffice_manager.is_ready():
            missing.append("LibreOffice")
        return missing

    def _live_row(self, job: Job) -> JobRow | None:
        row = self._row_by_job.get(id(job))
        return row if row is not None and row.winfo_exists() else None

    def _poll_ui_queue(self) -> None:
        # try/finally: one bad message must never stop the poll loop, or every
        # status/progress update for the rest of the session is lost.
        try:
            while True:
                try:
                    item = self._ui_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    self._handle_ui_item(item)
                except tk.TclError:
                    pass  # the row was removed while a message for it was in flight
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
        elif kind == "progress":
            _, job, fraction = item
            row = self._live_row(job)
            if row:
                row.set_progress(fraction)
        elif kind == "finished":
            _, _, done, failed = item
            self._converting = False
            self.convert_btn.configure(state="normal", text=t("convert"))
            self.summary_lbl.configure(text=t("summary_result", done=done, failed=failed))
        elif kind == "engine_status":
            self._refresh_engine_status()
        elif kind == "text_status":
            _, target, text = item
            if target == "ffmpeg":
                self.ffmpeg_status_lbl.configure(text=text)
            else:
                self.lo_status_lbl.configure(text=text)
        elif kind == "error_popup":
            _, title, text = item
            messagebox.showerror(title, text)

    # ------------------------------------------------------------- engines
    def _refresh_engine_status(self) -> None:
        if ffmpeg_manager.is_ready():
            self.ffmpeg_status_lbl.configure(text=t("engine_ready"), text_color=theme.SUCCESS)
            self.ffmpeg_dot.configure(text_color=theme.SUCCESS)
            self.ffmpeg_btn.configure(text=t("engine_recheck"))
        else:
            self.ffmpeg_status_lbl.configure(text=t("engine_not_ready"), text_color=theme.TEXT_MUTED)
            self.ffmpeg_dot.configure(text_color=theme.TEXT_MUTED)
            self.ffmpeg_btn.configure(text=t("engine_download"))

        if libreoffice_manager.is_ready():
            self.lo_status_lbl.configure(text=t("engine_ready"), text_color=theme.SUCCESS)
            self.lo_dot.configure(text_color=theme.SUCCESS)
            self.lo_btn.configure(text=t("engine_recheck"))
        else:
            self.lo_status_lbl.configure(text=t("engine_not_ready"), text_color=theme.TEXT_MUTED)
            self.lo_dot.configure(text_color=theme.TEXT_MUTED)
            self.lo_btn.configure(text=t("engine_install"))

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
