# Triton

*[Türkçe](#türkçe) | [English](#english)*

---

## Türkçe

Bilgisayarda yerel çalışan, çok formatlu dosya dönüştürücü. İnternete dosya
göndermez — tüm dönüşümler kendi makinenizde yapılır.

### Web sürümü

Aynı arayüzün tarayıcıda çalışan hâli: **[triton-app.vercel.app](https://triton-app.vercel.app)**.
Dosyalar sunucuya yüklenmez, dönüşüm tarayıcıda yapılır (kaynak: [`web/`](web)).
Masaüstü sürümünden farkları: PowerPoint, eski `.doc/.ppt/.rtf` ve `.odp` yok; PDF → Word yalnızca metni
taşır; video/ses için FFmpeg (≈30 MB) ilk kullanımda indirilir, masaüstüne göre yavaştır ve dosya başına 1 GB sınırı vardır.

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

- **Video/ses (FFmpeg):** Başlıktaki FFmpeg göstergesinden açılan ekranda
  "İndir" ile otomatik iner; sisteme kurulmaz, yalnızca uygulamanın kendi
  klasörüne iner.
- **Belgeler (dahili motor):** docx, xlsx/xls/csv, pptx, odt ve txt dosyalarını
  PDF'e çevirir (ayrıca xlsx ↔ csv, xls → xlsx, txt ↔ docx). Küçük Python
  kütüphaneleriyle HTML'e çevirip sistemdeki Edge veya Chrome ile PDF'e basar;
  **kurulum gerektirmez**. Metin, tablo ve görseller korunur; sayfa düzeni,
  üst/alt bilgi ve özel yazı tipleri birebir korunmaz (PowerPoint metin kutuları
  ve görselleri konumlarıyla çıkar, tema renkleri/madde işaretleri yaklaşıktır).
- **LibreOffice (isteğe bağlı):** Yalnızca eski `.doc`/`.ppt`/`.rtf`/`.odp`/`.ods`
  dosyaları ve Office biçimleri arası dönüşümler için gerekir; sayfa düzenini en
  sadık koruyan motordur. Yaklaşık 700 MB yer kaplar, Triton onsuz da çalışır.
  Kur düğmesi resmi indirme sayfasını tarayıcıda açar.
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

### Lisans

Tüm hakları saklıdır (All Rights Reserved). Kaynak kod yalnızca
görüntüleme amaçlıdır; kopyalanamaz, değiştirilemez veya dağıtılamaz.
Derlenmiş uygulama kişisel, ticari olmayan kullanım için olduğu gibi
kullanılabilir. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın.

---

## English

A local, multi-format file converter for your computer. It never sends
files anywhere — every conversion runs on your own machine.

### Web version

The same interface in the browser: **[triton-app.vercel.app](https://triton-app.vercel.app)**.
Files are not uploaded; conversion runs in your browser (source: [`web/`](web)).
Differences from the desktop app: no PowerPoint, legacy `.doc/.ppt/.rtf` or `.odp`; PDF → Word carries text only;
video/audio use FFmpeg (≈30 MB) downloaded on first use, which is slower than desktop and capped at 1 GB per file.

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

- **Video/audio (FFmpeg):** Downloaded automatically with the "Download"
  button on the engines screen (open it from the FFmpeg indicator in the
  header) — into the app's own folder only, never installed system-wide.
- **Documents (built-in engine):** Converts docx, xlsx/xls/csv, pptx, odt and
  txt to PDF (plus xlsx ↔ csv, xls → xlsx, txt ↔ docx). Small Python libraries
  turn the file into HTML and the Edge or Chrome already on your system prints
  it to PDF, so **nothing to install**. Text, tables and images are kept; exact
  page layout, headers/footers and custom fonts are not (PowerPoint text boxes
  and pictures keep their positions; theme colours and bullets are approximate).
- **LibreOffice (optional):** Only needed for old `.doc`/`.ppt`/`.rtf`/`.odp`/`.ods`
  files and conversions between Office formats; it is the engine that keeps
  page layout most faithfully. Takes about 700 MB, and Triton works without it.
  The install button opens the official download page in your browser.
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

### License

All Rights Reserved. The source code is provided for viewing purposes
only and may not be copied, modified, or distributed. The compiled
application may be used as-is for personal, non-commercial purposes. See
[LICENSE](LICENSE) for details.
