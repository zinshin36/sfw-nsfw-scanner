from PyInstaller.utils.hooks import collect_all

# Collect all DeepDanbooru files
datas, binaries, hiddenimports = collect_all("deepdanbooru")
