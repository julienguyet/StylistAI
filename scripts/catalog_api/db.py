import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MONGO_URI = os.getenv("MONGO_CONNECTION_STRING")
DB_NAME = os.getenv("MONGO_DB", "stylistai")
IMAGES_DIR = Path(os.getenv("IMAGES_DIR", "/data/images"))


def make_client() -> AsyncIOMotorClient:
    if not MONGO_URI:
        raise RuntimeError("MONGO_CONNECTION_STRING is not set")
    return AsyncIOMotorClient(MONGO_URI)


def normalize_article_id(article_id) -> int:
    """Article IDs arrive zero-padded ('0108775015'), bare ('108775015') or as ints.

    Mongo stores them as ints, so everything funnels through int().
    """
    try:
        return int(str(article_id).strip())
    except (TypeError, ValueError):
        raise ValueError(f"Invalid article_id: {article_id!r}")


def image_path(article_id: int) -> Path:
    padded = f"{article_id:010d}"
    return IMAGES_DIR / padded[:3] / f"{padded}.jpg"
