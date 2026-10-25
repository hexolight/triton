// TR / EN strings. Same keys and voice as the desktop app's app/i18n.py where the feature is the same.

const TR = {
  page_title: "Triton · dosya dönüştürücü",
  page_description:
    "Video, ses, görsel, PDF ve belgeleri tarayıcıda dönüştürün. Dosyalarınız cihazınızdan çıkmaz.",
  app_title: "Triton",
  app_tagline: "dosyalar cihazından çıkmaz",
  lang_label: "Dil",

  btn_add_files: "Dosya ekle",
  btn_add_folder: "Klasör ekle",
  btn_clear_list: "Listeyi temizle",
  empty_title: "Dosyaları buraya bırak",
  empty_hint: "ya da yukarıdan dosya veya klasör ekle",
  empty_formats: "MP4 · MP3 · WAV · JPG · PNG · PDF · DOCX · XLSX …",
  file_count_one: "{count} dosya",
  file_count_other: "{count} dosya",
  skipped_files: "{count} atlandı (desteklenmiyor ya da zaten ekli)",
  bulk_label: "Hepsini şuna çevir",
  bulk_placeholder: "biçim seç",
  bulk_applied: "{applied}/{total} dosya {fmt} olarak ayarlandı",
  tooltip_remove: "Listeden kaldır",
  target_label: "Hedef biçim: {name}",

  status_pending: "Bekliyor",
  status_converting: "Dönüştürülüyor…",
  status_save: "Kaydet",
  status_error: "Hata",
  conversion_error_title: "Dönüştürme hatası — {name}",
  close: "Kapat",

  save_note: "Dosyalar tarayıcınızın indirme klasörüne kaydedilir. Hiçbir şey bir sunucuya yüklenmez.",
  convert: "Dönüştür",
  convert_n: "Dönüştür ({count})",
  converting_progress: "Dönüştürülüyor {done}/{total}",
  save_all: "Hepsini kaydet ({count})",
  save_ready: "Hazır olanları kaydet ({count})",
  summary_result: "{done} tamamlandı, {failed} hata",
  zip_name: "triton-ciktilar.zip",

  engines_title: "Dönüştürme motorları",
  back: "Geri",
  chip_docs: "Belgeler",
  engine_ffmpeg_name: "FFmpeg",
  engine_ffmpeg_desc:
    "Video ve ses dönüşümleri için. Tarayıcıda çalışır; ilk kullanımda yaklaşık 30 MB indirilir. Büyük videolar masaüstü sürümünden daha yavaştır.",
  engine_state_idle: "Henüz yüklenmedi, ilk video/ses dönüşümünde otomatik yüklenir",
  engine_state_loading: "Yükleniyor…",
  engine_state_ready: "Hazır",
  engine_state_error: "Yüklenemedi",
  engine_load: "Şimdi yükle",
  engine_retry: "Tekrar dene",
  engine_docs_name: "Belge motoru",
  engine_docs_desc:
    "Word, Excel, ODT, CSV ve metin dosyalarını PDF'e çevirir; PDF'i Word'e (yalnızca metin) çevirir. Metin, tablo ve görseller korunur; sayfa düzeni, üst/alt bilgi ve özel yazı tipleri birebir korunmaz.",
  engine_docs_status: "Dahili, kurulum gerekmez",
  engine_desktop_name: "Masaüstü sürümü",
  engine_desktop_desc:
    "PowerPoint, eski .doc/.ppt/.rtf biçimleri, çok büyük dosyalar ve toplu işler için Windows sürümünü indirin. Her şey bilgisayarınızda çalışır.",
  engine_desktop_btn: "Windows sürümünü indir",

  err_ffmpeg_load: "FFmpeg yüklenemedi. Bağlantınızı kontrol edip tekrar deneyin.",
  err_too_big: "Bu dosya tarayıcı için çok büyük ({size}). Masaüstü sürümünü kullanın.",
  err_image: "Görsel okunamadı. Dosya bozuk ya da bu tarayıcı biçimi desteklemiyor.",
  err_pdf: "PDF okunamadı: {detail}",
  err_doc: "Dosya işlenemedi: {detail}",
  err_convert: "Dönüştürülemedi: {detail}",
  err_unsupported: "{src} -> {dst} dönüşümü desteklenmiyor.",
  docs_rows_hidden: "… ve {count} satır daha (PDF'te gösterilmiyor)",
  js_required: "Triton çalışmak için JavaScript gerektirir.",
};

const EN = {
  page_title: "Triton · file converter",
  page_description:
    "Convert video, audio, images, PDFs and documents in your browser. Your files never leave your device.",
  app_title: "Triton",
  app_tagline: "your files never leave your device",
  lang_label: "Language",

  btn_add_files: "Add files",
  btn_add_folder: "Add folder",
  btn_clear_list: "Clear list",
  empty_title: "Drop files here",
  empty_hint: "or add files or a folder above",
  empty_formats: "MP4 · MP3 · WAV · JPG · PNG · PDF · DOCX · XLSX …",
  file_count_one: "{count} file",
  file_count_other: "{count} files",
  skipped_files: "{count} skipped (unsupported or already added)",
  bulk_label: "Convert all to",
  bulk_placeholder: "choose format",
  bulk_applied: "{applied} of {total} set to {fmt}",
  tooltip_remove: "Remove from list",
  target_label: "Target format: {name}",

  status_pending: "Waiting",
  status_converting: "Converting…",
  status_save: "Save",
  status_error: "Failed",
  conversion_error_title: "Conversion failed — {name}",
  close: "Close",

  save_note: "Files are saved to your browser's downloads folder. Nothing is uploaded to a server.",
  convert: "Convert",
  convert_n: "Convert ({count})",
  converting_progress: "Converting {done}/{total}",
  save_all: "Save all ({count})",
  save_ready: "Save finished ({count})",
  summary_result: "{done} done, {failed} failed",
  zip_name: "triton-output.zip",

  engines_title: "Conversion engines",
  back: "Back",
  chip_docs: "Documents",
  engine_ffmpeg_name: "FFmpeg",
  engine_ffmpeg_desc:
    "For video and audio conversions. Runs in your browser; about 30 MB is downloaded on first use. Large videos are slower than in the desktop app.",
  engine_state_idle: "Not loaded yet, loads automatically on the first video/audio conversion",
  engine_state_loading: "Loading…",
  engine_state_ready: "Ready",
  engine_state_error: "Couldn't load",
  engine_load: "Load now",
  engine_retry: "Try again",
  engine_docs_name: "Document engine",
  engine_docs_desc:
    "Converts Word, Excel, ODT, CSV and text files to PDF, and PDF to Word (text only). Text, tables and images are kept; page layout, headers/footers and custom fonts are not reproduced exactly.",
  engine_docs_status: "Built in, nothing to install",
  engine_desktop_name: "Desktop app",
  engine_desktop_desc:
    "For PowerPoint, old .doc/.ppt/.rtf files, very large files and batch jobs, download the Windows app. Everything runs on your computer.",
  engine_desktop_btn: "Download for Windows",

  err_ffmpeg_load: "FFmpeg couldn't load. Check your connection and try again.",
  err_too_big: "This file is too large for the browser ({size}). Use the desktop app.",
  err_image: "Couldn't read the image. The file is damaged or this browser doesn't support the format.",
  err_pdf: "Couldn't read the PDF: {detail}",
  err_doc: "Couldn't process the file: {detail}",
  err_convert: "Conversion failed: {detail}",
  err_unsupported: "{src} -> {dst} conversion is not supported.",
  docs_rows_hidden: "… and {count} more rows (not shown in the PDF)",
  js_required: "Triton needs JavaScript to run.",
};

const STRINGS = { tr: TR, en: EN };
const listeners = new Set();
let lang = "en";

export function detectLang() {
  try {
    const saved = localStorage.getItem("triton-lang");
    if (saved === "tr" || saved === "en") return saved;
  } catch {
    /* storage can be blocked; fall through */
  }
  return (navigator.language || "en").toLowerCase().startsWith("tr") ? "tr" : "en";
}

export function getLang() {
  return lang;
}

export function setLang(next, { persist = true } = {}) {
  if (next !== "tr" && next !== "en") return;
  lang = next;
  document.documentElement.lang = next;
  document.title = t("page_title");
  document.querySelector('meta[name="description"]')?.setAttribute("content", t("page_description"));
  if (persist) {
    try {
      localStorage.setItem("triton-lang", next);
    } catch {
      /* ignore */
    }
  }
  listeners.forEach((fn) => fn(next));
}

export function onLangChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function t(key, vars) {
  let s = STRINGS[lang][key] ?? TR[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v));
  return s;
}

export function tn(key, count, vars = {}) {
  return t(`${key}_${count === 1 ? "one" : "other"}`, { count, ...vars });
}
