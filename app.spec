# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all
import os

# Collect EVERYTHING from deepdanbooru
dd_datas, dd_binaries, dd_hidden = collect_all("deepdanbooru")

# Collect EVERYTHING from tensorflow
tf_datas, tf_binaries, tf_hidden = collect_all("tensorflow")

# Collect EVERYTHING from tensorflow_io
tfio_datas, tfio_binaries, tfio_hidden = collect_all("tensorflow_io")

# Collect EVERYTHING from nudenet
nn_datas, nn_binaries, nn_hidden = collect_all("nudenet")

datas = dd_datas + tf_datas + tfio_datas + nn_datas
binaries = dd_binaries + tf_binaries + tfio_binaries + nn_binaries
hiddenimports = dd_hidden + tf_hidden + tfio_hidden + nn_hidden

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
