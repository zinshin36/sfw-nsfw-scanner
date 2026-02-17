import os
import sys
import hashlib
import threading
from datetime import datetime
import logging

import tkinter as tk
from tkinter import filedialog, ttk

import numpy as np
from PIL import Image
import cv2

import tensorflow as tf
import deepdanbooru


# ---------------- RESOURCE PATH ----------------

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)


# ---------------- GLOBALS ----------------

MODEL = None
TAGS = []
THRESHOLD = 0.30
stop_event = threading.Event()
hash_cache = set()


# ---------------- LOGGING ----------------

def create_log_file():
    exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(exe_dir, f"sort_log_{timestamp}.txt")

    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(logging.INFO)

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    logging.info("==== NEW RUN STARTED ====")
    logging.info(f"Threshold: {THRESHOLD}")
    logging.info("-------------------------")

    return log_path


# ---------------- MODEL LOADING ----------------

def load_model():
    global MODEL, TAGS

    model_path = resource_path("model")

    MODEL = deepdanbooru.project.load_model_from_project(model_path)
    MODEL.compile()

    with open(os.path.join(model_path, "tags.txt"), "r", encoding="utf-8") as f:
        TAGS = [line.strip() for line in f.readlines()]


load_model()


# ---------------- HASH ----------------

def file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------- FRAME PREPROCESS ----------------

def preprocess_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.resize(frame, (512, 512))
    frame = frame.astype(np.float32) / 255.0
    return np.expand_dims(frame, 0)


# ---------------- TAG ANALYSIS ----------------

def analyze_tags(preds):

    tag_dict = dict(zip(TAGS, preds))

    explicit = tag_dict.get("rating:explicit", 0)
    questionable = tag_dict.get("rating:questionable", 0)
    nsfw_score = max(explicit, questionable)
    is_nsfw = nsfw_score > THRESHOLD

    boy_score = max(tag_dict.get("1boy", 0), tag_dict.get("2boys", 0))
    girl_score = max(tag_dict.get("1girl", 0), tag_dict.get("2girls", 0))

    gender = None
    if boy_score > THRESHOLD and boy_score > girl_score:
        gender = "boys"
    elif girl_score > THRESHOLD:
        gender = "girls"

    sex_score = max(
        tag_dict.get("sex", 0),
        tag_dict.get("intercourse", 0),
        tag_dict.get("oral", 0),
        tag_dict.get("anal", 0)
    )
    is_sex = sex_score > THRESHOLD

    furry_score = max(
        tag_dict.get("furry", 0),
        tag_dict.get("animal_ears", 0),
        tag_dict.get("cat_ears", 0),
        tag_dict.get("fox_ears", 0),
        tag_dict.get("wolf_ears", 0),
        tag_dict.get("animal_nose", 0),
        tag_dict.get("tail", 0)
    )
    is_furry = furry_score > THRESHOLD

    is_yaoi = tag_dict.get("yaoi", 0) > THRESHOLD
    is_lesbian = tag_dict.get("lesbian", 0) > THRESHOLD

    return {
        "nsfw": is_nsfw,
        "gender": gender,
        "sex": is_sex,
        "furry": is_furry,
        "yaoi": is_yaoi,
        "lesbian": is_lesbian,
        "scores": {
            "nsfw": nsfw_score,
            "sex": sex_score,
            "furry": furry_score
        }
    }


# ---------------- CLASSIFIERS ----------------

def classify_image(path):
    img = Image.open(path).convert("RGB")
    img = img.resize((512, 512))
    img = np.array(img).astype(np.float32) / 255.0
    img = np.expand_dims(img, 0)
    preds = MODEL.predict(img, verbose=0)[0]
    return analyze_tags(preds)


def classify_gif(path):
    gif = Image.open(path)
    gif.seek(0)
    frame = preprocess_frame(np.array(gif.convert("RGB")))
    preds = MODEL.predict(frame, verbose=0)[0]
    return analyze_tags(preds)


def classify_video(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return None

    frame = preprocess_frame(frame)
    preds = MODEL.predict(frame, verbose=0)[0]
    return analyze_tags(preds)


# ---------------- PROCESS ----------------

def process_folder(folder, progress_cb, confidence_cb):

    log_path = create_log_file()

    files = [f for f in os.listdir(folder)
             if os.path.isfile(os.path.join(folder, f))]

    total = len(files)

    for index, fname in enumerate(files):

        if stop_event.is_set():
            break

        path = os.path.join(folder, fname)

        file_md5 = file_hash(path)
        if file_md5 in hash_cache:
            dup_dir = os.path.join(folder, "duplicates")
            os.makedirs(dup_dir, exist_ok=True)
            os.rename(path, os.path.join(dup_dir, fname))
            continue
        hash_cache.add(file_md5)

        lower = fname.lower()

        if lower.endswith((".gif",)):
            result = classify_gif(path)
            animated = True
        elif lower.endswith((".mp4", ".webm")):
            result = classify_video(path)
            animated = True
        elif lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
            result = classify_image(path)
            animated = False
        else:
            continue

        if not result:
            continue

        confidence_cb(result["scores"]["nsfw"],
                      result["scores"]["sex"],
                      result["scores"]["furry"])

        base = os.path.join(folder, "nsfw" if result["nsfw"] else "sfw")

        if result["furry"]:
            base = os.path.join(base, "furry")
            if result["sex"] and result["nsfw"]:
                base = os.path.join(base, "sex")

        elif result["nsfw"] and result["gender"] == "boys":
            base = os.path.join(base, "boys")
            if result["yaoi"]:
                base = os.path.join(base, "yaoi")
            elif result["sex"]:
                base = os.path.join(base, "sex")

        elif result["nsfw"] and result["gender"] == "girls":
            base = os.path.join(base, "girls")
            if result["lesbian"]:
                base = os.path.join(base, "lesbian")
            elif result["sex"]:
                base = os.path.join(base, "sex")

        if animated:
            base = os.path.join(base, "animated")

        os.makedirs(base, exist_ok=True)
        os.rename(path, os.path.join(base, fname))

        logging.info(f"""
File: {fname}
NSFW: {result['scores']['nsfw']}
Sex: {result['scores']['sex']}
Furry: {result['scores']['furry']}
Gender: {result['gender']}
Yaoi: {result['yaoi']}
Lesbian: {result['lesbian']}
Final Folder: {base}
-------------------------------------
""")

        progress_cb(index + 1, total)

    logging.info("==== RUN COMPLETE ====")
    print(f"Log saved to: {log_path}")


# ---------------- GUI ----------------

class App:

    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Sorter")
        self.root.geometry("600x420")

        self.folder = tk.StringVar()

        tk.Entry(root, textvariable=self.folder, width=50).pack(pady=5)
        tk.Button(root, text="Browse", command=self.browse).pack()

        tk.Label(root, text="Confidence Threshold").pack()
        self.slider = tk.Scale(root, from_=0.1, to=0.8,
                               resolution=0.05,
                               orient="horizontal")
        self.slider.set(0.30)
        self.slider.pack()

        self.conf_label = tk.Label(root, text="Confidence: ---")
        self.conf_label.pack(pady=10)

        self.progress = ttk.Progressbar(root, length=500)
        self.progress.pack(pady=10)

        tk.Button(root, text="Start", command=self.start).pack(pady=10)

    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.set(folder)

    def start(self):
        global THRESHOLD
        THRESHOLD = self.slider.get()

        threading.Thread(
            target=process_folder,
            args=(self.folder.get(),
                  self.update_progress,
                  self.update_confidence),
            daemon=True
        ).start()

    def update_progress(self, done, total):
        self.progress["maximum"] = total
        self.progress["value"] = done

    def update_confidence(self, nsfw, sex, furry):
        self.conf_label.config(
            text=f"NSFW: {nsfw:.2f} | Sex: {sex:.2f} | Furry: {furry:.2f}"
        )


# ---------------- MAIN ----------------

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
