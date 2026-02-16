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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Ensure BASE_DIR is defined
log_file_path = os.path.join(BASE_DIR, "app_debug.log")

logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info("Application starting...")
logging.info(f"Base directory: {BASE_DIR}")

# -------------------------------------------------
# SAFE ML IMPORT
# -------------------------------------------------

import logging
import sys

try:
    import numpy as np
    logging.info("Numpy loaded successfully")
except ImportError as e:
    logging.exception("Failed loading Numpy: %s", e)
    sys.exit(1)

try:
    import tensorflow as tf
    logging.info("TensorFlow loaded successfully")
except ImportError as e:
    logging.exception("Failed loading TensorFlow: %s", e)
    sys.exit(1)

try:
    import deepdanbooru as ddb
    logging.info("DeepDanbooru loaded successfully")
except ImportError as e:
    logging.exception("Failed loading DeepDanbooru: %s", e)
    sys.exit(1)

logging.info("ML libraries loaded successfully")

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
