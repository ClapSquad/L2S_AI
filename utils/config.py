# Defines config variables 

from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads values from .env if present
except Exception:
    pass

# this is so that config.py can be imported from anywhere within the repo
PROJECT_ROOT = Path(__file__).resolve().parents[1]

def get_video_dir() -> Path:
    # Prefer env var; fall back to a local 'assets' dir inside the repo
    env_val = os.getenv("VIDEO_DIR")
    if not env_val:
        raise ValueError("VIDEO_DIR not set in environment variables.")
    return Path(env_val).expanduser() 


def get_howto100m_path() -> Path:
    env_val = os.getenv("PATH_TO_HOWTO100M")
    if not env_val:
        raise ValueError("PATH_TO_HOWTO100M not set in environment variables.")
    return Path(env_val).expanduser()
