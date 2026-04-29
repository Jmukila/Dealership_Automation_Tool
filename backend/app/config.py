from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"
ASSETS_DIR = BASE_DIR / "assets"


class Config:
    SECRET_KEY = "assignment-dev-key"
    DATABASE_PATH = BACKEND_DIR / "app.db"
    UPLOAD_FOLDER = BACKEND_DIR / "uploads"
    GENERATED_FOLDER = BACKEND_DIR / "generated"
    ASSETS_DIR = ASSETS_DIR
