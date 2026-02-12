import os
import traceback
import datetime

# =========================
# LOGGING BOOTSTRAP (RUNS FIRST)
# =========================

TEMP_DIR = "temp"
LOG_FILE = os.path.join(TEMP_DIR, "log.txt")

os.makedirs(TEMP_DIR, exist_ok=True)

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full = f"[{timestamp}] {msg}"
    print(full)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full + "\n")

def log_exception(e):
    log("===== EXCEPTION =====")
    log(str(e))
    log(traceback.format_exc())

log("===== PROGRAM START =====")

# =========================
# SAFE IMPORTS (LOG FAILURES)
# =========================

try:
    import shutil
    import hashlib
    import numpy as np
    from PIL import Image, ImageSequence

    from deepdanbooru.project import load_project
    from deepdanbooru.model import load_model_from_project
    from deepdanbooru.image import transform_and_pad_image

    from nudenet import NudeDetector

    log("All imports loaded successfully.")

except Exception as e:
    log_exception(e)
    input("Import crash. Check temp/log.txt")
    raise

# =========================
# SETTINGS
# =========================

DANBOORU_THRESHOLD = 0.15
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

NSFW_TAGS = {
    "sex","anal","oral","vaginal",
    "cum","penis","pussy",
    "nipples","breasts",
    "spread_legs","ass",
    "masturbation","blowjob",
    "handjob","hentai","nude"
}

# =========================
# LOAD MODELS
# =========================

try:
    log("Loading DeepDanbooru...")
    project_path = os.path.expanduser("~/.deepdanbooru")
    project = load_project(project_path)
    model = load_model_from_project(project)
    log("DeepDanbooru loaded.")
except Exception as e:
    log_exception(e)
    input("DeepDanbooru failed. Check log.")
    raise

try:
    log("Loading NudeNet...")
    nudenet_detector = NudeDetector()
    log("NudeNet loaded.")
except Exception as e:
    log_exception(e)
    input("NudeNet failed. Check log.")
    raise

# =========================
# HELPERS
# =========================

def hash_file(path):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def detect_with_danbooru(image):
    try:
        image = image.resize((512,512))
        arr = np.array(image)
        arr = transform_and_pad_image(arr,512)
        arr = arr[np.newaxis,...]

        probs = model.predict(arr)[0]
        tags = model.tags

        strongest = None
        best_score = 0

        for tag,prob in zip(tags,probs):
            if tag in NSFW_TAGS and prob > DANBOORU_THRESHOLD:
                if tag in {"sex","anal","penis","pussy"}:
                    return tag
                if prob > best_score:
                    strongest = tag
                    best_score = prob

        return strongest

    except Exception as e:
        log_exception(e)
        return None

def detect_with_nudenet(path):
    try:
        results = nudenet_detector.detect(path)
        if results:
            return results[0]["class"]
        return None
    except Exception as e:
        log_exception(e)
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
    except Exception as e:
        log_exception(e)
        return None

def detect_image(path):
    try:
        if path.lower().endswith(".gif"):
            return detect_gif(path)

        img = Image.open(path).convert("RGB")

        tag = detect_with_danbooru(img)
        if tag:
            return tag

        return detect_with_nudenet(path)

    except Exception as e:
        log_exception(e)
        return None

# =========================
# SCANNER
# =========================

def scan_folder(folder):

    try:
        sfw = os.path.join(folder,"SFW")
        nsfw = os.path.join(folder,"NSFW")
        dup = os.path.join(folder,"DUPLICATES")

        os.makedirs(sfw,exist_ok=True)
        os.makedirs(nsfw,exist_ok=True)
        os.makedirs(dup,exist_ok=True)

        seen = set()

        for root,_,files in os.walk(folder):
            for file in files:

                if not file.lower().endswith(IMAGE_EXTENSIONS):
                    continue

                full = os.path.join(root,file)

                if any(x in full for x in ["SFW","NSFW","DUPLICATES"]):
                    continue

                log(f"Scanning {file}")

                h = hash_file(full)
                if h in seen:
                    shutil.move(full, os.path.join(dup,file))
                    log(f"Duplicate -> {file}")
                    continue

                seen.add(h)

                result = detect_image(full)

                if result:
                    tag_folder = os.path.join(nsfw,result)
                    os.makedirs(tag_folder,exist_ok=True)
                    shutil.move(full, os.path.join(tag_folder,file))
                    log(f"NSFW {result} -> {file}")
                else:
                    shutil.move(full, os.path.join(sfw,file))
                    log(f"SFW -> {file}")

        log("Scan complete.")

    except Exception as e:
        log_exception(e)
        raise

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    try:
        folder = input("Folder to scan: ").strip()
        scan_folder(folder)
    except Exception as e:
        log_exception(e)
        input("Fatal crash. Check temp/log.txt")
