import os
import sys
import logging
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Prevent tensorflow_io native loading issues
import types
sys.modules["tensorflow_io"] = types.ModuleType("tensorflow_io")

# Setup logging
LOG_FILE = os.path.join(os.getcwd(), "app.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info("Application starting...")

# Load ML Libraries
try:
    import numpy as np
    logging.info("NumPy loaded successfully")
except Exception as e:
    logging.exception("Failed loading NumPy")
    raise

try:
    import tensorflow as tf
    logging.info("TensorFlow loaded successfully")
except Exception as e:
    logging.exception("Failed loading TensorFlow")
    raise

try:
    import deepdanbooru
    logging.info("DeepDanbooru loaded successfully")
except Exception as e:
    logging.exception("Failed loading DeepDanbooru")
    raise

logging.info("ML libraries loaded successfully")

# Load model
MODEL = None

def load_model():
    global MODEL
    try:
        model_path = os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), "model")
        MODEL = deepdanbooru.project.load_model_from_project(model_path)
        logging.info("Model loaded successfully")
    except Exception as e:
        logging.exception("Failed loading model")
        MODEL = None

load_model()

# Sorting thread logic
task_queue = queue.Queue()
stop_event = threading.Event()

def process_queue(folder, progress_callback, list_callback):
    try:
        images = [
            f for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f))
        ]
        total = len(images)
        for i, fname in enumerate(images):
            if stop_event.is_set():
                break

            path = os.path.join(folder, fname)
            list_callback(fname)

            try:
                image = deepdanbooru.data.load_image_for_evaluate(path)
                result = deepdanbooru.project.predict_tags(MODEL, image)
                score = result.get("rating:explicit", 0)

                dest = "nsfw" if score > 0.5 else "sfw"
                target_folder = os.path.join(folder, dest)
                os.makedirs(target_folder, exist_ok=True)
                os.rename(path, os.path.join(target_folder, fname))

            except Exception:
                logging.exception("Failed processing %s", fname)

            progress_callback(i + 1, total)

    except Exception:
        logging.exception("Sorting thread failed")

# GUI
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("SFW/NSFW Sorter")
        self.root.geometry("600x400")

        self.folder_path = tk.StringVar()

        frame = tk.Frame(root)
        frame.pack(pady=10, padx=10, fill="x")

        tk.Label(frame, text="Folder:").pack(side="left")
        self.entry = tk.Entry(frame, textvariable=self.folder_path, width=40)
        self.entry.pack(side="left", padx=5)

        tk.Button(frame, text="Browse", command=self.browse).pack(side="left")

        self.start_btn = tk.Button(root, text="Start Sorting", command=self.start_sort)
        self.start_btn.pack(pady=5)

        self.cancel_btn = tk.Button(root, text="Cancel", command=self.cancel_sort, state="disabled")
        self.cancel_btn.pack(pady=5)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=500, mode="determinate")
        self.progress.pack(pady=10)

        self.listbox = tk.Listbox(root, width=80, height=10)
        self.listbox.pack(pady=10)

    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)

    def start_sort(self):
        folder = self.folder_path.get()
        if not folder:
            messagebox.showerror("Error", "Select a folder first")
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
        def progress_cb(completed, total):
            self.progress["maximum"] = total
            self.progress["value"] = completed

        def list_cb(fname):
            self.listbox.insert(tk.END, fname)
            self.listbox.yview(tk.END)

        process_queue(folder, progress_cb, list_cb)
        self.finish_sort()

    def cancel_sort(self):
        stop_event.set()
        self.finish_sort("Sorting cancelled")

    def finish_sort(self, msg=None):
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

        if msg:
            messagebox.showinfo("Info", msg)
        else:
            messagebox.showinfo("Info", "Sorting completed")

root = tk.Tk()
app = App(root)
root.mainloop()
