import os
import sys
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# -------------------------------------------------
# Logging Setup
# -------------------------------------------------

BASE_DIR = getattr(sys, "_MEIPASS", os.path.abspath("."))
LOG_FILE = os.path.join(os.getcwd(), "app.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info("Application starting...")
logging.info(f"Base directory: {BASE_DIR}")

# -------------------------------------------------
# Load ML Libraries
# -------------------------------------------------

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

# -------------------------------------------------
# Load Model
# -------------------------------------------------

MODEL = None

def load_model():
    global MODEL
    try:
        model_path = os.path.join(BASE_DIR, "model")
        MODEL = deepdanbooru.project.load_model_from_project(model_path)
        logging.info("Model loaded successfully")
    except Exception:
        logging.exception("Failed to load model")


# -------------------------------------------------
# Sorting Logic (placeholder for your real logic)
# -------------------------------------------------

def sort_folder(folder_path):
    if MODEL is None:
        messagebox.showerror("Error", "Model not loaded")
        return

    images = list(Path(folder_path).glob("*.*"))

    for image_path in images:
        logging.info(f"Processing {image_path.name}")

        try:
            image = deepdanbooru.data.load_image_for_evaluate(str(image_path))
            result = deepdanbooru.project.predict_tags(MODEL, image)

            # Example logic — replace with yours
            score = result.get("rating:explicit", 0)

            if score > 0.5:
                target_folder = Path(folder_path) / "nsfw"
            else:
                target_folder = Path(folder_path) / "sfw"

            target_folder.mkdir(exist_ok=True)
            image_path.rename(target_folder / image_path.name)

            logging.info(f"Moved {image_path.name} -> {target_folder.name}")

        except Exception:
            logging.exception(f"Failed processing {image_path.name}")


# -------------------------------------------------
# GUI
# -------------------------------------------------

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("SFW / NSFW Sorter")
        self.root.geometry("500x250")

        tk.Label(root, text="SFW / NSFW Image Sorter", font=("Arial", 16)).pack(pady=10)

        tk.Button(root, text="Select Folder", command=self.select_folder).pack(pady=5)

        self.status = tk.Label(root, text="Model loading...", fg="blue")
        self.status.pack(pady=10)

        load_model()
        self.status.config(text="Model loaded")

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            sort_folder(folder)
            messagebox.showinfo("Done", "Sorting completed")


# -------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
