import os
import sys
import tkinter as tk
from tkinter import messagebox
import logging

# =========================
# Safe Base Path
# =========================

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# Logging (File Only)
# =========================

LOG_FILE = os.path.join(BASE_DIR, "app.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logging.info("Application starting...")

# =========================
# Import ML Libraries
# =========================

try:
    import tensorflow as tf
    import deepdanbooru
    logging.info("TensorFlow and DeepDanbooru loaded successfully.")
except Exception as e:
    logging.exception("Failed loading ML libraries")
    raise

# =========================
# GUI
# =========================

root = tk.Tk()
root.title("SFW / NSFW Sorter")
root.geometry("400x200")

label = tk.Label(root, text="DeepDanbooru Loaded Successfully")
label.pack(pady=40)

btn = tk.Button(root, text="Exit", command=root.destroy)
btn.pack()

root.mainloop()
