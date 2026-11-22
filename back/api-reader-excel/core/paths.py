from pathlib import Path

# Carpeta core/ y archivo .env que vive junto a config.py.
CORE_DIR = Path(__file__).resolve().parent
ENV_FILE = CORE_DIR / ".env"
