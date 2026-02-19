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
# GPU AUTO DETECT
# =========================

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        logging.info("GPU detected and enabled.")
    except:
        pass

# =========================
# BASE PATH
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
# MODEL
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

seen_hashes = set()

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
            logging.info("Model loaded.")
            return True

        except Exception:
            logging.error(traceback.format_exc())
            messagebox.showerror("Model Error", "Failed to load model.")
            return False

# =========================
# DUPLICATE HASH
# =========================

def file_hash(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()

# =========================
# PREDICTION
# =========================

def preprocess_frame(frame):
    if frame is None or frame.size == 0:
        return None
    frame = cv2.resize(frame, (512, 512))
    frame = frame / 255.0
    return frame

def batch_predict(frames):
    processed = []
    for f in frames:
        p = preprocess_frame(f)
        if p is not None:
            processed.append(p)

    if not processed:
        return {}

    batch = np.array(processed)
    preds = model.predict(batch, verbose=0)

    combined = {}
    for prediction in preds:
        for i, val in enumerate(prediction):
            tag = tags[i]
            combined[tag] = max(combined.get(tag, 0), val)

    return combined

# =========================
# VIDEO FRAME SAMPLING
# =========================

def extract_sampled_frames(path):

    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24

    frames = []
    duration_limit = 10
    for second in range(duration_limit):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(second * fps))
        ret, frame = cap.read()
        if ret and frame is not None:
            frames.append(frame)

    cap.release()
    return frames

# =========================
# CLASSIFY
# =========================

def classify(tag_scores, is_video):

    def score(tag):
        return tag_scores.get(tag, 0)

    explicit_score = score("explicit") or score("sex")

    # Force override
    for tag in FORCE_NSFW_TAGS:
        if score(tag) >= 0.35:
            return os.path.join("nsfw", "animated" if is_video else "girls/sex")

    if explicit_score >= 0.30:
        if score("yaoi") >= 0.30:
            return os.path.join("nsfw", "boys", "yaoi")
        if score("lesbian") >= 0.30:
            return os.path.join("nsfw", "girls", "lesbian")
        if score("1boy") >= score("1girl"):
            return os.path.join("nsfw", "boys", "sex")
        return os.path.join("nsfw", "girls", "sex")

    # Videos always go animated branch
    if is_video:
        if explicit_score >= 0.25:
            return os.path.join("nsfw", "animated")
        return os.path.join("sfw", "animated")

    if score("furry") >= 0.35:
        return os.path.join("sfw", "furry")

    if score("animated") >= 0.20:
        return os.path.join("sfw", "animated")

    return os.path.join("sfw", "animated")

# =========================
# STRUCTURE
# =========================

def create_structure(base):

    paths = [
        "sfw/furry",
        "sfw/animated",
        "nsfw/boys/yaoi",
        "nsfw/boys/sex",
        "nsfw/girls/lesbian",
        "nsfw/girls/sex",
        "nsfw/furry/sex",
        "nsfw/animated",
        "duplicates"
    ]

    for p in paths:
        os.makedirs(os.path.join(base, p), exist_ok=True)

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
            hash_value = file_hash(file_path)
            if hash_value in seen_hashes:
                shutil.move(file_path, os.path.join(folder, "duplicates", os.path.basename(file_path)))
                continue
            seen_hashes.add(hash_value)

            ext = os.path.splitext(file_path)[1].lower()
            is_video = ext in VIDEO_EXTENSIONS

            if is_video:
                frames = extract_sampled_frames(file_path)
                tag_scores = batch_predict(frames)
            else:
                frame = cv2.imread(file_path)
                tag_scores = batch_predict([frame])

            destination = classify(tag_scores, is_video)
            target_dir = os.path.join(folder, destination)

            shutil.move(file_path, os.path.join(target_dir, os.path.basename(file_path)))

            logging.info(f"MOVED: {file_path} → {destination}")

            current_file_label.config(text=f"{os.path.basename(file_path)}")
            destination_label.config(text=f"{destination}")

        except Exception:
            logging.error(traceback.format_exc())

        progress_bar["value"] = idx + 1
        progress_label.config(text=f"{idx+1}/{total}")

    logging.info("Scan completed.")
    messagebox.showinfo("Done", "Scan Complete")

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

current_file_label = tk.Label(root, text="")
current_file_label.pack(pady=5)

destination_label = tk.Label(root, text="")
destination_label.pack(pady=5)

root.mainloop()
