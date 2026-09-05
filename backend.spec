# PyInstaller spec for the StreamRip Flask backend (lean).
# Build with:  python -m PyInstaller backend.spec --noconfirm --distpath dist-backend
# Output:      dist-backend/streamrip-backend(.exe)
# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Only spotdl needs a submodule sweep (dynamic provider imports).
# flask/werkzeug/jinja2/yt-dlp are handled by PyInstaller's own hooks
# (yt-dlp ships its own __pyinstaller hook for extractors).
hidden = ["yt_dlp", "spotdl", "spotdl.console", "spotdl.__main__"]
try:
    hidden += collect_submodules("spotdl")
except Exception:
    pass

datas = [
    ("UI.html", "."),
    ("Logo.svg", "."),
]
for pkg in ("certifi", "yt_dlp", "spotdl"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

# Heavy packages that the backend never touches at runtime.
# (Keeps the exe small and the build fast.)
excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "pandas",
    "sklearn",
    "torch",
    "tensorflow",
    "notebook",
    "IPython",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "wx",
    "imageio",
    "cv2",
    "av",
]

a = Analysis(
    ["server.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=sorted(set(hidden)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="streamrip-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # windowed: no console popup next to the Electron shell
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="build/icon.ico" if sys.platform == "win32" else None,
)
