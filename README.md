# Triton

*[Türkçe](#türkçe) | [English](#english)*

---

## Türkçe

Bilgisayarda yerel çalışan, çok formatlu dosya dönüştürücü. İnternete dosya
göndermez — tüm dönüşümler kendi makinenizde yapılır.

### Desteklenen formatlar

- **Video:** mp4, mkv, avi, mov, webm, flv, wmv, m4v, mpg, ts, 3gp (+ videodan ses çıkarma)
- **Ses:** mp3, wav, flac, aac, ogg, m4a, wma, opus, aiff
- **Görsel:** jpg, png, webp, bmp, gif, tiff, ico (+ görsel → PDF)
- **Belge:** pdf, docx, doc, odt, rtf, txt, pptx, ppt, odp, xlsx, xls, ods, csv, pdf → docx/görsel

### Çalıştırma

```
run.bat
```

İlk çalıştırmada sanal ortam kurulur ve bağımlılıklar otomatik indirilir.

### Dönüştürme motorları

- **Video/ses (FFmpeg):** Uygulama içindeki *Ayarlar* sekmesinden "İndir" ile
  otomatik iner; sisteme kurulmaz, yalnızca uygulamanın kendi klasörüne iner.
- **Ofis belgeleri (LibreOffice):** Word/Excel/PowerPoint dönüşümleri gerçek
  bir LibreOffice kurulumu gerektirir. *Ayarlar* sekmesindeki "Kur" butonu
  resmi indirme sayfasını tarayıcıda açar; .msi dosyasını siz indirip
  çalıştırırsınız.
- **PDF ↔ görsel, PDF → docx:** Ek kurulum gerekmez (Pillow, PyMuPDF, pdf2docx
  ile Python içinde çalışır).

### Geliştirme

```
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

### Diller

Arayüz Türkçe ve İngilizce olarak mevcut (`app/i18n.py`). Geliştirirken
`TRITON_LANG=en` ortam değişkeniyle geçici olarak değiştirilebilir.

### .exe derleme

```
.venv\Scripts\pip install pyinstaller
.venv\Scripts\python build.py            # Türkçe: dist\Triton.exe
.venv\Scripts\python build.py --lang en  # İngilizce: dist\Triton-EN.exe
```

Her biri tek dosya halinde oluşur (~100 MB, opencv/numpy/PyMuPDF gibi
bağımlılıklar dahil). `Triton.spec` dosyası derleme ayarlarını tutar;
`assets/` klasörü ve gerekli özel paketler (`customtkinter`, `tkinterdnd2`,
`pymupdf`) otomatik olarak pakete dahil edilir.

---

## English

A local, multi-format file converter for your computer. It never sends
files anywhere — every conversion runs on your own machine.

### Supported formats

- **Video:** mp4, mkv, avi, mov, webm, flv, wmv, m4v, mpg, ts, 3gp (+ extracting audio from video)
- **Audio:** mp3, wav, flac, aac, ogg, m4a, wma, opus, aiff
- **Image:** jpg, png, webp, bmp, gif, tiff, ico (+ image → PDF)
- **Documents:** pdf, docx, doc, odt, rtf, txt, pptx, ppt, odp, xlsx, xls, ods, csv, pdf → docx/image

### Running

```
run.bat
```

On first launch it creates a virtual environment and installs dependencies automatically.

### Conversion engines

- **Video/audio (FFmpeg):** Downloaded automatically via the "Download"
  button on the *Settings* tab — into the app's own folder only, never
  installed system-wide.
- **Office documents (LibreOffice):** Word/Excel/PowerPoint conversions
  need a real LibreOffice install. The "Install" button on the *Settings*
  tab opens the official download page in your browser; you download and
  run the .msi yourself.
- **PDF ↔ image, PDF → docx:** No extra install needed (runs in pure
  Python via Pillow, PyMuPDF, pdf2docx).

### Development

```
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

### Languages

The UI is available in Turkish and English (`app/i18n.py`). While
developing, switch it temporarily with the `TRITON_LANG=en` environment
variable.

### Building the .exe

```
.venv\Scripts\pip install pyinstaller
.venv\Scripts\python build.py            # Turkish: dist\Triton.exe
.venv\Scripts\python build.py --lang en  # English: dist\Triton-EN.exe
```

Each build is a single file (~100 MB, includes dependencies like
opencv/numpy/PyMuPDF). `Triton.spec` holds the build configuration; the
`assets/` folder and the packages that need explicit collection
(`customtkinter`, `tkinterdnd2`, `pymupdf`) are bundled in automatically.
