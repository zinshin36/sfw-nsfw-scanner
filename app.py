import os
import sys
import logging
from pathlib import Path

# =========================
# FORCE SAFE TENSORFLOW MODE
# =========================
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# =========================
# SETUP LOGGING IMMEDIATELY
# =========================
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
LOG_FILE = BASE_DIR / "app.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("app")

logger.info("=== APPLICATION STARTING ===")
logger.info(f"Base directory: {BASE_DIR}")

# =========================
# SAFE IMPORTS (AFTER LOG)
# =========================
try:
    import tensorflow as tf
    logger.info(f"TensorFlow version: {tf.__version__}")
except Exception as e:
    logger.exception("TensorFlow failed to import")
    raise

try:
    from deepdanbooru import DeepDanbooru
    logger.info("DeepDanbooru imported successfully")
except Exception as e:
    logger.exception("DeepDanbooru failed to import")
    raise

try:
    from nudenet import NudeClassifier
    logger.info("NudeNet imported successfully")
except Exception as e:
    logger.exception("NudeNet failed to import")
    raise

# =========================
# GUI (MINIMAL TEST WINDOW)
# =========================
import tkinter as tk
from tkinter import messagebox

def main():
    logger.info("Launching GUI")

    root = tk.Tk()
    root.title("NSFW Scanner")
    root.geometry("400x200")

    label = tk.Label(root, text="App started successfully", font=("Arial", 12))
    label.pack(pady=40)

    def quit_app():
        logger.info("Application closed by user")
        root.destroy()

    button = tk.Button(root, text="Exit", command=quit_app)
    button.pack()

    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Fatal error in main loop")
        raise
