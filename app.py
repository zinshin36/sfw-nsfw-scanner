import os
import sys
import logging
import threading
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import types
sys.modules["tensorflow_io"] = types.ModuleType("tensorflow_io")

LOG_FILE = os.path.join(os.getcwd(), "app.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info("Application starting...")

import numpy as np
import tensorflow as tf
import deepdanbooru

logging.info("Libraries loaded")

MODEL = None


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_model():
    global MODEL
    try:
        model_path = resource_path("model")
        MODEL = deepdanbooru.project.load_model_from_project(model_path)
        logging.info("Model loaded successfully")
    except Exception:
        logging.exception("Model failed to load")
        MODEL = None


load_model()


def file_hash(path):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


stop_event = threading.Event()


def process_folder(folder, progress_callback, list_callback):

    if MODEL is None:
        messagebox.showerror("Error", "Model not loaded.")
        return

    sfw_dir = os.path.join(folder, "sfw")
    nsfw_dir = os.path.join(folder, "nsfw")
    dup_dir = os.path.join(folder, "duplicates")

    os.makedirs(sfw_dir, exist_ok=True)
    os.makedirs(nsfw_dir, exist_ok=True)
    os.makedirs(dup_dir, exist_ok=True)

    hashes = set()

    files = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]

    total = len(files)

    for index, fname in enumerate(files):

        if stop_event.is_set():
            break

        path = os.path.join(folder, fname)
        list_callback(fname)

        try:
            # Duplicate detection
            h = file_hash(path)
            if h in hashes:
                os.rename(path, os.path.join(dup_dir, fname))
                progress_callback(index + 1, total)
                continue
            hashes.add(h)

            # Load image correctly
            image = deepdanbooru.data.load_image_for_evaluate(path, 512, 512)
            image = np.expand_dims(image, 0)

            # Predict
            predictions = MODEL.predict(image, verbose=0)[0]

            # Map tags
            tag_dict = dict(zip(MODEL.tags, predictions))

            explicit_score = tag_dict.get("rating:explicit", 0.0)
            safe_score = tag_dict.get("rating:safe", 0.0)

            # Decide classification
            if explicit_score > safe_score:
                os.rename(path, os.path.join(nsfw_dir, fname))
            else:
                os.rename(path, os.path.join(sfw_dir, fname))

        except Exception:
            logging.exception("Failed processing %s", fname)

        progress_callback(index + 1, total)


class App:

    def __init__(self, root):
        self.root = root
        self.root.title("SFW / NSFW Sorter")
        self.root.geometry("650x450")

        self.folder = tk.StringVar()

        top = tk.Frame(root)
        top.pack(pady=10)

        tk.Entry(top, textvariable=self.folder, width=50).pack(side="left")
        tk.Button(top, text="Browse", command=self.browse).pack(side="left", padx=5)

        self.start_btn = tk.Button(root, text="Start", command=self.start)
        self.start_btn.pack(pady=5)

        self.cancel_btn = tk.Button(root, text="Cancel", command=self.cancel, state="disabled")
        self.cancel_btn.pack(pady=5)

        self.progress = ttk.Progressbar(root, length=600)
        self.progress.pack(pady=10)

        self.listbox = tk.Listbox(root, width=90, height=15)
        self.listbox.pack(pady=10)

    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.set(folder)

    def start(self):
        folder = self.folder.get()
        if not folder:
            messagebox.showerror("Error", "Select a folder first.")
            return

        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress["value"] = 0
        self.listbox.delete(0, tk.END)
        stop_event.clear()

        threading.Thread(
            target=self.run_sort,
            args=(folder,),
            daemon=True
        ).start()

    def run_sort(self, folder):
        def progress_cb(done, total):
            self.progress["maximum"] = total
            self.progress["value"] = done

        def list_cb(fname):
            self.listbox.insert(tk.END, fname)
            self.listbox.yview(tk.END)

        process_folder(folder, progress_cb, list_cb)

        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        messagebox.showinfo("Done", "Sorting completed.")

    def cancel(self):
        stop_event.set()
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        messagebox.showinfo("Stopped", "Sorting cancelled.")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
