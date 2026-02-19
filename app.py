import os
import shutil
import threading
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

import tensorflow as tf
from tensorflow.keras.models import load_model

# -------------------------------
# CONFIG
# -------------------------------

MODEL_PATH = os.path.join("model", "model-resnet_custom_v3.h5")
TAGS_PATH = os.path.join("model", "tags.txt")

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".gif"]
VIDEO_EXTENSIONS = [".mp4", ".webm"]

FORCE_NSFW_TAGS = {
    "bulge",
    "bikini",
    "frilled_bikini",
    "swimsuit"
}

# -------------------------------
# GLOBALS
# -------------------------------

model = None
tags = []
model_loaded = False


# -------------------------------
# LOAD MODEL (Lazy Load)
# -------------------------------

def load_model_once():
    global model, tags, model_loaded

    if model_loaded:
        return

    print("Loading DeepDanbooru model...")
    model = load_model(MODEL_PATH, compile=False)

    with open(TAGS_PATH, "r", encoding="utf-8") as f:
        tags = [line.strip() for line in f.readlines()]

    model_loaded = True
    print(f"Loaded model with {len(tags)} tags")


# -------------------------------
# IMAGE PREPROCESS
# -------------------------------

def preprocess_image(path):
    from PIL import Image

    image = Image.open(path).convert("RGB")
    image = image.resize((512, 512))
    image = np.array(image) / 255.0
    return np.expand_dims(image, axis=0)


# -------------------------------
# PREDICT
# -------------------------------

def predict(path):
    img = preprocess_image(path)
    predictions = model.predict(img, verbose=0)[0]
    tag_scores = dict(zip(tags, predictions))
    return tag_scores


# -------------------------------
# FOLDER STRUCTURE
# -------------------------------

def create_structure(base):

    structure = {
        "sfw": [
            "furry",
            "animated"
        ],
        "nsfw": {
            "boys": ["yaoi", "sex"],
            "girls": ["lesbian", "sex"],
            "furry": ["sex"],
            "animated": []
        }
    }

    os.makedirs(os.path.join(base, "sfw"), exist_ok=True)
    os.makedirs(os.path.join(base, "nsfw"), exist_ok=True)

    for folder in structure["sfw"]:
        os.makedirs(os.path.join(base, "sfw", folder), exist_ok=True)

    for main_cat, subcats in structure["nsfw"].items():
        os.makedirs(os.path.join(base, "nsfw", main_cat), exist_ok=True)
        for sub in subcats:
            os.makedirs(os.path.join(base, "nsfw", main_cat, sub), exist_ok=True)

    os.makedirs(os.path.join(base, "unsorted"), exist_ok=True)


# -------------------------------
# CLASSIFICATION LOGIC
# -------------------------------

def classify(tag_scores, threshold):

    # Force override tags to NSFW
    for tag in FORCE_NSFW_TAGS:
        if tag_scores.get(tag, 0) >= threshold:
            return os.path.join("nsfw", "girls", "sex")

    is_nsfw = tag_scores.get("explicit", 0) >= threshold
    is_animated = tag_scores.get("animated", 0) >= threshold
    is_furry = tag_scores.get("furry", 0) >= threshold
    is_boys = tag_scores.get("1boy", 0) >= threshold
    is_girls = tag_scores.get("1girl", 0) >= threshold
    is_yaoi = tag_scores.get("yaoi", 0) >= threshold
    is_lesbian = tag_scores.get("lesbian", 0) >= threshold

    if is_nsfw:
        if is_boys:
            if is_yaoi:
                return os.path.join("nsfw", "boys", "yaoi")
            return os.path.join("nsfw", "boys", "sex")

        if is_girls:
            if is_lesbian:
                return os.path.join("nsfw", "girls", "lesbian")
            return os.path.join("nsfw", "girls", "sex")

        if is_furry:
            return os.path.join("nsfw", "furry", "sex")

        if is_animated:
            return os.path.join("nsfw", "animated")

        return os.path.join("nsfw", "girls", "sex")

    # SFW
    if is_furry:
        return os.path.join("sfw", "furry")

    if is_animated:
        return os.path.join("sfw", "animated")

    return "unsorted"


# -------------------------------
# SCAN PROCESS (ERRNO FIXED)
# -------------------------------

def scan_folder(folder, threshold, progress_bar, status_label):

    load_model_once()
    create_structure(folder)

    # Build static file list FIRST (no recursion bugs)
    files = []
    excluded = {
        os.path.join(folder, "sfw"),
        os.path.join(folder, "nsfw"),
        os.path.join(folder, "unsorted")
    }

    for root_dir, dirs, filenames in os.walk(folder):

        dirs[:] = [
            d for d in dirs
            if os.path.join(root_dir, d) not in excluded
        ]

        for file in filenames:
            ext = os.path.splitext(file)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                files.append(os.path.join(root_dir, file))

    total = len(files)

    if total == 0:
        messagebox.showinfo("Done", "No images found.")
        return

    progress_bar["maximum"] = total

    for idx, file_path in enumerate(files):

        try:
            tag_scores = predict(file_path)
            destination = classify(tag_scores, threshold)

            target_dir = os.path.join(folder, destination)
            os.makedirs(target_dir, exist_ok=True)

            shutil.move(file_path, os.path.join(target_dir, os.path.basename(file_path)))

        except Exception as e:
            print(f"ERROR: {e}")

        progress_bar["value"] = idx + 1
        status_label.config(text=f"{idx + 1} / {total}")

    messagebox.showinfo("Done", "Scan complete.")


# -------------------------------
# UI
# -------------------------------

def start_scan():
    folder = filedialog.askdirectory()
    if not folder:
        return

    threshold = threshold_slider.get()

    threading.Thread(
        target=scan_folder,
        args=(folder, threshold, progress_bar, status_label),
        daemon=True
    ).start()


def update_threshold_label(value):
    threshold_value_label.config(text=f"{float(value):.2f}")


root = tk.Tk()
root.title("SFW / NSFW Sorter")
root.geometry("500x300")

threshold_label = tk.Label(root, text="Tag Confidence Threshold")
threshold_label.pack(pady=5)

threshold_slider = tk.Scale(
    root,
    from_=0.1,
    to=1.0,
    resolution=0.01,
    orient=tk.HORIZONTAL,
    length=300,
    command=update_threshold_label
)
threshold_slider.set(0.6)
threshold_slider.pack()

threshold_value_label = tk.Label(root, text="0.60")
threshold_value_label.pack()

start_button = tk.Button(root, text="Select Folder & Scan", command=start_scan)
start_button.pack(pady=10)

progress_bar = ttk.Progressbar(root, length=400)
progress_bar.pack(pady=10)

status_label = tk.Label(root, text="0 / 0")
status_label.pack()

root.mainloop()
