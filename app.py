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
    model_path = resource_path("model")

    MODEL = deepdanbooru.project.load_model_from_project(model_path)
    MODEL.compile()

    with open(os.path.join(model_path, "tags.txt"), "r", encoding="utf-8") as f:
        TAGS = [line.strip() for line in f.readlines()]

    logging.info("Model and tags loaded successfully")


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


def analyze_tags(preds):
    tag_dict = dict(zip(TAGS, preds))

    explicit = tag_dict.get("rating:explicit", 0.0)
    questionable = tag_dict.get("rating:questionable", 0.0)

    is_nsfw = explicit > 0.25 or questionable > 0.35

    # Gender detection
    boy_score = max(
        tag_dict.get("1boy", 0.0),
        tag_dict.get("2boys", 0.0),
        tag_dict.get("male_focus", 0.0)
    )

    girl_score = max(
        tag_dict.get("1girl", 0.0),
        tag_dict.get("2girls", 0.0),
        tag_dict.get("female_focus", 0.0)
    )

    gender = None
    if boy_score > 0.3 and boy_score > girl_score:
        gender = "boys"
    elif girl_score > 0.3:
        gender = "girls"

    # Sex detection
    sex_score = max(
        tag_dict.get("sex", 0.0),
        tag_dict.get("intercourse", 0.0),
        tag_dict.get("oral", 0.0),
        tag_dict.get("anal", 0.0),
        tag_dict.get("penetration", 0.0)
    )

    is_sex = sex_score > 0.3

    return is_nsfw, gender, is_sex


def classify_image_array(img_array):
    preds = MODEL.predict(img_array, verbose=0)[0]
    return analyze_tags(preds)


def classify_video(path):
    cap = cv2.VideoCapture(path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    max_frames = int(min(total_frames, fps * 10))
    sample_interval = int(fps)

    nsfw_votes = 0
    boy_votes = 0
    girl_votes = 0
    sex_votes = 0

    for frame_idx in range(0, max_frames, sample_interval):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        img = preprocess_frame(frame)
        is_nsfw, gender, is_sex = classify_image_array(img)

        if is_nsfw:
            nsfw_votes += 1
        if gender == "boys":
            boy_votes += 1
        if gender == "girls":
            girl_votes += 1
        if is_sex:
            sex_votes += 1

    cap.release()

    final_gender = None
    if boy_votes > girl_votes:
        final_gender = "boys"
    elif girl_votes > 0:
        final_gender = "girls"

    return nsfw_votes > 0, final_gender, sex_votes > 0


def classify_gif(path):
    gif = Image.open(path)

    nsfw_votes = 0
    boy_votes = 0
    girl_votes = 0
    sex_votes = 0

    for i in range(min(10, getattr(gif, "n_frames", 1))):
        gif.seek(i)
        frame = np.array(gif.convert("RGB"))
        frame = cv2.resize(frame, (512, 512))
        frame = frame.astype(np.float32) / 255.0
        frame = np.expand_dims(frame, 0)

        is_nsfw, gender, is_sex = classify_image_array(frame)

        if is_nsfw:
            nsfw_votes += 1
        if gender == "boys":
            boy_votes += 1
        if gender == "girls":
            girl_votes += 1
        if is_sex:
            sex_votes += 1

    final_gender = None
    if boy_votes > girl_votes:
        final_gender = "boys"
    elif girl_votes > 0:
        final_gender = "girls"

    return nsfw_votes > 0, final_gender, sex_votes > 0


stop_event = threading.Event()


def process_folder(folder, progress_callback, list_callback):

    sfw_dir = os.path.join(folder, "sfw")
    nsfw_dir = os.path.join(folder, "nsfw")
    dup_dir = os.path.join(folder, "duplicates")

    # NSFW subfolders
    boys_dir = os.path.join(nsfw_dir, "boys")
    girls_dir = os.path.join(nsfw_dir, "girls")

    boys_sex = os.path.join(boys_dir, "sex")
    girls_sex = os.path.join(girls_dir, "sex")

    # Animated versions
    nsfw_anim = os.path.join(nsfw_dir, "animated")
    boys_anim = os.path.join(nsfw_anim, "boys")
    girls_anim = os.path.join(nsfw_anim, "girls")
    boys_anim_sex = os.path.join(boys_anim, "sex")
    girls_anim_sex = os.path.join(girls_anim, "sex")

    for d in [
        sfw_dir, nsfw_dir, dup_dir,
        boys_dir, girls_dir,
        boys_sex, girls_sex,
        nsfw_anim,
        boys_anim, girls_anim,
        boys_anim_sex, girls_anim_sex
    ]:
        os.makedirs(d, exist_ok=True)

    image_ext = (".png", ".jpg", ".jpeg", ".webp")
    gif_ext = (".gif",)
    video_ext = (".webm", ".mp4")

    files = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and f.lower().endswith(image_ext + gif_ext + video_ext)
    ]

    for fname in files:
        path = os.path.join(folder, fname)
        list_callback(fname)

        lower = fname.lower()
        is_animated = lower.endswith(gif_ext + video_ext)

        try:
            if lower.endswith(video_ext):
                is_nsfw, gender, is_sex = classify_video(path)
            elif lower.endswith(gif_ext):
                is_nsfw, gender, is_sex = classify_gif(path)
            else:
                img = Image.open(path).convert("RGB")
                img = img.resize((512, 512))
                img = np.array(img).astype(np.float32) / 255.0
                img = np.expand_dims(img, 0)
                is_nsfw, gender, is_sex = classify_image_array(img)

            if not is_nsfw:
                target = sfw_dir
            else:
                if gender == "boys":
                    if is_animated:
                        target = boys_anim_sex if is_sex else boys_anim
                    else:
                        target = boys_sex if is_sex else boys_dir
                else:
                    if is_animated:
                        target = girls_anim_sex if is_sex else girls_anim
                    else:
                        target = girls_sex if is_sex else girls_dir

            os.rename(path, os.path.join(target, fname))

        except Exception:
            logging.exception("Failed processing %s", fname)

        progress_callback(1, 1)
