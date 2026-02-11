import os
import shutil
import hashlib
import numpy as np
from PIL import Image, ImageSequence

from nudenet import NudeDetector
import deepdanbooru as dd
import tensorflow as tf

# ==============================
# SETTINGS
# ==============================

DANBOORU_THRESHOLD = 0.12  # aggressive
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

NSFW_DANBOORU_TAGS = {
    "sex", "anal", "oral", "vaginal",
    "cum", "ejaculation",
    "penis", "pussy", "nipples",
    "breasts", "ass", "anus",
    "spread_legs", "masturbation",
    "fingering", "handjob", "blowjob",
    "bdsm", "hentai", "nude",
    "no_bra", "no_panties",
    "cameltoe"
}

# ==============================
# LOAD MODELS (LOAD ONCE)
# ==============================

print("Loading models...")

danbooru_model = dd.project.load_model_from_project(
    dd.project.load_project("deepdanbooru-project")
)

nudenet_detector = NudeDetector()

print("Models loaded.")

# ==============================
# HELPERS
# ==============================

def hash_file(path):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def resize_image(image):
    image = image.resize((512, 512))
    return image

# ==============================
# DANBOORU DETECTION (PRIMARY)
# ==============================

def detect_with_danbooru(image):
    try:
        image = resize_image(image)
        arr = np.array(image)
        arr = dd.image.transform_and_pad_image(arr, 512)
        arr = arr[np.newaxis, ...]

        probs = danbooru_model.predict(arr, verbose=0)[0]
        tags = danbooru_model.tags

        strongest = None
        score_max = 0

        for tag, prob in zip(tags, probs):
            if tag in NSFW_DANBOORU_TAGS and prob > DANBOORU_THRESHOLD:
                if tag in {"sex", "anal", "oral", "penis", "pussy"}:
                    return tag

                if prob > score_max:
                    strongest = tag
                    score_max = prob

        return strongest

    except:
        return None

# ==============================
# NUDENET BACKUP
# ==============================

def detect_with_nudenet(path):
    try:
        results = nudenet_detector.detect(path)
        if results:
            return results[0]["class"]
        return None
    except:
        return None

# ==============================
# GIF HANDLING
# ==============================

def detect_gif(path):
    try:
        with Image.open(path) as img:
            for frame in ImageSequence.Iterator(img):
                frame = frame.convert("RGB")
                tag = detect_with_danbooru(frame)
                if tag:
                    return tag
        return None
    except:
        return None

# ==============================
# MAIN DETECTION
# ==============================

def detect_image(path):

    if path.lower().endswith(".gif"):
        tag = detect_gif(path)
        if tag:
            return tag
        return None

    try:
        img = Image.open(path).convert("RGB")
    except:
        return None

    # 1️⃣ DeepDanbooru FIRST
    tag = detect_with_danbooru(img)
    if tag:
        return tag

    # 2️⃣ NudeNet backup
    return detect_with_nudenet(path)

# ==============================
# SCAN FOLDER
# ==============================

def scan_folder(folder):

    sfw_folder = os.path.join(folder, "SFW")
    nsfw_folder = os.path.join(folder, "NSFW")
    dup_folder = os.path.join(folder, "DUPLICATES")

    os.makedirs(sfw_folder, exist_ok=True)
    os.makedirs(nsfw_folder, exist_ok=True)
    os.makedirs(dup_folder, exist_ok=True)

    seen_hashes = set()

    for root, _, files in os.walk(folder):
        for file in files:

            if not file.lower().endswith(IMAGE_EXTENSIONS):
                continue

            full_path = os.path.join(root, file)

            if "SFW" in full_path or "NSFW" in full_path or "DUPLICATES" in full_path:
                continue

            print("Scanning:", file)

            # Duplicate detection
            file_hash = hash_file(full_path)
            if file_hash in seen_hashes:
                shutil.move(full_path, os.path.join(dup_folder, file))
                continue
            seen_hashes.add(file_hash)

            # Detection
            result = detect_image(full_path)

            if result:
                tag_folder = os.path.join(nsfw_folder, result)
                os.makedirs(tag_folder, exist_ok=True)
                shutil.move(full_path, os.path.join(tag_folder, file))
            else:
                shutil.move(full_path, os.path.join(sfw_folder, file))

    print("Scan complete.")

# ==============================
# ENTRY
# ==============================

if __name__ == "__main__":
    target = input("Enter folder path to scan: ").strip()
    scan_folder(target)
