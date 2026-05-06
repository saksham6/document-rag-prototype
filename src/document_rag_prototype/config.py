from pathlib import Path

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

CHUNK_SIZE = 180
CHUNK_OVERLAP = 50
TOP_K = 3

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FOLDER = PROJECT_ROOT / "data" / "raw"
UPLOAD_FOLDER = PROJECT_ROOT / "data" / "uploads"

MIN_CHARS_PER_PAGE = 40