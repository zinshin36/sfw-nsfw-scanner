# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all data, binaries, hidden imports for dependencies
deep_datas, deep_bins, deep_hidden = collect_all("deepdanbooru")
tf_datas, tf_bins, tf_hidden = collect_all("tensorflow")
scipy_datas, scipy_bins, scipy_hidden = collect_all("scipy")
tfio_datas, tfio_bins, tfio_hidden = collect_all("tensorflow_io")
numpy_datas, numpy_bins, numpy_hidden = collect_all("numpy")
pillow_datas, pillow_bins, pillow_hidden = collect_all("PIL")

binaries = deep_bins + tf_bins + scipy_bins + tfio_bins + numpy_bins + pillow_bins
datas = deep_datas + tf_datas + scipy_datas + tfio_datas + numpy_datas + pillow_datas
hiddenimports = deep_hidden + tf_hidden + scipy_hidden + tfio_hidden + numpy_hidden + pillow_hidden

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
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
    name='app',
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
    name='app',
)
