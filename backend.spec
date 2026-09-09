# PyInstaller spec for the StreamRip Flask backend (lean, onedir).
# Build with:  python -m PyInstaller backend.spec --noconfirm --distpath dist-backend
# Output:      dist-backend/streamrip-backend/streamrip-backend(.exe)  (folder)
#
# onedir (not onefile) on purpose: a 300MB onefile re-extracts itself to
# %TEMP% on EVERY launch (~10-30s of hanging + temp litter on crash).
# A folder build starts in ~2s. Electron ships folders fine via extraResources.
# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# spotdl and its audio/metadata providers (ytmusicapi, spotapi, SpotipyFree, etc.)
# require comprehensive submodule sweeps and data files (e.g. ytmusicapi locales).
hidden = [
    "yt_dlp",
    "spotdl",
    "spotdl.console",
    "spotdl.__main__",
    "SpotipyFree",
    "spotapi",
    "pymongo",
    "bson",
    "gridfs",
    "pykakasi",
    "jaconv",
    "imageio_ffmpeg",
    "ytmusicapi",
    "syncedlyrics",
    "spotipy",
    "soundcloud",
    "rich",
    "mutagen",
    "rapidfuzz",
]
for mod in (
    "spotdl",
    "spotapi",
    "SpotipyFree",
    "pymongo",
    "bson",
    "gridfs",
    "pykakasi",
    "ytmusicapi",
    "syncedlyrics",
    "spotipy",
    "soundcloud",
):
    try:
        hidden += collect_submodules(mod)
    except Exception:
        pass

datas = [
    ("UI.html", "."),
    ("Logo.svg", "."),
    ("css", "css"),
    ("js", "js"),
]
for pkg in (
    "certifi",
    "yt_dlp",
    "spotdl",
    "spotapi",
    "pymongo",
    "bson",
    "gridfs",
    "pykakasi",
    "jaconv",
    "imageio_ffmpeg",
    "ytmusicapi",
    "syncedlyrics",
    "soundcloud",
    "rich",
):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

# Explicitly ensure ytmusicapi locales are bundled for gettext translation
try:
    import ytmusicapi
    ytm_locales = Path(ytmusicapi.__file__).parent / "locales"
    if ytm_locales.is_dir():
        datas.append((str(ytm_locales), "ytmusicapi/locales"))
except Exception:
    pass

# pykakasi kanwadict / dictionary DBs required at runtime by spotdl.
try:
    datas += collect_data_files("pykakasi")
except Exception:
    pass

# Heavy packages that the backend never touches at runtime.
# (Keeps the exe small and the build fast.)
# Verified 2026-09: torch/polars/botocore/transformers & co (~165MB!) get
# swept in from a dirty dev env via boto3/gradio/accelerate chains — the app
# runs fine without them (numpy/PIL/lxml/mutagen/rapidfuzz/cryptodome stay).
excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "pandas",
    "sklearn",
    "torch",
    "torchvision",
    "torchaudio",
    "tensorflow",
    "polars",
    "botocore",
    "boto3",
    "aiobotocore",
    "s3transfer",
    "transformers",
    "tokenizers",
    "tiktoken",
    "grpc",
    "psycopg2",
    "accelerate",
    "asyncpg",
    "gradio",
    "openai",
    "sounddevice",
    "pytest",
    "_pytest",
    "pluggy",
    "iniconfig",
    "hf_xet",
    "huggingface_hub",
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
    [],
    exclude_binaries=True,  # onedir layout: binaries collected below
    name="streamrip-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # no UPX: slower start + Windows Defender false positives
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

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="streamrip-backend",
)
