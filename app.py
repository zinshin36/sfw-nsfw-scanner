import os
import shutil
import hashlib
import numpy as np
from PIL import Image, ImageSequence

from nudenet import NudeDetector
import deepdanbooru as dd

# ==============================
# SETTINGS
# ==============================

DANBOORU_THRESHOLD = 0.15
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

NSFW_TAGS = {
    "sex", "anal", "oral", "vaginal",
    "cum", "penis", "pussy",
    "nipples", "breasts",
    "spread_legs", "ass",
    "masturbation", "blowjob",
    "handjob", "hentai", "nude"
}

# ==============================
# LOAD MODELS (CORRECT METHOD)
# ==============================

print("Loading DeepDanbooru model...")

project = dd.project.load_project(
    dd.project.get_default_project_path()
)
danbooru_model = dd.project.load_model_from_project(project)

print("Loading NudeNet model...")
nudenet_detector = NudeDetector()

print("Models loaded.")

# ==============================
# HELPERS
# ==============================

def hash_file(path):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def detect_with_danbooru(image):
    try:
        image = image.resize((512, 512))
        arr = np.array(image)
        arr = dd.image.transform_and_pad_image(arr, 512)
        arr = arr[np.newaxis, ...]

        probs = danbooru_model.predict(arr)[0]
        tags = danbooru_model.tags

        strongest = None
        score_max = 0

        for tag, prob in zip(tags, probs):
            if tag in NSFW_TAGS and prob > DANBOORU_THRESHOLD:
                if tag in {"sex", "anal", "penis", "pussy"}:
                    return tag

                if prob > score_max:
                    strongest = tag
                    score_max = prob

        return strongest

    except Exception as e:
        print("Danbooru error:", e)
        return None

def detect_with_nudenet(path):
    try:
        results = nudenet_detector.detect(path)
        if results:
            return results[0]["class"]
        return None
    except:
        return None

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

    # Anime first
    tag = detect_with_danbooru(img)
    if tag:
        return tag

    # Real content backup
    return detect_with_nudenet(path)

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

            if any(x in full_path for x in ["SFW", "NSFW", "DUPLICATES"]):
                continue

            print("Scanning:", file)

            # Duplicate detection
            file_hash = hash_file(full_path)
            if file_hash in seen_hashes:
                shutil.move(full_path, os.path.join(dup_folder, file))
                continue
            seen_hashes.add(file_hash)

            result = detect_image(full_path)

            if result:
                tag_folder = os.path.join(nsfw_folder, result)
                os.makedirs(tag_folder, exist_ok=True)
                shutil.move(full_path, os.path.join(tag_folder, file))
            else:
                shutil.move(full_path, os.path.join(sfw_folder, file))

    print("Scan complete.")

if __name__ == "__main__":
    target = input("Enter folder path to scan: ").strip()
    scan_folder(target)
