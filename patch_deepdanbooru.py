import deepdanbooru
import os

init_path = os.path.join(os.path.dirname(deepdanbooru.__file__), "__init__.py")

with open(init_path, "r", encoding="utf-8") as f:
    content = f.read()

# Comment out the CLI import
content = content.replace("import deepdanbooru.commands", "# CLI disabled for PyInstaller build")

with open(init_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patched deepdanbooru __init__.py successfully.")
