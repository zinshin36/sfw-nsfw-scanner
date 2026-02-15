import os
import sys
import logging
import traceback

# =========================
# Logging Setup
# =========================

LOG_FILE = "app_debug.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.info("=== APPLICATION STARTING ===")

try:
    # Detect base directory (PyInstaller safe)
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    logging.info(f"Base directory: {BASE_DIR}")

    # =========================
    # TensorFlow Import
    # =========================

    import tensorflow as tf
    logging.info(f"TensorFlow version: {tf.__version__}")

    # =========================
    # DeepDanbooru Import
    # =========================

    import deepdanbooru
    logging.info("DeepDanbooru imported successfully")

    logging.info("Application is running correctly.")

except Exception as e:
    logging.error("FATAL ERROR OCCURRED")
    logging.error(traceback.format_exc())
    input("Press ENTER to exit...")
    sys.exit(1)

input("Press ENTER to exit...")
