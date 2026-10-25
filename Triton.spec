# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

exe_name = os.environ.get('TRITON_EXE_NAME', 'Triton')

datas = [('assets', 'assets')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('tkinterdnd2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pymupdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# the built-in document engine: these ship template/data files that only matter at runtime
for pkg in ('pptx', 'docx', 'openpyxl', 'odf', 'mammoth'):
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # nothing in the app uses these; keeping them out stops a stray dev-environment install from bloating the exe
    excludes=['numpy', 'cv2', 'fontTools', 'matplotlib', 'pandas', 'scipy', 'IPython', 'pytest', 'pydoc_data'],
    noarchive=False,
    optimize=0,
)
# dead weight collect_all() drags in: PyMuPDF's C headers/import libs (build-time only) and Pillow's AVIF codec
# (Triton converts jpg/png/webp/bmp/gif/tiff/ico; Pillow skips the AVIF plugin cleanly when the module is absent)
_unused = ('mupdf-devel', '_avif')
a.binaries = [b for b in a.binaries if not any(u in b[0] for u in _unused)]
a.datas = [d for d in a.datas if not any(u in d[0] for u in _unused)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/app.ico'],
)
