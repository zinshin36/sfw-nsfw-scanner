import os
import sys
import site

# Find deepdanbooru in site-packages
site_packages_paths = site.getsitepackages()
found = False
for sp in site_packages_paths:
    init_path = os.path.join(sp, "deepdanbooru", "__init__.py")
    if os.path.exists(init_path):
        found = True
        break

if not found:
    print("ERROR: Could not find deepdanbooru __init__.py")
    sys.exit(1)

# Patch __init__.py
with open(init_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("import deepdanbooru.commands", "# CLI disabled for PyInstaller build")

with open(init_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Patched deepdanbooru __init__.py at {init_path} successfully.")
