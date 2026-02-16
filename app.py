import os
import sys
import logging

# -------------------------------------------------
# CRITICAL RUNTIME FIXES FOR FROZEN ML APPS
# -------------------------------------------------

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure DLL lookup path
os.environ["PATH"] = BASE_DIR + os.pathsep + os.environ.get("PATH", "")

if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BASE_DIR)

# Prevent OpenMP conflicts
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Prevent excessive thread spawning
os.environ["OMP_NUM_THREADS"] = "1"

# Reduce TensorFlow logging noise
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# -------------------------------------------------
# Logging
# -------------------------------------------------

logging.basicConfig(
    filename="app_debug.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info("Application starting...")
logging.info(f"Base directory: {BASE_DIR}")

# -------------------------------------------------
# SAFE ML IMPORT
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
# SIMPLE GUI TEST WINDOW
# -------------------------------------------------

import tkinter as tk

def main():
    root = tk.Tk()
    root.title("SFW / NSFW Sorter")
    root.geometry("500x300")

    label = tk.Label(root, text="Application Loaded Successfully", font=("Arial", 14))
    label.pack(pady=40)

    root.mainloop()

if __name__ == "__main__":
    main()
