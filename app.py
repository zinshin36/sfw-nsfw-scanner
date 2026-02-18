import os
import sys
import shutil
import hashlib
import logging
import threading
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, ttk

import numpy as np
from PIL import Image
import cv2

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import tensorflow as tf
import deepdanbooru as dd

# =============================
# BASE PATH
# =============================

if getattr(sys, "frozen", False):
    base_path = sys._MEIPASS
    base_dir = os.path.dirname(sys.executable)
else:
    base_path = os.path.abspath(".")
    base_dir = base_path

# =============================
# LOG ROOT
# =============================

log_root = os.path.join(base_dir, "logs")
os.makedirs(log_root, exist_ok=True)

# =============================
# LOAD MODEL (STABLE METHOD)
# =============================

model_path = os.path.join(base_path, "model")

if not os.path.exists(os.path.join(model_path, "project.json")):
    raise FileNotFoundError("DeepDanbooru model missing.")

print("Loading DeepDanbooru model...")

model = dd.project.load_model_from_project(model_path)

# MANUAL TAG LOAD (fixes PyInstaller issue)
tags_file = os.path.join(model_path, "tags.txt")
with open(tags_file, "r", encoding="utf-8") as f:
    tags = [line.strip() for line in f.readlines()]

print(f"Loaded model with {len(tags)} tags")

# =============================
# HELPERS
# =============================

def hash_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def is_animated(ext):
    return ext in [".gif", ".mp4", ".webm"]

def get_video_frames(path, max_seconds=5):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    max_frames = int(fps * max_seconds) if fps > 0 else 50
    frames = []
    count = 0
    while count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
        count += 1
    cap.release()
    return frames

def predict_image(image_array):
    image_array = cv2.resize(image_array, (512, 512))
    image_array = image_array.astype(np.float32) / 255.0
    image_array = np.expand_dims(image_array, 0)
    return model.predict(image_array, verbose=0)[0]

# =============================
# CLASSIFICATION
# =============================

def get_rating(scored):
    for tag, score in scored:
        if tag.startswith("rating:"):
            return tag.split(":")[1]
    return "unknown"

def has_tag(scored, keyword, threshold=0.30):
    for tag, score in scored:
        if keyword in tag and score > threshold:
            return True
    return False

def determine_destination(scored, ext):

    rating = get_rating(scored)
    animated = ext in [".gif", ".mp4", ".webm"]

    # SFW
    if rating == "safe":
        if animated:
            return os.path.join("sfw", "animated")
        if has_tag(scored, "furry") or has_tag(scored, "anthro"):
            return os.path.join("sfw", "furry")
        return os.path.join("sfw")

    # NSFW
    if rating in ["explicit", "questionable", "sensitive"]:

        if animated:
            return os.path.join("nsfw", "animated")

        if has_tag(scored, "furry") or has_tag(scored, "anthro"):
            if has_tag(scored, "sex"):
                return os.path.join("nsfw", "furry", "sex")
            return os.path.join("nsfw", "furry")

        if has_tag(scored, "yaoi") or has_tag(scored, "male/male"):
            return os.path.join("nsfw", "boys", "yaoi")

        if has_tag(scored, "1boy") and has_tag(scored, "sex"):
            return os.path.join("nsfw", "boys", "sex")

        if has_tag(scored, "lesbian") or has_tag(scored, "yuri"):
            return os.path.join("nsfw", "girls", "lesbian")

        if has_tag(scored, "1girl") and has_tag(scored, "sex"):
            return os.path.join("nsfw", "girls", "sex")

        return os.path.join("nsfw")

    return "unsorted"

# =============================
# GUI
# =============================

class App:
    def __init__(self, root):
        self.root = root
        root.title("Structured SFW / NSFW Sorter")
        self.folder = tk.StringVar()

        ttk.Button(root, text="Select Folder", command=self.select_folder).pack(pady=5)
        ttk.Entry(root, textvariable=self.folder, width=80).pack()

        self.progress = ttk.Progressbar(root, mode="determinate")
        self.progress.pack(fill="x", padx=5, pady=5)

        ttk.Button(root, text="Start Scan", command=self.start_scan).pack(pady=5)

        self.output = tk.Text(root, height=15)
        self.output.pack(fill="both", expand=True)

    def gui_log(self, msg):
        self.output.insert(tk.END, msg + "\n")
        self.output.see(tk.END)
        self.root.update_idletasks()

    def select_folder(self):
        self.folder.set(filedialog.askdirectory())

    def start_scan(self):
        threading.Thread(target=self.process).start()

    def process(self):
        folder = self.folder.get()
        if not folder:
            return

        scan_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        scan_log_dir = os.path.join(log_root, scan_time)
        os.makedirs(scan_log_dir, exist_ok=True)

        log_file = os.path.join(scan_log_dir, "scan_log.txt")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.FileHandler(log_file, encoding="utf-8")]
        )

        files = []
        for r, _, f in os.walk(folder):
            for file in f:
                ext = os.path.splitext(file)[1].lower()
                if ext in [".png",".jpg",".jpeg",".webp",".gif",".mp4",".webm"]:
                    files.append(os.path.join(r, file))

        self.progress["maximum"] = len(files)
        self.progress["value"] = 0

        seen_hashes = {}

        for i, path in enumerate(files):
            file = os.path.basename(path)
            ext = os.path.splitext(file)[1].lower()

            try:
                file_hash = hash_file(path)
                if file_hash in seen_hashes:
                    dup = os.path.join(folder,"duplicate")
                    os.makedirs(dup, exist_ok=True)
                    shutil.move(path, os.path.join(dup,file))
                    msg = f"{file} → duplicate"
                    logging.info(msg)
                    self.gui_log(msg)
                    continue
                seen_hashes[file_hash] = True

                if is_animated(ext):
                    frames = get_video_frames(path)
                    if not frames:
                        continue
                    preds = [predict_image(f) for f in frames]
                    prediction = np.mean(preds, axis=0)
                else:
                    img = np.array(Image.open(path).convert("RGB"))
                    prediction = predict_image(img)

                scored = list(zip(tags, prediction))
                scored.sort(key=lambda x: x[1], reverse=True)

                relative = determine_destination(scored, ext)
                dest = os.path.join(folder, relative)
                os.makedirs(dest, exist_ok=True)
                shutil.move(path, os.path.join(dest,file))

                msg = f"{file} → {relative}"
                logging.info(msg)
                self.gui_log(msg)

            except Exception as e:
                msg = f"{file} ERROR: {e}"
                logging.error(msg)
                self.gui_log(msg)

            self.progress["value"] = i+1
            self.root.update_idletasks()

        self.gui_log("SCAN COMPLETE")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
