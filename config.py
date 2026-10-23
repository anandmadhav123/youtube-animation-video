import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# API Keys & URLs
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FLOW_PROJECT_URL = os.getenv(
    "FLOW_PROJECT_URL",
    "https://flow.google.com/project/0ebc25ad-8226-4302-a20a-f0728d85d0a2"
)
CHROME_CDP_PORT = int(os.getenv("CHROME_CDP_PORT", "9222"))
CHROME_CDP_URL = f"http://localhost:{CHROME_CDP_PORT}"

# Video Scene Settings
SCENE_DURATION_SECONDS = int(os.getenv("SCENE_DURATION_SECONDS", "8"))
TOTAL_VIDEO_TARGET_MINUTES = float(os.getenv("TOTAL_VIDEO_TARGET_MINUTES", "2.5"))

# Directories
OUTPUT_DIR = BASE_DIR / "output"
CLIPS_DIR = OUTPUT_DIR / "clips"
FINAL_VIDEO_DIR = OUTPUT_DIR / "final"

OUTPUT_DIR.mkdir(exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
FINAL_VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# YouTube Settings
YOUTUBE_CLIENT_SECRET_FILE = os.getenv(
    "YOUTUBE_CLIENT_SECRET_FILE", 
    str(BASE_DIR / "client_secret.json")
)
YOUTUBE_TOKEN_FILE = BASE_DIR / "token.json"
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")  # 'private', 'unlisted', 'public'
