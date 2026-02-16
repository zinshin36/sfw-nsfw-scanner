# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

numpy_datas, numpy_binaries, numpy_hidden = collect_all("numpy")
tensorflow_datas, tensorflow_binaries, tensorflow_hidden = collect_all("tensorflow")
scipy_datas, scipy_binaries, scipy_hidden = collect_all("scipy")
deepdanbooru_datas, deepdanbooru_binaries, deepdanbooru_hidden = collect_all("deepdanbooru")

a = Analysis(
    ["app.py"],
    pathex=[sys.base_prefix],
    binaries=(
        numpy_binaries
        + tensorflow_binaries
        + scipy_binaries
        + deepdanbooru_binaries
    ),
    datas=(
        numpy_datas
        + tensorflow_datas
        + scipy_datas
        + deepdanbooru_datas
    ),
    hiddenimports=(
        numpy_hidden
        + tensorflow_hidden
        + scipy_hidden
        + deepdanbooru_hidden
    ),
    hookspath=[],
    runtime_hooks=[],
    excludes=["tensorflow_io"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=False,
    name="sfw_nsfw_sorter",
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
    name="sfw_nsfw_sorter"
)
