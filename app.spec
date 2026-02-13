# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = []
hiddenimports += collect_submodules('tensorflow')
hiddenimports += collect_submodules('tensorflow_io')
hiddenimports += collect_submodules('deepdanbooru')
hiddenimports += collect_submodules('nudenet')

datas = []
datas += collect_data_files('tensorflow')
datas += collect_data_files('tensorflow_io')
datas += collect_data_files('deepdanbooru')
datas += collect_data_files('nudenet')

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='app',
    debug=False,
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
