import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-fallback")
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "userid")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "password")

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")

    # Max upload size: 32 MB
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024