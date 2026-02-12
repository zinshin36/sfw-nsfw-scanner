import os
import shutil
import hashlib
import numpy as np
from PIL import Image, ImageSequence

# IMPORTANT: Do NOT import deepdanbooru normally
from deepdanbooru.project import load_project
from deepdanbooru.model import load_model_from_project
from deepdanbooru.image import transform_and_pad_image

from nudenet import NudeDetector

# =========================
# SETTINGS
# =========================

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

# =========================
# LOAD MODELS
# =========================

print("Loading DeepDanbooru project...")
project_path = os.path.expanduser("~/.deepdanbooru")
project = load_project(project_path)
model = load_model_from_project(project)
print("DeepDanbooru loaded.")

print("Loading NudeNet...")
nudenet_detector = NudeDetector()
print("NudeNet loaded.")

# =========================
# HELPERS
# =========================

def hash_file(path):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def detect_with_danbooru(image):
    image = image.resize((512, 512))
    arr = np.array(image)
    arr = transform_and_pad_image(arr, 512)
    arr = arr[np.newaxis, ...]

    probs = model.predict(arr)[0]
    tags = model.tags

    strongest = None
    best_score = 0

    for tag, prob in zip(tags, probs):
        if tag in NSFW_TAGS and prob > DANBOORU_THRESHOLD:
            if tag in {"sex", "anal", "penis", "pussy"}:
                return tag
            if prob > best_score:
                strongest = tag
                best_score = prob

    return strongest

def detect_with_nudenet(path):
    results = nudenet_detector.detect(path)
    if results:
        return results[0]["class"]
    return None

def detect_gif(path):
    with Image.open(path) as img:
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGB")
            tag = detect_with_danbooru(frame)
            if tag:
                return tag
    return None

def detect_image(path):
    if path.lower().endswith(".gif"):
        tag = detect_gif(path)
        if tag:
            return tag
        return None

    img = Image.open(path).convert("RGB")

    tag = detect_with_danbooru(img)
    if tag:
        return tag

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
