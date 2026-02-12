import os
import sys
import logging
import tkinter as tk
from tkinter import messagebox

import tensorflow as tf
import deepdanbooru.project as dd_project
import deepdanbooru.model as dd_model


# =========================
# Logging Setup
# =========================

LOG_FILE = "app.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logging.info("===== PROGRAM START =====")


# =========================
# PyInstaller Safe Path
# =========================

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)


MODEL_PATH = resource_path("model/deepdanbooru-v3-20211112-sgd-e28")


# =========================
# Load Model Automatically
# =========================

def load_deepdanbooru_model():
    project = dd_project.load_project_from_path(MODEL_PATH)
    model = dd_model.create_model_from_project(project)
    model.load_weights(project.weights_path)
    return model, project.tags


# =========================
# GUI Application
# =========================

class NSFWScannerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("NSFW Scanner")
        self.root.geometry("400x200")

        try:
            logging.info("Loading DeepDanbooru model...")
            self.model, self.tags = load_deepdanbooru_model()
            logging.info("Model loaded successfully.")
        except Exception as e:
            logging.exception("Model loading failed.")
            messagebox.showerror("Error", f"Model failed to load:\n{e}")
            sys.exit(1)

        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="NSFW Scanner Ready", font=("Arial", 16)).pack(pady=30)

        tk.Button(
            self.root,
            text="Exit",
            command=self.root.quit,
            width=30
        ).pack(pady=10)


# =========================
# Start Application
# =========================

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = NSFWScannerApp(root)
        root.mainloop()
    except Exception:
        logging.exception("Fatal crash.")
        sys.exit(1)
