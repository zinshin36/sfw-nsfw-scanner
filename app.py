import os
import sys
import logging
import threading
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image
import numpy as np
import tensorflow as tf
import deepdanbooru
import cv2


LOG_FILE = os.path.join(os.getcwd(), "app.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info("Application starting...")
logging.info("Libraries loaded")

MODEL = None
TAGS = []


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_model():
    global MODEL, TAGS
    try:
        model_path = resource_path("model")

        MODEL = deepdanbooru.project.load_model_from_project(model_path)
        MODEL.compile()

        with open(os.path.join(model_path, "tags.txt"), "r", encoding="utf-8") as f:
            TAGS = [line.strip() for line in f.readlines()]

        logging.info("Model and tags loaded successfully")

    except Exception:
        logging.exception("Model failed to load")
        MODEL = None


load_model()


def file_hash(path):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def preprocess_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.resize(frame, (512, 512))
    frame = frame.astype(np.float32) / 255.0
    return np.expand_dims(frame, 0)


def classify_image_array(img_array):
    preds = MODEL.predict(img_array, verbose=0)[0]
    tag_dict = dict(zip(TAGS, preds))

    explicit = tag_dict.get("rating:explicit", 0.0)
    questionable = tag_dict.get("rating:questionable", 0.0)

    if explicit > 0.25 or questionable > 0.35:
        return "nsfw"
    return "sfw"


def classify_video(path):
    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        return "sfw"

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    max_seconds = 10
    max_frames = int(min(total_frames, fps * max_seconds))
    sample_interval = int(fps)

    nsfw_votes = 0
    sfw_votes = 0

    for frame_idx in range(0, max_frames, sample_interval):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        img = preprocess_frame(frame)
        result = classify_image_array(img)

        if result == "nsfw":
            nsfw_votes += 1
        else:
            sfw_votes += 1

    cap.release()

    return "nsfw" if nsfw_votes > sfw_votes else "sfw"


def classify_gif(path):
    gif = Image.open(path)

    nsfw_votes = 0
    sfw_votes = 0

    frame_count = min(10, getattr(gif, "n_frames", 1))

    for i in range(frame_count):
        gif.seek(i)
        frame = np.array(gif.convert("RGB"))
        frame = cv2.resize(frame, (512, 512))
        frame = frame.astype(np.float32) / 255.0
        frame = np.expand_dims(frame, 0)

        result = classify_image_array(frame)

        if result == "nsfw":
            nsfw_votes += 1
        else:
            sfw_votes += 1

    return "nsfw" if nsfw_votes > sfw_votes else "sfw"


stop_event = threading.Event()


def process_folder(folder, progress_callback, list_callback):

    if MODEL is None:
        messagebox.showerror("Error", "Model not loaded.")
        return

    sfw_dir = os.path.join(folder, "sfw")
    nsfw_dir = os.path.join(folder, "nsfw")
    dup_dir = os.path.join(folder, "duplicates")

    for d in [sfw_dir, nsfw_dir, dup_dir]:
        os.makedirs(d, exist_ok=True)

    hashes = set()

    image_ext = (".png", ".jpg", ".jpeg", ".webp")
    gif_ext = (".gif",)
    video_ext = (".webm", ".mp4")

    files = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and f.lower().endswith(image_ext + gif_ext + video_ext)
    ]

    total = len(files)

    for index, fname in enumerate(files):

        if stop_event.is_set():
            break

        path = os.path.join(folder, fname)
        list_callback(fname)

        try:
            h = file_hash(path)

            if h in hashes:
                os.rename(path, os.path.join(dup_dir, fname))
                progress_callback(index + 1, total)
                continue

            hashes.add(h)

            lower = fname.lower()

            if lower.endswith(video_ext):
                result = classify_video(path)

            elif lower.endswith(gif_ext):
                result = classify_gif(path)

            else:
                img = Image.open(path).convert("RGB")
                img = img.resize((512, 512))
                img = np.array(img).astype(np.float32) / 255.0
                img = np.expand_dims(img, 0)
                result = classify_image_array(img)

            if result == "nsfw":
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
