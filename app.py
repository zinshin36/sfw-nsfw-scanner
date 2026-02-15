import os
import sys
import logging

# =========================
# Logging Setup
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logging.info("=== APPLICATION STARTING ===")

# Detect base directory (PyInstaller safe)
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logging.info(f"Base directory: {BASE_DIR}")

# =========================
# TensorFlow Import
# =========================

try:
    import tensorflow as tf
    logging.info(f"TensorFlow version: {tf.__version__}")
except Exception as e:
    logging.exception("TensorFlow failed to import")
    sys.exit(1)

# =========================
# DeepDanbooru Import
# =========================

try:
    import deepdanbooru
    logging.info("DeepDanbooru imported successfully")
except Exception as e:
    logging.exception("DeepDanbooru failed to import")
    sys.exit(1)

# =========================
# Basic DeepDanbooru Model Load
# =========================

try:
    model = deepdanbooru.project.load_model_from_project(
        os.path.join(BASE_DIR, "model")
    )
    logging.info("DeepDanbooru model loaded successfully")
except Exception as e:
    logging.warning("Model not loaded (check if model folder exists)")
    model = None

# =========================
# Simple Test Run
# =========================

def main():
    logging.info("Application is running.")

    if model is None:
        logging.info("No model available. Exiting.")
        return

    logging.info("Model ready.")

if __name__ == "__main__":
    main()
