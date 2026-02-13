# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Collect tensorflow properly
tf_datas, tf_binaries, tf_hidden = collect_all('tensorflow')
datas += tf_datas
binaries += tf_binaries
hiddenimports += tf_hidden

# Collect tensorflow_io
tio_datas, tio_binaries, tio_hidden = collect_all('tensorflow_io')
datas += tio_datas
binaries += tio_binaries
hiddenimports += tio_hidden

# Collect deepdanbooru
dd_datas, dd_binaries, dd_hidden = collect_all('deepdanbooru')
datas += dd_datas
binaries += dd_binaries
hiddenimports += dd_hidden

# Collect nudenet
nn_datas, nn_binaries, nn_hidden = collect_all('nudenet')
datas += nn_datas
binaries += nn_binaries
hiddenimports += nn_hidden


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
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
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='app',
)
