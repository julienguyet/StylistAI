from pathlib import Path
import os
from typing import Optional
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

_client: Optional[AsyncIOMotorClient] = None


def _get_client(mongo_uri: str) -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(mongo_uri)
    return _client


async def get_customer_info(
    customer_id: str,
    mongo_uri: Optional[str] = None,
    db: str = "stylistai",
    collection: str = "customers",
) -> Optional[dict]:
    uri = mongo_uri or os.getenv("MONGO_CONNECTION_STRING")
    if not uri:
        raise RuntimeError("MONGO_CONNECTION_STRING is not set")

    client = _get_client(uri)
    customers_collection = client[db][collection]
    doc = await customers_collection.find_one({"customer_id": customer_id})
    if doc and "_id" in doc:
        doc.pop("_id", None)
    return doc
