import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import sys
import json
import shutil
import logging
import traceback
import threading
import hashlib
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

import tensorflow as tf
tf.get_logger().setLevel("ERROR")

from tensorflow.keras.models import load_model
import cv2

# ==============================
# PATHS
# ==============================

if hasattr(sys, "_MEIPASS"):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.abspath(".")

MODEL_PATH = os.path.join(BASE_PATH, "model", "model-resnet_custom_v3.h5")
TAGS_PATH = os.path.join(BASE_PATH, "model", "tags.txt")
RULES_PATH = os.path.join(BASE_PATH, "config", "tag_rules.json")

IMAGE_EXT = [".png", ".jpg", ".jpeg", ".webp"]
VIDEO_EXT = [".gif", ".mp4", ".webm"]

# ==============================
# LOGGING (Fresh Per Scan)
# ==============================

def setup_logger():
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "scan.log")

    if os.path.exists(log_file):
        os.remove(log_file)

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        force=True
    )

# ==============================
# LOAD RULES
# ==============================

with open(RULES_PATH, "r", encoding="utf-8") as f:
    RULES = json.load(f)

TH = RULES["thresholds"]

# ==============================
# MODEL
# ==============================

model = None
tags = []
model_lock = threading.Lock()
loaded = False

def load_model_once():
    global model, tags, loaded
    with model_lock:
        if loaded:
            return True
        try:
            model = load_model(MODEL_PATH, compile=False)
            with open(TAGS_PATH, "r", encoding="utf-8") as f:
                tags = [line.strip() for line in f.readlines()]
            loaded = True
            return True
        except Exception:
            logging.error(traceback.format_exc())
            messagebox.showerror("Model Error", "Failed to load model.")
            return False

# ==============================
# HASH
# ==============================

seen_hashes = set()

def file_hash(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()

# ==============================
# PREDICT
# ==============================

def preprocess(img):
    if img is None:
        return None
    img = cv2.resize(img, (512, 512))
    return img / 255.0

def predict_frames(frames):
    processed = []
    for f in frames:
        p = preprocess(f)
        if p is not None:
            processed.append(p)

    if not processed:
        return {}

    preds = model.predict(np.array(processed), verbose=0)

    combined = {}
    for pred in preds:
        for i, val in enumerate(pred):
            combined[tags[i]] = max(combined.get(tags[i], 0), float(val))

    return combined

# ==============================
# VIDEO FRAME SAMPLE (10 sec)
# ==============================

def extract_frames(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24

    frames = []
    for sec in range(10):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec * fps))
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
    return frames

# ==============================
# STRICT WEIGHTED CLASSIFIER
# ==============================

def tag_high(scores, tag):
    return scores.get(tag, 0) >= TH["high"]

def tag_medium(scores, tag):
    return scores.get(tag, 0) >= TH["medium"]

def classify(scores, ext):

    logging.info(f"TAGS: {sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]}")

    # ===== RATING FIRST =====
    if tag_medium(scores, RULES["rating"]["explicit"]):
        nsfw = True
    elif tag_high(scores, RULES["rating"]["safe"]):
        nsfw = False
    else:
        nsfw = False

    # ===== FORCE NSFW =====
    for tag in RULES["force_nsfw"]:
        if tag_medium(scores, tag):
            nsfw = True

    # ===== GIRLS EXPLICIT =====
    for tag in RULES["girls_explicit"]:
        if tag_medium(scores, tag):
            return "nsfw/girls/sex"

    # ===== BOYS EXPLICIT =====
    for tag in RULES["boys_explicit"]:
        if tag_medium(scores, tag):
            return "nsfw/boys/sex"

    # ===== FURRY REQUIRE 2 TAGS =====
    furry_hits = sum(1 for t in RULES["force_furry"] if tag_medium(scores, t))
    if furry_hits >= 2:
        return "nsfw/furry/sex" if nsfw else "sfw/furry"

    # ===== YAoi FORCE =====
    for tag in RULES["force_yaoi"]:
        if tag_medium(scores, tag):
            return "nsfw/boys/yaoi"

    # ===== LESBIAN FORCE =====
    for tag in RULES["force_lesbian"]:
        if tag_medium(scores, tag):
            return "nsfw/girls/lesbian"

    # ===== GENDER DOMINANCE =====
    boy = scores.get("1boy", 0)
    girl = scores.get("1girl", 0)

    if boy >= 0.65 and boy > girl + 0.25:
        return "nsfw/boys/sex"

    if girl >= 0.65 and girl > boy + 0.25:
        return "nsfw/girls/sex"

    # ===== VIDEO =====
    if ext in VIDEO_EXT:
        return "nsfw/animated" if nsfw else "sfw/animated"

    # ===== FINAL =====
    if nsfw:
        return "nsfw/girls/sex"

    return "sfw"

# ==============================
# STRUCTURE
# ==============================

def create_structure(base):
    paths = [
        "sfw",
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

# ==============================
# SCAN
# ==============================

def scan(folder):

    setup_logger()
    logging.info("NEW SCAN STARTED")

    if not load_model_once():
        return

    create_structure(folder)

    files = []
    skip = {"sfw", "nsfw", "duplicates"}

    for root_dir, dirs, filenames in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in IMAGE_EXT or ext in VIDEO_EXT:
                files.append(os.path.join(root_dir, f))

    progress_bar["maximum"] = len(files)

    for i, path in enumerate(files):

        try:
            h = file_hash(path)
            if h in seen_hashes:
                shutil.move(path, os.path.join(folder, "duplicates", os.path.basename(path)))
                continue
            seen_hashes.add(h)

            ext = os.path.splitext(path)[1].lower()

            if ext in VIDEO_EXT:
                frames = extract_frames(path)
                scores = predict_frames(frames)
            else:
                img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
                scores = predict_frames([img])

            dest = classify(scores, ext)

            logging.info(f"MOVE: {path} -> {dest}")

            shutil.move(path, os.path.join(folder, dest, os.path.basename(path)))

        except:
            logging.error(traceback.format_exc())

        progress_bar["value"] = i + 1

    logging.info("SCAN COMPLETE")
    messagebox.showinfo("Done", "Scan Complete")

# ==============================
# GUI
# ==============================

def start():
    folder = filedialog.askdirectory()
    if folder:
        threading.Thread(target=scan, args=(folder,), daemon=True).start()

root = tk.Tk()
root.title("Ultra Strict Media Sorter")
root.geometry("500x200")

tk.Button(root, text="Select Folder & Scan", command=start).pack(pady=15)

progress_bar = ttk.Progressbar(root, length=450)
progress_bar.pack(pady=10)

root.mainloop()
