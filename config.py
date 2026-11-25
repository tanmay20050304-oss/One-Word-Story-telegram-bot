import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "one_word_story_logo.png"

MIN_PLAYERS = 2
MAX_PLAYERS = 10
MAX_STORY_WORDS = 40
TURN_SECONDS = 30
TWIST_EVERY_WORDS = 5
