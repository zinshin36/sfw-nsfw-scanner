# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

block_cipher = None

numpy_binaries = collect_dynamic_libs("numpy")
tensorflow_binaries = collect_dynamic_libs("tensorflow")
deepdanbooru_binaries = collect_dynamic_libs("deepdanbooru")

hidden_imports = (
    collect_submodules("deepdanbooru")
    + collect_submodules("tensorflow")
)

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=numpy_binaries + tensorflow_binaries + deepdanbooru_binaries,
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
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
