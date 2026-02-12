import os
import site

# Locate DeepDanbooru
found = False
for sp in site.getsitepackages():
    init_path = os.path.join(sp, "deepdanbooru", "__init__.py")
    if os.path.exists(init_path):
        found = True
        break

if not found:
    raise FileNotFoundError("Cannot find deepdanbooru __init__.py")

# Comment out CLI import
with open(init_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("import deepdanbooru.commands", "# CLI import disabled")

with open(init_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Patched DeepDanbooru at {init_path}")
