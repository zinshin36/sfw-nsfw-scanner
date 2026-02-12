import os
import sys
import logging
import tkinter as tk
from tkinter import filedialog, messagebox

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
# DeepDanbooru Loader
# =========================

def load_deepdanbooru_model(project_path):
    project = dd_project.load_project_from_path(project_path)
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

        self.model = None
        self.tags = None

        self.create_widgets()

    def create_widgets(self):

        tk.Label(self.root, text="NSFW Scanner", font=("Arial", 16)).pack(pady=10)

        tk.Button(
            self.root,
            text="Load DeepDanbooru Model",
            command=self.select_model_folder,
            width=30
        ).pack(pady=5)

        tk.Button(
            self.root,
            text="Exit",
            command=self.root.quit,
            width=30
        ).pack(pady=5)

    def select_model_folder(self):
        folder = filedialog.askdirectory(title="Select DeepDanbooru Project Folder")
        if not folder:
            return

        try:
            logging.info(f"Loading model from: {folder}")
            self.model, self.tags = load_deepdanbooru_model(folder)
            messagebox.showinfo("Success", "Model loaded successfully!")
            logging.info("Model loaded successfully.")

        except Exception as e:
            logging.exception("Model loading failed.")
            messagebox.showerror("Error", f"Failed to load model:\n{e}")


# =========================
# Start Application
# =========================

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = NSFWScannerApp(root)
        root.mainloop()
    except Exception as e:
        logging.exception("Fatal crash.")
        sys.exit(1)
