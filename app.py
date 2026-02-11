import os
import shutil
import hashlib
import numpy as np
import cv2
from PIL import Image, ImageSequence
from nudenet import NudeDetector
import onnxruntime as ort

# ==============================
# SETTINGS
# ==============================

ANIME_THRESHOLD = 0.50  # aggressive
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

MODEL_PATH = "anime_nsfw.onnx"

print("Loading models...")

nudenet_detector = NudeDetector()
anime_session = ort.InferenceSession(MODEL_PATH)

print("Models loaded.")

# ==============================
# HELPERS
# ==============================

def hash_file(path):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def preprocess_anime(img_path):
    img = cv2.imread(img_path)
    img = cv2.resize(img, (224, 224))
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    img = np.expand_dims(img, axis=0)
    return img

def detect_anime_nsfw(path):
    try:
        input_tensor = preprocess_anime(path)
        input_name = anime_session.get_inputs()[0].name
        outputs = anime_session.run(None, {input_name: input_tensor})
        score = outputs[0][0][1]  # NSFW probability
        if score > ANIME_THRESHOLD:
            return "ANIME_NSFW"
        return None
    except:
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
                temp_path = "temp_frame.jpg"
                frame.convert("RGB").save(temp_path)
                tag = detect_anime_nsfw(temp_path)
                os.remove(temp_path)
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

    tag = detect_anime_nsfw(path)
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
