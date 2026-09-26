"""Tiny i18n layer. All user-facing text goes through t(key, **kwargs).

Language resolution order:
1. TRITON_LANG environment variable (handy for `TRITON_LANG=en python main.py`)
2. app._lang_default.DEFAULT_LANG, written by build.py before each PyInstaller
   build so the TR and EN .exe each default to their own language without
   needing an env var set on the end user's machine.
3. "tr"
"""

from __future__ import annotations
import os

try:
    from app._lang_default import DEFAULT_LANG
except ImportError:
    DEFAULT_LANG = "tr"

LANG = os.environ.get("TRITON_LANG", DEFAULT_LANG).strip().lower()
if LANG not in ("tr", "en"):
    LANG = "tr"

_TR: dict[str, str] = {
    "app_title": "Triton",
    "app_tagline": "yerel dosya dönüştürücü",
    "tab_convert": "Dönüştür",
    "tab_settings": "Ayarlar",
    "btn_add_files": "+ Dosya Ekle",
    "btn_add_folder": "+ Klasör Ekle",
    "btn_clear_list": "Listeyi Temizle",
    "drop_hint": "dosyaları buraya sürükleyip bırakabilirsin",
    "empty_list": "Henüz dosya eklenmedi.",
    "default_download_folder": "Varsayılan indirme klasörü:",
    "browse": "Gözat",
    "convert": "Dönüştür",
    "converting_btn": "Dönüştürülüyor...",
    "download_all": "Tümünü İndir",
    "status_label_pending": "Bekliyor",
    "status_label_converting": "Dönüştürülüyor...",
    "status_done_action": "İndir  ⬇",
    "status_error_action": "Hata  (i)",
    "conversion_error_title": "Dönüştürme hatası — {name}",
    "engines_title": "Dönüştürme motorları",
    "engine_ffmpeg_name": "FFmpeg",
    "engine_ffmpeg_desc": "Video ve ses dönüşümleri için. Yalnızca uygulama "
        "klasörüne indirilir, sisteme kurulmaz.",
    "engine_libreoffice_name": "LibreOffice",
    "engine_libreoffice_desc": "Word / Excel / PowerPoint dönüşümleri için. "
        "PDF ↔ görsel ve PDF → Word bunsuz da çalışır — yalnızca ofis "
        "belgelerini PDF'e çevirmek için gerekir.",
    "engine_ready": "Hazır",
    "engine_not_ready": "Kurulu değil",
    "engine_recheck": "Yeniden Kontrol Et",
    "engine_download": "İndir",
    "engine_install": "Kur",
    "dialog_select_file": "Dosya seç",
    "dialog_supported_files": "Desteklenen dosyalar",
    "dialog_all_files": "Tüm dosyalar",
    "dialog_select_folder": "Klasör seç",
    "dialog_select_default_folder": "Varsayılan indirme klasörü seç",
    "dialog_save_as": "Farklı kaydet",
    "dialog_select_download_folder": "İndirme klasörü seç",
    "no_files_to_download": "İndirilecek tamamlanmış dosya yok.",
    "add_files_first": "Önce dönüştürülecek dosya ekleyin.",
    "missing_engine_title": "Eksik bileşen",
    "missing_engine_body": "Şu motorlar hazır değil: {engines}\nAyarlar "
        "sekmesinden kurabilirsiniz. Bu motoru gerektirmeyen dosyalar yine "
        "de dönüştürülecek.",
    "summary_result": "{done} tamamlandı, {failed} hata",
    "file_count": "{count} dosya",
    "output_folder_name": "Triton Çıktıları",
    "ffmpeg_download_failed_title": "FFmpeg indirilemedi",
    "libreoffice_already_ready": "LibreOffice zaten hazır.",
    "libreoffice_setup_title": "LibreOffice kurulumu",
    "libreoffice_setup_body": "Tarayıcınızda LibreOffice'in resmi indirme "
        "sayfası açıldı.\n\nİndirdiğiniz .msi dosyasını çalıştırıp kurulumu "
        "tamamlayın, ardından bu sekmedeki 'Yeniden Kontrol Et' butonuna "
        "tekrar basın.",
    "ffmpeg_downloading": "FFmpeg indiriliyor...",
    "ffmpeg_downloading_pct": "FFmpeg indiriliyor... %{pct}",
    "ffmpeg_extracting": "FFmpeg çıkarılıyor...",
    "ffmpeg_ready_status": "FFmpeg hazır.",
    "err_ffmpeg_missing": "FFmpeg bulunamadı. Önce Ayarlar sekmesinden indirin.",
    "err_ffmpeg_failed": "FFmpeg hatası:\n{detail}",
    "err_ffmpeg_windows_only": "FFmpeg otomatik indirme yalnızca Windows "
        "için yapılandırıldı. Lütfen ffmpeg'i sisteminize kurup PATH'e "
        "ekleyin.",
    "err_ffmpeg_bad_package": "İndirilen FFmpeg paketi içinde çalıştırılabilir "
        "dosyalar bulunamadı.",
    "err_unsupported_image_format": "Desteklenmeyen görsel formatı: {ext}",
    "err_unsupported_pdf_conversion": "Desteklenmeyen PDF dönüşümü: {src} -> {dst}",
    "err_libreoffice_missing": "LibreOffice bulunamadı. Önce Ayarlar sekmesinden kurun.",
    "err_libreoffice_failed": "LibreOffice hatası:\n{detail}",
    "err_libreoffice_no_output": "LibreOffice çıktı dosyası oluşturmadı.",
    "err_unsupported_conversion": "{src} -> {dst} dönüşümü desteklenmiyor.",
}

_EN: dict[str, str] = {
    "app_title": "Triton",
    "app_tagline": "local file converter",
    "tab_convert": "Convert",
    "tab_settings": "Settings",
    "btn_add_files": "+ Add Files",
    "btn_add_folder": "+ Add Folder",
    "btn_clear_list": "Clear List",
    "drop_hint": "you can drag and drop files here",
    "empty_list": "No files added yet.",
    "default_download_folder": "Default download folder:",
    "browse": "Browse",
    "convert": "Convert",
    "converting_btn": "Converting...",
    "download_all": "Download All",
    "status_label_pending": "Pending",
    "status_label_converting": "Converting...",
    "status_done_action": "Download  ⬇",
    "status_error_action": "Error  (i)",
    "conversion_error_title": "Conversion error — {name}",
    "engines_title": "Conversion engines",
    "engine_ffmpeg_name": "FFmpeg",
    "engine_ffmpeg_desc": "For video and audio conversions. Downloaded only "
        "into the app's own folder, never installed system-wide.",
    "engine_libreoffice_name": "LibreOffice",
    "engine_libreoffice_desc": "For Word / Excel / PowerPoint conversions. "
        "PDF ↔ image and PDF → Word work without it — it's only needed to "
        "convert office documents to PDF.",
    "engine_ready": "Ready",
    "engine_not_ready": "Not installed",
    "engine_recheck": "Check Again",
    "engine_download": "Download",
    "engine_install": "Install",
    "dialog_select_file": "Select file",
    "dialog_supported_files": "Supported files",
    "dialog_all_files": "All files",
    "dialog_select_folder": "Select folder",
    "dialog_select_default_folder": "Select default download folder",
    "dialog_save_as": "Save as",
    "dialog_select_download_folder": "Select download folder",
    "no_files_to_download": "No completed files to download.",
    "add_files_first": "Add files to convert first.",
    "missing_engine_title": "Missing component",
    "missing_engine_body": "These engines aren't ready: {engines}\nYou can "
        "install them from the Settings tab. Files that don't need them "
        "will still be converted.",
    "summary_result": "{done} done, {failed} failed",
    "file_count": "{count} file(s)",
    "output_folder_name": "Triton Output",
    "ffmpeg_download_failed_title": "FFmpeg download failed",
    "libreoffice_already_ready": "LibreOffice is already ready.",
    "libreoffice_setup_title": "LibreOffice setup",
    "libreoffice_setup_body": "LibreOffice's official download page opened "
        "in your browser.\n\nRun the downloaded .msi file to finish the "
        "install, then click 'Check Again' on this tab.",
    "ffmpeg_downloading": "Downloading FFmpeg...",
    "ffmpeg_downloading_pct": "Downloading FFmpeg... {pct}%",
    "ffmpeg_extracting": "Extracting FFmpeg...",
    "ffmpeg_ready_status": "FFmpeg ready.",
    "err_ffmpeg_missing": "FFmpeg not found. Download it from the Settings tab first.",
    "err_ffmpeg_failed": "FFmpeg error:\n{detail}",
    "err_ffmpeg_windows_only": "Automatic FFmpeg download is only set up "
        "for Windows. Please install ffmpeg yourself and add it to PATH.",
    "err_ffmpeg_bad_package": "No executables found inside the downloaded FFmpeg package.",
    "err_unsupported_image_format": "Unsupported image format: {ext}",
    "err_unsupported_pdf_conversion": "Unsupported PDF conversion: {src} -> {dst}",
    "err_libreoffice_missing": "LibreOffice not found. Install it from the Settings tab first.",
    "err_libreoffice_failed": "LibreOffice error:\n{detail}",
    "err_libreoffice_no_output": "LibreOffice did not produce an output file.",
    "err_unsupported_conversion": "{src} -> {dst} conversion is not supported.",
}

_STRINGS = {"tr": _TR, "en": _EN}


def t(key: str, **kwargs) -> str:
    s = _STRINGS[LANG].get(key) or _TR.get(key, key)
    return s.format(**kwargs) if kwargs else s
