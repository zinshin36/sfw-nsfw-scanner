import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext
import nudenet

model = nudenet.NudeDetector()

def is_nsfw(detections):
    for d in detections:
        if d["score"] > 0.6:
            return True
    return False

def scan_file(filepath, sfw_dir, nsfw_dir, log):
    detections = model.detect(filepath)

    if is_nsfw(detections):
        shutil.move(filepath, os.path.join(nsfw_dir, os.path.basename(filepath)))
        log(f"NSFW → {os.path.basename(filepath)}")
    else:
        shutil.move(filepath, os.path.join(sfw_dir, os.path.basename(filepath)))
        log(f"SFW  → {os.path.basename(filepath)}")

def scan_folder(folder, log):
    sfw_dir = os.path.join(folder, "SFW")
    nsfw_dir = os.path.join(folder, "NSFW")

    os.makedirs(sfw_dir, exist_ok=True)
    os.makedirs(nsfw_dir, exist_ok=True)

    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        if path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and os.path.isfile(path):
            try:
                scan_file(path, sfw_dir, nsfw_dir, log)
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
    root.title("SFW / NSFW Scanner")
    root.geometry("500x400")

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
