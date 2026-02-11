import os
import shutil
import threading
import hashlib
import tkinter as tk
from tkinter import filedialog, scrolledtext
from nudenet import NudeDetector
from PIL import Image, ImageSequence

# Initialize detector
detector = NudeDetector()

seen_hashes = set()

# ULTRA AGGRESSIVE SETTINGS
NSFW_THRESHOLD = 0.20  # very low = more sensitive

# Include all classes (exposed + covered + hentai/sexual)
NSFW_CLASSES = {
    "EXPOSED_ANUS", "EXPOSED_BREAST", "EXPOSED_BUTTOCKS", "EXPOSED_GENITALIA", "EXPOSED_PUBIC_AREA",
    "COVERED_BREAST", "COVERED_GENITALIA", "COVERED_BUTTOCKS", "COVERED_PUBIC_AREA",
    "HENTAI", "SEXY", "PORN"
}

def get_file_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def is_nsfw(detections):
    for d in detections:
        if d["class"] in NSFW_CLASSES and d["score"] > NSFW_THRESHOLD:
            return True
    return False

def detect_image(filepath):
    return detector.detect(filepath)

def detect_gif(filepath):
    try:
        with Image.open(filepath) as img:
            for frame in ImageSequence.Iterator(img):
                frame_path = "temp_frame.jpg"
                frame.convert("RGB").save(frame_path)
                detections = detector.detect(frame_path)
                os.remove(frame_path)
                if is_nsfw(detections):
                    return True
        return False
    except:
        return False

def scan_file(filepath, sfw_dir, nsfw_dir, dup_dir, log):
    file_hash = get_file_hash(filepath)

    # Duplicate detection
    if file_hash in seen_hashes:
        shutil.move(filepath, os.path.join(dup_dir, os.path.basename(filepath)))
        log(f"DUPLICATE → {os.path.basename(filepath)}")
        return
    else:
        seen_hashes.add(file_hash)

    ext = filepath.lower()

    if ext.endswith(".gif"):
        nsfw = detect_gif(filepath)
    else:
        detections = detect_image(filepath)
        nsfw = is_nsfw(detections)

    if nsfw:
        shutil.move(filepath, os.path.join(nsfw_dir, os.path.basename(filepath)))
        log(f"NSFW → {os.path.basename(filepath)}")
    else:
        shutil.move(filepath, os.path.join(sfw_dir, os.path.basename(filepath)))
        log(f"SFW  → {os.path.basename(filepath)}")

def scan_folder(folder, log):
    global seen_hashes
    seen_hashes = set()

    sfw_dir = os.path.join(folder, "SFW")
    nsfw_dir = os.path.join(folder, "NSFW")
    dup_dir = os.path.join(folder, "DUPLICATES")

    os.makedirs(sfw_dir, exist_ok=True)
    os.makedirs(nsfw_dir, exist_ok=True)
    os.makedirs(dup_dir, exist_ok=True)

    for file in os.listdir(folder):
        path = os.path.join(folder, file)

        if path.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")) and os.path.isfile(path):
            try:
                scan_file(path, sfw_dir, nsfw_dir, dup_dir, log)
            except Exception as e:
                log(f"ERROR → {file}: {e}")

    log("✔ Folder scan complete")

def start_scan(log):
    folder = filedialog.askdirectory()
    if not folder:
        return
    threading.Thread(target=scan_folder, args=(folder, log), daemon=True).start()

def main():
    root = tk.Tk()
    root.title("SFW / NSFW + Duplicate Scanner (Ultra Aggressive)")
    root.geometry("650x450")

    log_box = scrolledtext.ScrolledText(root, state="disabled")
    log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def log(msg):
        log_box.configure(state="normal")
        log_box.insert("end", msg + "\n")
        log_box.configure(state="disabled")
        log_box.see("end")

    tk.Button(root, text="Scan Folder", command=lambda: start_scan(log), height=2).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
