# Triton

Bilgisayarda yerel çalışan, çok formatlu dosya dönüştürücü. İnternete dosya
göndermez — tüm dönüşümler kendi makinenizde yapılır.

## Desteklenen formatlar

- **Video:** mp4, mkv, avi, mov, webm, flv, wmv, m4v, mpg, ts, 3gp (+ videodan ses çıkarma)
- **Ses:** mp3, wav, flac, aac, ogg, m4a, wma, opus, aiff
- **Görsel:** jpg, png, webp, bmp, gif, tiff, ico (+ görsel → PDF)
- **Belge:** pdf, docx, doc, odt, rtf, txt, pptx, ppt, odp, xlsx, xls, ods, csv, pdf → docx/görsel

## Çalıştırma

```
run.bat
```

İlk çalıştırmada sanal ortam kurulur ve bağımlılıklar otomatik indirilir.

## Dönüştürme motorları

- **Video/ses (FFmpeg):** Uygulama içindeki *Ayarlar* sekmesinden "İndir" ile
  otomatik iner; sisteme kurulmaz, yalnızca uygulamanın kendi klasörüne iner.
- **Ofis belgeleri (LibreOffice):** Word/Excel/PowerPoint dönüşümleri gerçek
  bir LibreOffice kurulumu gerektirir. *Ayarlar* sekmesindeki "Kur" butonu
  resmi indirme sayfasını tarayıcıda açar; .msi dosyasını siz indirip
  çalıştırırsınız.
- **PDF ↔ görsel, PDF → docx:** Ek kurulum gerekmez (Pillow, PyMuPDF, pdf2docx
  ile Python içinde çalışır).

## Geliştirme

```
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

## .exe derleme

```
.venv\Scripts\pip install pyinstaller
.venv\Scripts\python build.py
```

Çıktı `dist\Triton.exe` olarak tek dosya halinde oluşur (~100 MB, opencv/numpy/
PyMuPDF gibi bağımlılıklar dahil). `Triton.spec` dosyası derleme ayarlarını
tutar; `assets/` klasörü ve gerekli özel paketler (`customtkinter`,
`tkinterdnd2`, `pymupdf`) otomatik olarak pakete dahil edilir.
