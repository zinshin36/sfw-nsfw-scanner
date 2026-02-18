import os
import sys
import shutil
import hashlib
import logging
import threading
import json
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
# PATH HANDLING (PyInstaller Safe)
# =============================

if getattr(sys, "frozen", False):
    base_path = sys._MEIPASS
    base_dir = os.path.dirname(sys.executable)
else:
    base_path = os.path.abspath(".")
    base_dir = base_path

log_root = os.path.join(base_dir, "logs")
os.makedirs(log_root, exist_ok=True)

# =============================
# LOAD MODEL (Stable Method)
# =============================

model_path = os.path.join(base_path, "model")

if not os.path.exists(os.path.join(model_path, "project.json")):
    raise FileNotFoundError("DeepDanbooru model missing.")

print("Loading DeepDanbooru model...")
model = dd.project.load_model_from_project(model_path)

with open(os.path.join(model_path, "tags.txt"), "r", encoding="utf-8") as f:
    tags = [line.strip() for line in f.readlines()]

print(f"Loaded model with {len(tags)} tags")

# =============================
# HELPER FUNCTIONS
# =============================

def hash_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def is_animated(ext):
    return ext in [".gif", ".mp4", ".webm"]

def get_video_frames(path, max_seconds=4):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    max_frames = int(fps * max_seconds) if fps > 0 else 40
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
# CLASSIFICATION LOGIC
# =============================

SEX_TAGS = ["sex", "intercourse", "penetration", "cum"]

def has_tag(scored, keyword, threshold):
    for tag, score in scored:
        if keyword in tag and score >= threshold:
            return True
    return False

def has_any_tag(scored, keywords, threshold):
    for tag, score in scored:
        if score >= threshold and any(k in tag for k in keywords):
            return True
    return False

def get_rating(scored):
    for tag, score in scored:
        if tag.startswith("rating:"):
            return tag.split(":")[1], score
    return "unknown", 0.0

def determine_destination(scored, ext, threshold):

    rating, rating_score = get_rating(scored)
    animated = is_animated(ext)

    # SFW
    if rating == "safe":
        if animated:
            return "sfw/animated", rating_score
        if has_any_tag(scored, ["furry", "anthro"], threshold):
            return "sfw/furry", rating_score
        return "sfw", rating_score

    # NSFW
    if rating in ["explicit", "questionable", "sensitive"]:

        if animated:
            return "nsfw/animated", rating_score

        # FURRY
        if has_any_tag(scored, ["furry", "anthro"], threshold):
            if has_any_tag(scored, SEX_TAGS, threshold):
                return "nsfw/furry/sex", rating_score
            return "nsfw/furry", rating_score

        # BOYS
        if has_any_tag(scored, ["yaoi", "male/male"], threshold):
            return "nsfw/boys/yaoi", rating_score

        if has_any_tag(scored, ["1boy"], threshold) and has_any_tag(scored, SEX_TAGS, threshold):
            return "nsfw/boys/sex", rating_score

        # GIRLS
        if has_any_tag(scored, ["lesbian", "yuri"], threshold):
            return "nsfw/girls/lesbian", rating_score

        if has_any_tag(scored, ["1girl"], threshold) and has_any_tag(scored, SEX_TAGS, threshold):
            return "nsfw/girls/sex", rating_score

        return "nsfw", rating_score

    return "unsorted", rating_score

# =============================
# PRECREATE FOLDER TREE
# =============================

def create_structure(base_folder):
    structure = [
        "sfw",
        "sfw/furry",
        "sfw/animated",
        "nsfw",
        "nsfw/boys",
        "nsfw/boys/yaoi",
        "nsfw/boys/sex",
        "nsfw/girls",
        "nsfw/girls/lesbian",
        "nsfw/girls/sex",
        "nsfw/furry",
        "nsfw/furry/sex",
        "nsfw/animated",
        "duplicate",
        "unsorted"
    ]
    for path in structure:
        os.makedirs(os.path.join(base_folder, path), exist_ok=True)

# =============================
# GUI
# =============================

class App:
    def __init__(self, root):
        self.root = root
        root.title("Production SFW / NSFW Scanner")

        self.folder = tk.StringVar()
        self.threshold = tk.DoubleVar(value=0.35)

        ttk.Button(root, text="Select Folder", command=self.select_folder).pack(pady=5)
        ttk.Entry(root, textvariable=self.folder, width=80).pack()

        ttk.Label(root, text="Tag Confidence Threshold").pack()
        ttk.Scale(root, from_=0.20, to=0.80, variable=self.threshold, orient="horizontal").pack(fill="x")

        self.conf_label = ttk.Label(root, text="Confidence: -")
        self.conf_label.pack()

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
        threshold = self.threshold.get()

        if not folder:
            return

        create_structure(folder)

        scan_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        scan_log_dir = os.path.join(log_root, scan_time)
        os.makedirs(scan_log_dir, exist_ok=True)

        log_file = os.path.join(scan_log_dir, "scan_log.txt")
        json_file = os.path.join(scan_log_dir, "results.json")

        logger = logging.getLogger(scan_time)
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)

        results = []

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
                    dest = os.path.join(folder, "duplicate", file)
                    shutil.move(path, dest)
                    logger.info(f"{file} → duplicate")
                    self.gui_log(f"{file} → duplicate")
                    continue
                seen_hashes[file_hash] = True

                if is_animated(ext):
                    frames = get_video_frames(path)
                    preds = [predict_image(f) for f in frames]
                    prediction = np.mean(preds, axis=0)
                else:
                    img = np.array(Image.open(path).convert("RGB"))
                    prediction = predict_image(img)

                scored = list(zip(tags, prediction))
                scored.sort(key=lambda x: x[1], reverse=True)

                relative, confidence = determine_destination(scored, ext, threshold)
                dest_folder = os.path.join(folder, relative)
                dest_path = os.path.join(dest_folder, file)

                shutil.move(path, dest_path)

                results.append({
                    "file": file,
                    "destination": relative,
                    "confidence": float(confidence)
                })

                logger.info(f"{file} → {relative} ({confidence:.3f})")
                self.gui_log(f"{file} → {relative}")
                self.conf_label.config(text=f"{confidence:.2f}")

            except Exception as e:
                logger.error(f"{file} ERROR: {e}")
                self.gui_log(f"{file} ERROR")

            self.progress["value"] = i+1
            self.root.update_idletasks()

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)

        logger.info("SCAN COMPLETE")
        self.gui_log("SCAN COMPLETE")
