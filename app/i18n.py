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

    # toolbar and list
    "btn_add_files": "Dosya ekle",
    "btn_add_folder": "Klasör ekle",
    "btn_clear_list": "Listeyi temizle",
    "empty_title": "Dosyaları buraya bırak",
    "empty_hint": "ya da yukarıdan dosya veya klasör ekle",
    "empty_formats": "MP4 · MP3 · WAV · JPG · PNG · PDF · DOCX · PPTX · XLSX …",
    "file_count_one": "{count} dosya",
    "file_count_other": "{count} dosya",
    "skipped_files": "{count} atlandı (desteklenmiyor ya da zaten ekli)",
    "bulk_label": "Hepsini şuna çevir",
    "bulk_placeholder": "biçim seç",
    "bulk_applied": "{applied}/{total} dosya {fmt} olarak ayarlandı",
    "show_more": "{step} dosya daha göster ({hidden} gizli)",
    "tooltip_remove": "Listeden kaldır",

    # row status
    "status_pending": "Bekliyor",
    "status_converting": "Dönüştürülüyor…",
    "status_save": "Kaydet",
    "status_error": "Hata",
    "conversion_error_title": "Dönüştürme hatası — {name}",

    # footer
    "save_folder_label": "Kaydetme klasörü",
    "change": "Değiştir",
    "convert": "Dönüştür",
    "convert_n": "Dönüştür ({count})",
    "converting_progress": "Dönüştürülüyor {done}/{total}",
    "save_all": "Hepsini kaydet ({count})",
    "save_ready": "Hazır olanları kaydet ({count})",
    "summary_result": "{done} tamamlandı, {failed} hata",
    "output_folder_name": "Triton Çıktıları",

    # engines
    "engines_title": "Dönüştürme motorları",
    "back": "Geri",
    "engine_ffmpeg_name": "FFmpeg",
    "engine_ffmpeg_desc": "Video ve ses dönüşümleri için. Yalnızca uygulamanın "
        "kendi klasörüne indirilir, sisteme kurulmaz.",
    "engine_docs_name": "Belge motoru",
    "engine_docs_desc": "Word, Excel, PowerPoint, ODT ve metin dosyalarını PDF'e "
        "çevirir; PDF'i Edge veya Chrome ile basar. Metin, tablo ve görseller "
        "korunur; sayfa düzeni, üst/alt bilgi ve özel yazı tipleri birebir korunmaz.",
    "engine_docs_status": "Dahili, kurulum gerekmez",
    "engine_docs_status_nobrowser": "Edge veya Chrome bulunamadı, yalnızca metin tabanlı belgeler",
    "engine_libreoffice_name": "LibreOffice",
    "engine_libreoffice_desc": "İsteğe bağlı. Eski .doc, .ppt, .rtf, .odp, .ods "
        "biçimleri ve Office biçimleri arası dönüşümler için; sayfa düzenini "
        "en sadık koruyan motor. Yaklaşık 700 MB yer kaplar.",
    "engine_ready": "Hazır",
    "engine_not_ready": "Kurulu değil",
    "engine_optional_missing": "Kurulu değil · isteğe bağlı",
    "engine_recheck": "Yeniden kontrol et",
    "engine_download": "İndir",
    "engine_install": "Kur",
    "ffmpeg_download_failed_title": "FFmpeg indirilemedi",
    "ffmpeg_downloading": "FFmpeg indiriliyor…",
    "ffmpeg_downloading_pct": "FFmpeg indiriliyor… %{pct}",
    "ffmpeg_extracting": "FFmpeg çıkarılıyor…",
    "ffmpeg_ready_status": "FFmpeg hazır.",
    "libreoffice_already_ready": "LibreOffice zaten hazır.",
    "libreoffice_setup_title": "LibreOffice kurulumu",
    "libreoffice_setup_body": "LibreOffice'in resmi indirme sayfası tarayıcıda "
        "açıldı.\n\nİndirdiğiniz .msi dosyasını çalıştırıp kurulumu tamamlayın, "
        "sonra bu ekrandaki 'Yeniden kontrol et' düğmesine basın.",

    # dialogs
    "dialog_select_file": "Dosya seç",
    "dialog_supported_files": "Desteklenen dosyalar",
    "dialog_all_files": "Tüm dosyalar",
    "dialog_select_folder": "Klasör seç",
    "dialog_select_default_folder": "Kaydetme klasörünü seç",
    "dialog_save_as": "Farklı kaydet",
    "dialog_select_download_folder": "Kaydedilecek klasörü seç",
    "no_files_to_download": "Kaydedilecek tamamlanmış dosya yok.",

    # errors raised by converters (shown in the row's error dialog)
    "err_ffmpeg_missing": "FFmpeg kurulu değil. Sağ üstteki FFmpeg göstergesine "
        "tıklayıp indirin.",
    "err_ffmpeg_failed": "FFmpeg hatası:\n{detail}",
    "err_ffmpeg_windows_only": "FFmpeg otomatik indirme yalnızca Windows için "
        "yapılandırıldı. Lütfen ffmpeg'i kendiniz kurup PATH'e ekleyin.",
    "err_ffmpeg_bad_package": "İndirilen FFmpeg paketinde çalıştırılabilir dosya bulunamadı.",
    "err_unsupported_image_format": "Desteklenmeyen görsel biçimi: {ext}",
    "err_unsupported_pdf_conversion": "Desteklenmeyen PDF dönüşümü: {src} -> {dst}",
    "err_libreoffice_missing": "Bu dönüşüm için isteğe bağlı LibreOffice gerekiyor "
        "(≈700 MB). Sağ üstteki LibreOffice göstergesinden kurabilirsiniz.",
    "err_no_browser": "PDF oluşturmak için Microsoft Edge veya Google Chrome gerekiyor.",
    "err_pdf_print": "PDF oluşturulamadı: tarayıcı çıktı üretmedi.",
    "err_doc_read": "Dosya işlenemedi: {detail}",
    "docs_rows_hidden": "… ve {count} satır daha (PDF'te gösterilmiyor)",
    "err_libreoffice_failed": "LibreOffice hatası:\n{detail}",
    "err_libreoffice_no_output": "LibreOffice çıktı dosyası oluşturmadı.",
    "err_unsupported_conversion": "{src} -> {dst} dönüşümü desteklenmiyor.",
}

_EN: dict[str, str] = {
    "app_title": "Triton",
    "app_tagline": "local file converter",

    # toolbar and list
    "btn_add_files": "Add files",
    "btn_add_folder": "Add folder",
    "btn_clear_list": "Clear list",
    "empty_title": "Drop files here",
    "empty_hint": "or add files or a folder above",
    "empty_formats": "MP4 · MP3 · WAV · JPG · PNG · PDF · DOCX · PPTX · XLSX …",
    "file_count_one": "{count} file",
    "file_count_other": "{count} files",
    "skipped_files": "{count} skipped (unsupported or already added)",
    "bulk_label": "Convert all to",
    "bulk_placeholder": "choose format",
    "bulk_applied": "{applied} of {total} set to {fmt}",
    "show_more": "Show {step} more ({hidden} hidden)",
    "tooltip_remove": "Remove from list",

    # row status
    "status_pending": "Waiting",
    "status_converting": "Converting…",
    "status_save": "Save",
    "status_error": "Failed",
    "conversion_error_title": "Conversion failed — {name}",

    # footer
    "save_folder_label": "Save to",
    "change": "Change",
    "convert": "Convert",
    "convert_n": "Convert ({count})",
    "converting_progress": "Converting {done}/{total}",
    "save_all": "Save all ({count})",
    "save_ready": "Save finished ({count})",
    "summary_result": "{done} done, {failed} failed",
    "output_folder_name": "Triton Output",

    # engines
    "engines_title": "Conversion engines",
    "back": "Back",
    "engine_ffmpeg_name": "FFmpeg",
    "engine_ffmpeg_desc": "For video and audio conversions. Downloaded into the "
        "app's own folder only, never installed system-wide.",
    "engine_docs_name": "Document engine",
    "engine_docs_desc": "Converts Word, Excel, PowerPoint, ODT and text files to "
        "PDF, printing through Edge or Chrome. Text, tables and images are kept; "
        "page layout, headers/footers and custom fonts are not reproduced exactly.",
    "engine_docs_status": "Built in, nothing to install",
    "engine_docs_status_nobrowser": "Edge or Chrome not found, text-based documents only",
    "engine_libreoffice_name": "LibreOffice",
    "engine_libreoffice_desc": "Optional. For old .doc, .ppt, .rtf, .odp, .ods files "
        "and conversions between Office formats; the engine that keeps page "
        "layout most faithfully. Takes about 700 MB.",
    "engine_ready": "Ready",
    "engine_not_ready": "Not installed",
    "engine_optional_missing": "Not installed · optional",
    "engine_recheck": "Check again",
    "engine_download": "Download",
    "engine_install": "Install",
    "ffmpeg_download_failed_title": "FFmpeg download failed",
    "ffmpeg_downloading": "Downloading FFmpeg…",
    "ffmpeg_downloading_pct": "Downloading FFmpeg… {pct}%",
    "ffmpeg_extracting": "Extracting FFmpeg…",
    "ffmpeg_ready_status": "FFmpeg ready.",
    "libreoffice_already_ready": "LibreOffice is already ready.",
    "libreoffice_setup_title": "LibreOffice setup",
    "libreoffice_setup_body": "LibreOffice's official download page opened in "
        "your browser.\n\nRun the downloaded .msi to finish the install, then "
        "press 'Check again' on this screen.",

    # dialogs
    "dialog_select_file": "Select files",
    "dialog_supported_files": "Supported files",
    "dialog_all_files": "All files",
    "dialog_select_folder": "Select folder",
    "dialog_select_default_folder": "Choose where to save",
    "dialog_save_as": "Save as",
    "dialog_select_download_folder": "Choose a folder to save into",
    "no_files_to_download": "No finished files to save.",

    # errors raised by converters (shown in the row's error dialog)
    "err_ffmpeg_missing": "FFmpeg isn't installed. Click FFmpeg at the top right "
        "to download it.",
    "err_ffmpeg_failed": "FFmpeg error:\n{detail}",
    "err_ffmpeg_windows_only": "Automatic FFmpeg download is only set up for "
        "Windows. Please install ffmpeg yourself and add it to PATH.",
    "err_ffmpeg_bad_package": "No executables found inside the downloaded FFmpeg package.",
    "err_unsupported_image_format": "Unsupported image format: {ext}",
    "err_unsupported_pdf_conversion": "Unsupported PDF conversion: {src} -> {dst}",
    "err_libreoffice_missing": "This conversion needs the optional LibreOffice "
        "(≈700 MB). You can install it from the LibreOffice indicator at the top right.",
    "err_no_browser": "Microsoft Edge or Google Chrome is required to create PDFs.",
    "err_pdf_print": "Couldn't create the PDF: the browser produced no output.",
    "err_doc_read": "Couldn't process the file: {detail}",
    "docs_rows_hidden": "… and {count} more rows (not shown in the PDF)",
    "err_libreoffice_failed": "LibreOffice error:\n{detail}",
    "err_libreoffice_no_output": "LibreOffice did not produce an output file.",
    "err_unsupported_conversion": "{src} -> {dst} conversion is not supported.",
}

_STRINGS = {"tr": _TR, "en": _EN}


def t(key: str, **kwargs) -> str:
    s = _STRINGS[LANG].get(key) or _TR.get(key, key)
    return s.format(**kwargs) if kwargs else s


def tn(key: str, count: int, **kwargs) -> str:
    """Plural-aware lookup: uses `<key>_one` for exactly 1, else `<key>_other`."""
    return t(f"{key}_{'one' if count == 1 else 'other'}", count=count, **kwargs)
