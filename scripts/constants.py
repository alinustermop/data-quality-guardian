import os
from pathlib import Path

# Base Directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed" # Silver Layer

GOLD_DATA_DIR = DATA_DIR / "gold" # Gold Layer
VISUALS_DIR = BASE_DIR / "visuals"

# Database Path
DB_PATH = os.getenv("OLIST_DB_PATH", DATA_DIR / "olist_raw.db")
LOG_FILE = BASE_DIR / "data_guardian.log"

DB_CONN = f"sqlite:///{DB_PATH}"

# List of Olist files
TABLES = {f.stem.replace('olist_', '').replace('_dataset', ''): f.name 
          for f in RAW_DATA_DIR.glob("*.csv")}