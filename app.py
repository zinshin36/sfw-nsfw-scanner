import os
import sys
import logging
import threading
import hashlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from PIL import Image
import numpy as np
import tensorflow as tf
import deepdanbooru
import cv2


MODEL = None
TAGS = []
THRESHOLD = 0.30
LOG_FILE = None


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def start_new_log():
    global LOG_FILE
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_FILE = f"sort_log_{timestamp}.txt"
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(message)s",
        force=True
    )


def load_model():
    global MODEL, TAGS
    model_path = resource_path("model")
    MODEL = deepdanbooru.project.load_model_from_project(model_path)
    MODEL.compile()

    with open(os.path.join(model_path, "tags.txt"), "r", encoding="utf-8") as f:
        TAGS = [line.strip() for line in f.readlines()]


load_model()


def preprocess_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.resize(frame, (512, 512))
    frame = frame.astype(np.float32) / 255.0
    return np.expand_dims(frame, 0)


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

    is_yaoi = (
        tag_dict.get("yaoi", 0) > THRESHOLD or
        (gender == "boys" and is_sex and girl_score < 0.1)
    )

    is_lesbian = (
        tag_dict.get("lesbian", 0) > THRESHOLD or
        (gender == "girls" and is_sex and boy_score < 0.1)
    )

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


def classify_image_array(img_array):
    preds = MODEL.predict(img_array, verbose=0)[0]
    return analyze_tags(preds)


def process_file(path):

    img = Image.open(path).convert("RGB")
    img = img.resize((512, 512))
    img = np.array(img).astype(np.float32) / 255.0
    img = np.expand_dims(img, 0)

    return classify_image_array(img)


stop_event = threading.Event()


def process_folder(folder, progress_callback, list_callback):

    start_new_log()

    sfw_dir = os.path.join(folder, "sfw")
    nsfw_dir = os.path.join(folder, "nsfw")

    os.makedirs(sfw_dir, exist_ok=True)
    os.makedirs(nsfw_dir, exist_ok=True)

    image_ext = (".png", ".jpg", ".jpeg", ".webp")

    files = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and f.lower().endswith(image_ext)
    ]

    total = len(files)

    for index, fname in enumerate(files):

        path = os.path.join(folder, fname)
        list_callback(fname)

        try:
            result = process_file(path)

            is_nsfw = result["nsfw"]
            gender = result["gender"]
            is_sex = result["sex"]
            is_furry = result["furry"]
            is_yaoi = result["yaoi"]
            is_lesbian = result["lesbian"]

            if not is_nsfw:
                target = os.path.join(sfw_dir, "furry") if is_furry else sfw_dir
            else:
                if is_furry:
                    base = os.path.join(nsfw_dir, "furry")
                    target = os.path.join(base, "sex") if is_sex else base
                elif gender == "boys":
                    base = os.path.join(nsfw_dir, "boys")
                    if is_yaoi:
                        target = os.path.join(base, "yaoi")
                    elif is_sex:
                        target = os.path.join(base, "sex")
                    else:
                        target = base
                elif gender == "girls":
                    base = os.path.join(nsfw_dir, "girls")
                    if is_lesbian:
                        target = os.path.join(base, "lesbian")
                    elif is_sex:
                        target = os.path.join(base, "sex")
                    else:
                        target = base
                else:
                    target = nsfw_dir

            os.makedirs(target, exist_ok=True)
            os.rename(path, os.path.join(target, fname))

            logging.info(f"""
File: {fname}
NSFW Score: {result["scores"]["nsfw"]}
Sex Score: {result["scores"]["sex"]}
Furry Score: {result["scores"]["furry"]}
Gender: {gender}
Yaoi: {is_yaoi}
Lesbian: {is_lesbian}
Final: {target}
----------------------------------------
""")

        except Exception as e:
            logging.info(f"ERROR processing {fname}: {e}")

        progress_callback(index + 1, total)


class App:

    def __init__(self, root):
        self.root = root
        self.root.title("SFW / NSFW Sorter")
        self.root.geometry("500x400")

        self.folder = tk.StringVar()

        tk.Entry(root, textvariable=self.folder, width=40).pack(pady=5)
        tk.Button(root, text="Browse", command=self.browse).pack()

        tk.Label(root, text="Confidence Threshold").pack(pady=5)

        self.slider = tk.Scale(root, from_=0.1, to=0.8,
                               resolution=0.05,
                               orient="horizontal")
        self.slider.set(0.30)
        self.slider.pack()

        tk.Button(root, text="Start", command=self.start).pack(pady=10)

        self.progress = ttk.Progressbar(root, length=400)
        self.progress.pack(pady=5)

    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.set(folder)

    def start(self):
        global THRESHOLD
        THRESHOLD = self.slider.get()

        folder = self.folder.get()
        if not folder:
            return

        threading.Thread(
            target=process_folder,
            args=(folder, self.update_progress, lambda x: None),
            daemon=True
        ).start()

    def update_progress(self, done, total):
        self.progress["maximum"] = total
        self.progress["value"] = done


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
