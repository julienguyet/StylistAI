from contextlib import asynccontextmanager
from pathlib import Path
import os
from typing import Optional
import anyio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from customer_info import get_customer_info
from recommandation import RecommendationEngine, recommend_async

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MODEL_PATH = os.getenv("MODEL_PATH", "/data/models/mlruns_outputs/fc49224e1ba24094ae6b606de6a86b17/saved_model")
ARTICLES_CSV_PATH = os.getenv("ARTICLES_CSV_PATH", "/data/processed/articles_df.csv")
SCALER_PATH = os.getenv("SCALER_PATH", "/data/scalers/age_scaler_portugal.pkl")
MONGO_URI = os.getenv("MONGO_CONNECTION_STRING")


class RecommendRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID used in MongoDB")
    top_k: int = Field(5, ge=1, le=100)
    exclude_purchased: bool = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not MONGO_URI:
        raise RuntimeError("MONGO_CONNECTION_STRING is not set")
    # Load the model + artifacts off the event loop.
    engine = await anyio.to_thread.run_sync(
        RecommendationEngine,
        MODEL_PATH,
        ARTICLES_CSV_PATH,
        SCALER_PATH,
    )
    app.state.engine = engine
    app.state.mongo_uri = MONGO_URI
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/invoke")
async def recommend_products(payload: RecommendRequest):
    customer_info = await get_customer_info(
        customer_id=payload.customer_id,
        mongo_uri=app.state.mongo_uri,
    )
    if not customer_info:
        raise HTTPException(status_code=404, detail="Customer not found")

    recs = await recommend_async(
        app.state.engine,
        customer_info,
        top_k=payload.top_k,
        exclude_purchased=payload.exclude_purchased,
    )

    return recs.to_dict(orient="records")

@app.get("/health")
async def health():
    return {"status": "ok"}
