import sys
import os
import types
import logging
import tkinter as tk
from tkinter import messagebox

# Prevent tensorflow_io native loading issues
sys.modules["tensorflow_io"] = types.ModuleType("tensorflow_io")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logging.info("Application starting...")

BASE_DIR = getattr(sys, "_MEIPASS", os.path.abspath("."))
logging.info(f"Base directory: {BASE_DIR}")

# ---- Load ML Libraries Safely ----

try:
    import numpy as np
    logging.info("NumPy loaded successfully")
except Exception:
    logging.exception("Failed loading NumPy")
    raise

try:
    import tensorflow as tf
    logging.info("TensorFlow loaded successfully")
except Exception:
    logging.exception("Failed loading TensorFlow")
    raise

try:
    import deepdanbooru
    logging.info("DeepDanbooru loaded successfully")
except Exception:
    logging.exception("Failed loading DeepDanbooru")
    raise

logging.info("ML libraries loaded successfully")

# ---- Minimal GUI ----

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("SFW / NSFW Sorter")
        self.root.geometry("400x200")

        label = tk.Label(
            root,
            text="Application loaded successfully",
            font=("Arial", 14)
        )
        label.pack(pady=40)

        button = tk.Button(
            root,
            text="Test TensorFlow",
            command=self.test_tf
        )
        button.pack(pady=10)

    def test_tf(self):
        try:
            version = tf.__version__
            messagebox.showinfo("TensorFlow Version", f"TensorFlow {version}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
