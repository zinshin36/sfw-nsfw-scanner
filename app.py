import os
import sys
import shutil
import threading
import logging
import traceback
import hashlib
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

import tensorflow as tf
from tensorflow.keras.models import load_model
import cv2

# =========================
# BASE PATH (PyInstaller Safe)
# =========================

if hasattr(sys, "_MEIPASS"):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.abspath(".")

# =========================
# LOGGING
# =========================

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "app.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("===== APPLICATION STARTED =====")

# =========================
# MODEL PATHS
# =========================

MODEL_PATH = os.path.join(BASE_PATH, "model", "model-resnet_custom_v3.h5")
TAGS_PATH = os.path.join(BASE_PATH, "model", "tags.txt")

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]
VIDEO_EXTENSIONS = [".gif", ".mp4", ".webm"]

FORCE_NSFW_TAGS = {"bulge", "bikini", "frilled_bikini", "swimsuit"}

model = None
tags = []
model_loaded = False
model_lock = threading.Lock()

# =========================
# DUPLICATE HASH STORAGE
# =========================

seen_hashes = set()
hash_lock = threading.Lock()

# =========================
# LOAD MODEL
# =========================

def load_model_once():
    global model, tags, model_loaded

    with model_lock:
        if model_loaded:
            return True

        try:
            logging.info("Loading model...")
            model = load_model(MODEL_PATH, compile=False)

            with open(TAGS_PATH, "r", encoding="utf-8") as f:
                tags = [line.strip() for line in f.readlines()]

            model_loaded = True
            logging.info(f"Model loaded ({len(tags)} tags)")
            return True

        except Exception:
            logging.error(traceback.format_exc())
            messagebox.showerror("Model Error", "Failed to load model. Check logs.")
            return False

# =========================
# HASHING (Duplicate Detection)
# =========================

def file_hash(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()

# =========================
# IMAGE PREDICTION
# =========================

def preprocess_frame(frame):
    frame = cv2.resize(frame, (512, 512))
    frame = frame / 255.0
    return np.expand_dims(frame, axis=0)

def predict_frame(frame):
    processed = preprocess_frame(frame)
    predictions = model.predict(processed, verbose=0)[0]
    return dict(zip(tags, predictions))

# =========================
# VIDEO FRAME EXTRACTION
# =========================

def extract_frames(path):

    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24

    max_frames = int(fps * 10)
    count = 0
    frames = []

    while cap.isOpened() and count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
        count += 1

    cap.release()
    return frames

# =========================
# CLASSIFICATION
# =========================

def classify(tag_scores):

    def score(tag):
        return tag_scores.get(tag, 0)

    # Forced NSFW override
    for tag in FORCE_NSFW_TAGS:
        if score(tag) >= 0.35:
            return os.path.join("nsfw", "girls", "sex")

    if score("yaoi") >= 0.35:
        return os.path.join("nsfw", "boys", "yaoi")

    if score("lesbian") >= 0.35:
        return os.path.join("nsfw", "girls", "lesbian")

    if score("sex") >= 0.35 and score("1boy") >= score("1girl"):
        return os.path.join("nsfw", "boys", "sex")

    if score("sex") >= 0.35:
        return os.path.join("nsfw", "girls", "sex")

    if score("furry") >= 0.35 and score("sex") >= 0.35:
        return os.path.join("nsfw", "furry", "sex")

    if score("animated") >= 0.35 and score("sex") >= 0.35:
        return os.path.join("nsfw", "animated")

    if score("furry") >= 0.35:
        return os.path.join("sfw", "furry")

    if score("animated") >= 0.20:
        return os.path.join("sfw", "animated")

    return os.path.join("sfw", "animated")

# =========================
# STRUCTURE
# =========================

def create_structure(base):

    os.makedirs(os.path.join(base, "sfw", "furry"), exist_ok=True)
    os.makedirs(os.path.join(base, "sfw", "animated"), exist_ok=True)

    os.makedirs(os.path.join(base, "nsfw", "boys", "yaoi"), exist_ok=True)
    os.makedirs(os.path.join(base, "nsfw", "boys", "sex"), exist_ok=True)

    os.makedirs(os.path.join(base, "nsfw", "girls", "lesbian"), exist_ok=True)
    os.makedirs(os.path.join(base, "nsfw", "girls", "sex"), exist_ok=True)

    os.makedirs(os.path.join(base, "nsfw", "furry", "sex"), exist_ok=True)
    os.makedirs(os.path.join(base, "nsfw", "animated"), exist_ok=True)

    os.makedirs(os.path.join(base, "duplicates"), exist_ok=True)

# =========================
# SCAN
# =========================

def scan_folder(folder):

    if not load_model_once():
        return

    create_structure(folder)

    files = []

    skip_dirs = {"sfw", "nsfw", "duplicates"}

    for root_dir, dirs, filenames in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in filenames:
            ext = os.path.splitext(file)[1].lower()
            if ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                files.append(os.path.join(root_dir, file))

    total = len(files)
    progress_bar["maximum"] = total

    for idx, file_path in enumerate(files):

        try:
            # Duplicate detection
            hash_value = file_hash(file_path)

            with hash_lock:
                if hash_value in seen_hashes:
                    dest = os.path.join(folder, "duplicates")
                    shutil.move(file_path, os.path.join(dest, os.path.basename(file_path)))
                    logging.info(f"DUPLICATE: {file_path}")
                    continue
                else:
                    seen_hashes.add(hash_value)

            ext = os.path.splitext(file_path)[1].lower()

            if ext in IMAGE_EXTENSIONS:
                frame = cv2.imread(file_path)
                tag_scores = predict_frame(frame)
            else:
                frames = extract_frames(file_path)
                combined = {}
                for frame in frames:
                    scores = predict_frame(frame)
                    for k, v in scores.items():
                        combined[k] = max(combined.get(k, 0), v)
                tag_scores = combined

            destination = classify(tag_scores)
            target_dir = os.path.join(folder, destination)

            shutil.move(file_path, os.path.join(target_dir, os.path.basename(file_path)))

            logging.info(f"MOVED: {file_path} → {destination}")

            current_file_label.config(text=f"File: {os.path.basename(file_path)}")
            destination_label.config(text=f"Destination: {destination}")

        except Exception:
            logging.error(traceback.format_exc())

        progress_bar["value"] = idx + 1
        progress_label.config(text=f"{idx+1}/{total}")

    logging.info("Scan completed.")
    messagebox.showinfo("Done", "Scan Complete.")

# =========================
# GUI
# =========================

def start_scan():
    folder = filedialog.askdirectory()
    if not folder:
        return
    threading.Thread(target=scan_folder, args=(folder,), daemon=True).start()

root = tk.Tk()
root.title("Media Auto Sorter")
root.geometry("600x350")

tk.Button(root, text="Select Folder & Scan", command=start_scan).pack(pady=10)

progress_bar = ttk.Progressbar(root, length=500)
progress_bar.pack(pady=10)

progress_label = tk.Label(root, text="0/0")
progress_label.pack()

current_file_label = tk.Label(root, text="File:")
current_file_label.pack(pady=5)

destination_label = tk.Label(root, text="Destination:")
destination_label.pack(pady=5)

root.mainloop()
