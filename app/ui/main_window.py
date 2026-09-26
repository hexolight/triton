from __future__ import annotations

import queue
import shutil
import subprocess
import threading
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
from app.i18n import t

ctk.set_appearance_mode("dark")

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

        self.grid_columnconfigure(0, weight=1)

        name_lbl = ctk.CTkLabel(
            self, text=job.src.name, anchor="w",
            text_color=theme.TEXT, font=(theme.FONT_FAMILY, 13, "bold"),
        )
        name_lbl.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=(10, 0))

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

        path_lbl = ctk.CTkLabel(
            self, text=str(job.src.parent), anchor="w",
            text_color=theme.TEXT_MUTED, font=(theme.FONT_FAMILY, 10),
        )
        path_lbl.grid(row=1, column=0, columnspan=6, sticky="ew", padx=(14, 10), pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            self, height=6, progress_color=theme.ACCENT, fg_color=theme.BG_PANEL,
        )
        self.progress_bar.set(0)

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

        self.rows: list[JobRow] = []
        self.out_dir = default_output_dir()
        self._ui_queue: queue.Queue = queue.Queue()
        self._converting = False

        self._set_window_icon()
        self._build_layout()
        self._poll_ui_queue()

        if DND_AVAILABLE:
            self.drop_target_register(DND_FILES)
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

        self.scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=12, pady=6)
        self.scroll.grid_columnconfigure(0, weight=1)

        self.empty_lbl = ctk.CTkLabel(
            self.scroll, text=t("empty_list"), text_color=theme.TEXT_MUTED,
        )
        self.empty_lbl.grid(row=0, column=0, pady=40)

        bottom = ctk.CTkFrame(tab, fg_color="transparent")
        bottom.pack(fill="x", padx=12, pady=(6, 14))

        ctk.CTkLabel(bottom, text=t("default_download_folder"), text_color=theme.TEXT_MUTED).pack(side="left")
        self.out_dir_lbl = ctk.CTkLabel(
            bottom, text=str(self.out_dir), text_color=theme.TEXT,
            font=(theme.FONT_FAMILY, 11),
        )
        self.out_dir_lbl.pack(side="left", padx=(6, 10))
        ctk.CTkButton(
            bottom, text=t("browse"), width=70, command=self._choose_out_dir,
            fg_color=theme.BG_ROW, hover_color=theme.BG_ROW_HOVER,
        ).pack(side="left")

        self.convert_btn = ctk.CTkButton(
            bottom, text=t("convert"), command=self._start_conversion,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, width=140, height=36,
            font=(theme.FONT_FAMILY, 14, "bold"),
        )
        self.convert_btn.pack(side="right")

        self.download_all_btn = ctk.CTkButton(
            bottom, text=t("download_all"), command=self._download_all,
            fg_color=theme.BG_ROW, hover_color=theme.BG_ROW_HOVER, width=130, height=36,
        )
        self.download_all_btn.pack(side="right", padx=(0, 10))

        self.summary_lbl = ctk.CTkLabel(bottom, text="", text_color=theme.TEXT_MUTED)
        self.summary_lbl.pack(side="right", padx=12)

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

    # --------------------------------------------------------------- files
    def _add_paths(self, paths: list[str]) -> None:
        added = False
        for p in paths:
            path = Path(p)
            if not path.is_file():
                continue
            ext = path.suffix.lower().lstrip(".")
            targets = formats.targets_for(ext)
            if not targets:
                continue
            job = Job(src=path, target_ext=targets[0])
            row = JobRow(self.scroll, job, self._remove_row, self._update_summary, self._download_one)
            self.rows.append(row)
            added = True

        if added:
            self.empty_lbl.grid_forget()
            self._relayout_rows()
            self._update_summary()

    def _relayout_rows(self) -> None:
        for i, row in enumerate(self.rows):
            row.grid(row=i, column=0, sticky="ew", pady=4, padx=2)

    def _remove_row(self, row: JobRow) -> None:
        row.destroy()
        self.rows.remove(row)
        if not self.rows:
            self.empty_lbl.grid(row=0, column=0, pady=40)
        self._relayout_rows()
        self._update_summary()

    def _clear_all(self) -> None:
        for row in self.rows:
            row.destroy()
        self.rows.clear()
        self.empty_lbl.grid(row=0, column=0, pady=40)
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
        if not folder:
            return
        exts = set(formats.all_extensions())
        found = [str(p) for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower().lstrip(".") in exts]
        self._add_paths(found)

    def _on_drop(self, event) -> None:
        raw = self.tk.splitlist(event.data)
        self._add_paths(list(raw))

    def _choose_out_dir(self) -> None:
        folder = filedialog.askdirectory(title=t("dialog_select_default_folder"), initialdir=str(self.out_dir))
        if folder:
            self.out_dir = Path(folder)
            self.out_dir_lbl.configure(text=str(self.out_dir))

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
        self.out_dir = dest.parent
        self.out_dir_lbl.configure(text=str(self.out_dir))
        self._reveal_in_explorer(dest)

    def _download_all(self) -> None:
        completed = [row.job for row in self.rows if row.job.status == STATUS_DONE and row.job.dst and row.job.dst.exists()]
        if not completed:
            messagebox.showinfo(t("app_title"), t("no_files_to_download"))
            return

        folder = filedialog.askdirectory(title=t("dialog_select_download_folder"), initialdir=str(self.out_dir))
        if not folder:
            return

        dest_dir = Path(folder)
        for job in completed:
            shutil.copy2(job.dst, dest_dir / job.dst.name)

        self.out_dir = dest_dir
        self.out_dir_lbl.configure(text=str(self.out_dir))
        self._reveal_in_explorer(dest_dir)

    def _update_summary(self) -> None:
        self.summary_lbl.configure(text=t("file_count", count=len(self.rows)))

    # ---------------------------------------------------------- conversion
    def _start_conversion(self) -> None:
        if self._converting:
            return
        if not self.rows:
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

        jobs = [row.job for row in self.rows]
        rows_by_job = {id(row.job): row for row in self.rows}
        stage_dir = staging_dir()

        def worker():
            done, failed = 0, 0
            for job in jobs:
                self._ui_queue.put(("status", id(job), STATUS_CONVERTING, None))
                try:
                    dst = job.output_path(stage_dir)
                    if dst.exists():
                        dst.unlink()

                    def progress_cb(fraction: float, _job=job) -> None:
                        self._ui_queue.put(("progress", id(_job), fraction))

                    convert_file(job.src, dst, progress_cb=progress_cb)
                    job.dst = dst
                    self._ui_queue.put(("status", id(job), STATUS_DONE, None))
                    done += 1
                except Exception as exc:  # noqa: BLE001
                    self._ui_queue.put(("status", id(job), STATUS_ERROR, str(exc)))
                    failed += 1
            self._ui_queue.put(("finished", None, done, failed))

        self._rows_by_job = rows_by_job
        threading.Thread(target=worker, daemon=True).start()

    def _missing_engines(self) -> list[str]:
        need_ffmpeg = any(row.job.target_ext in formats.VIDEO_EXTS + formats.AUDIO_EXTS for row in self.rows)
        need_office = any(
            formats.category_of(row.job.target_ext) == formats.Category.DOCUMENT and row.job.target_ext != "pdf"
            or (formats.category_of(row.job.src_ext) == formats.Category.DOCUMENT and row.job.src_ext not in ("pdf", "jpg", "jpeg", "png"))
            for row in self.rows
        )
        missing = []
        if need_ffmpeg and not ffmpeg_manager.is_ready():
            missing.append("FFmpeg")
        if need_office and not libreoffice_manager.is_ready():
            missing.append("LibreOffice")
        return missing

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                item = self._ui_queue.get_nowait()
                kind = item[0]
                if kind == "status":
                    _, job_id, status, error = item
                    row = self._rows_by_job.get(job_id)
                    if row:
                        row.set_status(status, error)
                elif kind == "progress":
                    _, job_id, fraction = item
                    row = self._rows_by_job.get(job_id)
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
        except queue.Empty:
            pass
        self.after(120, self._poll_ui_queue)

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
