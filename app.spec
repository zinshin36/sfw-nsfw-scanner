# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None


# --- Collect everything properly ---
numpy_datas, numpy_binaries, numpy_hidden = collect_all("numpy")
tensorflow_datas, tensorflow_binaries, tensorflow_hidden = collect_all("tensorflow")
deepdanbooru_datas, deepdanbooru_binaries, deepdanbooru_hidden = collect_all("deepdanbooru")


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=numpy_binaries + tensorflow_binaries + deepdanbooru_binaries,
    datas=numpy_datas + tensorflow_datas + deepdanbooru_datas,
    hiddenimports=numpy_hidden + tensorflow_hidden + deepdanbooru_hidden,
    hookspath=["hooks"],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="app",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="app",
)
