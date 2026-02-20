import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import sys
import shutil
import threading
import logging
import traceback
import hashlib
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

import tensorflow as tf
tf.get_logger().setLevel("ERROR")

from tensorflow.keras.models import load_model
import cv2

# =========================
# PATHS
# =========================

if hasattr(sys, "_MEIPASS"):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.abspath(".")

MODEL_PATH = os.path.join(BASE_PATH, "model", "model-resnet_custom_v3.h5")
TAGS_PATH = os.path.join(BASE_PATH, "model", "tags.txt")

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]
VIDEO_EXTENSIONS = [".gif", ".mp4", ".webm"]

# =========================
# LOGGING
# =========================

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "app.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================
# TAG RULES
# =========================

EXPLICIT_TAGS = {
    "sex","explicit","penis","vagina","nipples",
    "breasts","cum","oral","anal","masturbation","nude"
}

FORCE_NSFW_TAGS = {"bulge","bikini","frilled_bikini","swimsuit"}

# =========================
# MODEL
# =========================

model = None
tags = []
model_loaded = False
model_lock = threading.Lock()
seen_hashes = set()

def load_model_once():
    global model, tags, model_loaded

    with model_lock:
        if model_loaded:
            return True
        try:
            model = load_model(MODEL_PATH, compile=False)
            with open(TAGS_PATH, "r", encoding="utf-8") as f:
                tags = [line.strip() for line in f.readlines()]
            model_loaded = True
            return True
        except Exception:
            logging.error(traceback.format_exc())
            messagebox.showerror("Model Error", "Failed to load model.")
            return False

# =========================
# HASH
# =========================

def file_hash(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()

# =========================
# PREDICT
# =========================

def preprocess(frame):
    if frame is None:
        return None
    frame = cv2.resize(frame, (512,512))
    return frame/255.0

def batch_predict(frames):

    processed = []
    for f in frames:
        p = preprocess(f)
        if p is not None:
            processed.append(p)

    if not processed:
        return {}

    preds = model.predict(np.array(processed), verbose=0)

    combined = {}
    for pred in preds:
        for i,val in enumerate(pred):
            combined[tags[i]] = max(combined.get(tags[i],0), float(val))

    return combined

# =========================
# VIDEO SAMPLE
# =========================

def extract_frames(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24

    frames=[]
    for sec in range(10):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(sec*fps))
        ret,frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
    return frames

# =========================
# STRICT CLASSIFIER
# =========================

def is_nsfw(scores):

    for tag in EXPLICIT_TAGS:
        if scores.get(tag,0) >= 0.15:
            return True

    for tag in FORCE_NSFW_TAGS:
        if scores.get(tag,0) >= 0.15:
            return True

    return False


def classify(scores, ext):

    is_video = ext in VIDEO_EXTENSIONS

    furry = scores.get("furry",0)
    boy   = scores.get("1boy",0)
    girl  = scores.get("1girl",0)
    yaoi  = scores.get("yaoi",0)
    lesbian = scores.get("lesbian",0)

    nsfw = is_nsfw(scores)

    # ======================
    # NSFW STRICT
    # ======================
    if nsfw:

        if is_video:
            return "nsfw/animated"

        if furry >= 0.50:
            return "nsfw/furry/sex"

        if yaoi >= 0.40 and boy >= 0.45 and boy > girl + 0.25:
            return "nsfw/boys/yaoi"

        if lesbian >= 0.40 and girl >= 0.45 and girl > boy + 0.25:
            return "nsfw/girls/lesbian"

        if boy >= 0.45 and boy > girl + 0.25:
            return "nsfw/boys/sex"

        if girl >= 0.45 and girl > boy + 0.25:
            return "nsfw/girls/sex"

        return "nsfw/girls/sex"

    # ======================
    # SFW STRICT
    # ======================
    else:

        if is_video:
            return "sfw/animated"

        if furry >= 0.50:
            return "sfw/furry"

        return "sfw"

# =========================
# STRUCTURE
# =========================

def create_structure(base):
    paths = [
        "sfw",
        "sfw/furry",
        "sfw/animated",
        "nsfw/boys/yaoi",
        "nsfw/boys/sex",
        "nsfw/girls/lesbian",
        "nsfw/girls/sex",
        "nsfw/furry/sex",
        "nsfw/animated",
        "duplicates"
    ]
    for p in paths:
        os.makedirs(os.path.join(base,p), exist_ok=True)

# =========================
# SCAN
# =========================

def scan(folder):

    if not load_model_once():
        return

    create_structure(folder)

    files=[]
    skip={"sfw","nsfw","duplicates"}

    for root_dir,dirs,filenames in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in filenames:
            ext=os.path.splitext(f)[1].lower()
            if ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                files.append(os.path.join(root_dir,f))

    total=len(files)
    progress_bar["maximum"]=total

    for i,path in enumerate(files):

        try:
            h=file_hash(path)
            if h in seen_hashes:
                shutil.move(path, os.path.join(folder,"duplicates",os.path.basename(path)))
                continue
            seen_hashes.add(h)

            ext=os.path.splitext(path)[1].lower()

            if ext in VIDEO_EXTENSIONS:
                frames=extract_frames(path)
                scores=batch_predict(frames)
            else:
                bytes=np.fromfile(path,dtype=np.uint8)
                img=cv2.imdecode(bytes,cv2.IMREAD_COLOR)
                scores=batch_predict([img])

            dest=classify(scores,ext)
            target=os.path.join(folder,dest)

            shutil.move(path, os.path.join(target,os.path.basename(path)))

            current_file_label.config(text=os.path.basename(path))
            destination_label.config(text=dest)

        except:
            logging.error(traceback.format_exc())

        progress_bar["value"]=i+1
        progress_label.config(text=f"{i+1}/{total}")

    messagebox.showinfo("Done","Scan Complete")

# =========================
# GUI
# =========================

def start():
    folder=filedialog.askdirectory()
    if folder:
        threading.Thread(target=scan,args=(folder,),daemon=True).start()

root=tk.Tk()
root.title("Media Auto Sorter STRICT")
root.geometry("600x350")

tk.Button(root,text="Select Folder & Scan",command=start).pack(pady=10)

progress_bar=ttk.Progressbar(root,length=500)
progress_bar.pack(pady=10)

progress_label=tk.Label(root,text="0/0")
progress_label.pack()

current_file_label=tk.Label(root,text="")
current_file_label.pack(pady=5)

destination_label=tk.Label(root,text="")
destination_label.pack(pady=5)

root.mainloop()
