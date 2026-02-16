import os
import sys
import logging

# -------------------------------------------------
# FORCE DLL PATH FIX FOR PYINSTALLER + NUMPY
# -------------------------------------------------

if getattr(sys, "frozen", False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

os.environ["PATH"] = base_dir + os.pathsep + os.environ.get("PATH", "")

# On Python 3.8+ this is required for DLL loading
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(base_dir)

# -------------------------------------------------
# Logging
# -------------------------------------------------

logging.basicConfig(
    filename="app_debug.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info("Application starting...")
logging.info(f"Base directory: {base_dir}")

# -------------------------------------------------
# Import ML Libraries
# -------------------------------------------------

try:
    import numpy as np
    import tensorflow as tf
    import deepdanbooru as ddb
    logging.info("ML libraries loaded successfully")
except Exception:
    logging.exception("Failed loading ML libraries")
    sys.exit(1)

# -------------------------------------------------
# GUI
# -------------------------------------------------

import tkinter as tk
from tkinter import filedialog, messagebox


def main():
    root = tk.Tk()
    root.title("SFW / NSFW Sorter")
    root.geometry("500x300")

    label = tk.Label(root, text="Application Loaded Successfully", font=("Arial", 14))
    label.pack(pady=40)

    root.mainloop()


if __name__ == "__main__":
    main()
