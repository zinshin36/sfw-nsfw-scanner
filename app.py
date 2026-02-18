import os
import sys
import shutil
import hashlib
import logging
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, ttk

import numpy as np
from PIL import Image
import cv2
import tensorflow as tf
import deepdanbooru as dd

# FORCE CPU ONLY
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# =============================
# LOGGING (ALWAYS NEW FILE)
# =============================

if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
    log_dir = os.path.join(base_dir, "logs")
else:
    log_dir = "logs"

os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logging.info("Application started")

# =============================
# LOAD MODEL
# =============================

logging.info("Loading DeepDanbooru model...")

if getattr(sys, "frozen", False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

model_path = os.path.join(base_path, "model")

if not os.path.exists(os.path.join(model_path, "project.json")):
    logging.error(f"Model not found at {model_path}")
    raise FileNotFoundError("DeepDanbooru model files missing.")

model = dd.project.load_model_from_project(model_path)

logging.info("Model loaded successfully")

# =============================
# HELPERS
# =============================

def hash_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def is_animated(ext):
    return ext in [".gif", ".mp4", ".webm"]

def get_video_frame(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    max_frames = int(fps * 10) if fps > 0 else 100
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
    return model.predict(image_array)[0]

# =============================
# GUI
# =============================

class App:
    def __init__(self, root):
        self.root = root
        root.title("SFW / NSFW Sorter")

        self.folder = tk.StringVar()
        self.threshold = tk.DoubleVar(value=0.75)

        ttk.Button(root, text="Select Folder", command=self.select_folder).pack(pady=5)
        ttk.Entry(root, textvariable=self.folder, width=60).pack()

        ttk.Label(root, text="Confidence Threshold").pack()
        ttk.Scale(root, from_=0.5, to=0.99, variable=self.threshold, orient="horizontal").pack(fill="x")

        self.conf_label = ttk.Label(root, text="Confidence: -")
        self.conf_label.pack()

        ttk.Button(root, text="Start", command=self.process).pack(pady=10)

    def select_folder(self):
        self.folder.set(filedialog.askdirectory())

    def process(self):
        folder = self.folder.get()
        threshold = self.threshold.get()

        logging.info(f"Scanning folder: {folder}")
        logging.info(f"Threshold: {threshold}")

        seen_hashes = {}

        for root_dir, _, files in os.walk(folder):
            for file in files:
                path = os.path.join(root_dir, file)
                ext = os.path.splitext(file)[1].lower()

                if ext not in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".webm"]:
                    continue

                file_hash = hash_file(path)
                if file_hash in seen_hashes:
                    dest = os.path.join(folder, "duplicate")
                    os.makedirs(dest, exist_ok=True)
                    shutil.move(path, os.path.join(dest, file))
                    logging.info(f"{file} → duplicate")
                    continue

                seen_hashes[file_hash] = True

                try:
                    if is_animated(ext):
                        frames = get_video_frame(path)
                        if not frames:
                            continue
                        preds = [predict_image(f) for f in frames]
                        prediction = np.mean(preds, axis=0)
                    else:
                        img = np.array(Image.open(path).convert("RGB"))
                        prediction = predict_image(img)
                except Exception as e:
                    logging.error(f"Prediction failed for {file}: {e}")
                    continue

                tags = model.tags
                scored = list(zip(tags, prediction))
                scored.sort(key=lambda x: x[1], reverse=True)

                top_tag, top_score = scored[0]
                self.conf_label.config(text=f"Confidence: {top_score:.2f}")
                self.root.update()

                logging.info(f"{file} → {top_tag} ({top_score:.3f})")

                base_folder = "sfw"
                if top_score >= threshold and "rating:explicit" in [t[0] for t in scored[:5]]:
                    base_folder = "nsfw"

                dest = os.path.join(folder, base_folder)
                os.makedirs(dest, exist_ok=True)
                shutil.move(path, os.path.join(dest, file))

        logging.info("Scan complete")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
