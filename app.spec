# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None

numpy_datas, numpy_binaries, numpy_hidden = collect_all("numpy")
tensorflow_datas, tensorflow_binaries, tensorflow_hidden = collect_all("tensorflow")
tfio_datas, tfio_binaries, tfio_hidden = collect_all("tensorflow_io")
deepdanbooru_datas, deepdanbooru_binaries, deepdanbooru_hidden = collect_all("deepdanbooru")

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=(
        numpy_binaries
        + tensorflow_binaries
        + tfio_binaries
        + deepdanbooru_binaries
    ),
    datas=(
        numpy_datas
        + tensorflow_datas
        + tfio_datas
        + deepdanbooru_datas
    ),
    hiddenimports=(
        numpy_hidden
        + tensorflow_hidden
        + tfio_hidden
        + deepdanbooru_hidden
    ),
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

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
    console=True,
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
