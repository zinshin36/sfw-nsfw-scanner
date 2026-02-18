# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all
import os

block_cipher = None

deep_datas, deep_bins, deep_hidden = collect_all("deepdanbooru")
tf_datas, tf_bins, tf_hidden = collect_all("tensorflow")
scipy_datas, scipy_bins, scipy_hidden = collect_all("scipy")
numpy_datas, numpy_bins, numpy_hidden = collect_all("numpy")
pillow_datas, pillow_bins, pillow_hidden = collect_all("PIL")
cv2_datas, cv2_bins, cv2_hidden = collect_all("cv2")

binaries = deep_bins + tf_bins + scipy_bins + numpy_bins + pillow_bins + cv2_bins
datas = deep_datas + tf_datas + scipy_datas + numpy_datas + pillow_datas + cv2_datas
hiddenimports = deep_hidden + tf_hidden + scipy_hidden + numpy_hidden + pillow_hidden + cv2_hidden

datas += [(os.path.join("model"), "model")]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='app',
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
