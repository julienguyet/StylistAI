from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional
import re

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from db import DB_NAME, image_path, make_client, normalize_article_id
from models import (
    AddItemRequest,
    Cart,
    CartItem,
    CatalogFacets,
    CustomerSummary,
    ProductDetail,
    ProductPage,
    ProductSummary,
    UpdateItemRequest,
)
from pricing import compute_price

PRODUCT_FIELDS = {
    "_id": 0,
    "article_id": 1,
    "prod_name": 1,
    "product_type_name": 1,
    "product_group_name": 1,
    "section_name": 1,
    "index_name": 1,
    "department_name": 1,
    "detail_desc": 1,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = make_client()
    app.state.db = client[DB_NAME]
    await app.state.db["carts"].create_index("customer_id", unique=True)
    yield
    client.close()


app = FastAPI(title="StylistAI Catalog & Cart API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def to_summary(doc: dict) -> ProductSummary:
    article_id = str(doc["article_id"])
    return ProductSummary(
        article_id=article_id,
        prod_name=doc.get("prod_name"),
        product_type_name=doc.get("product_type_name"),
        product_group_name=doc.get("product_group_name"),
        section_name=doc.get("section_name"),
        index_name=doc.get("index_name"),
        price=compute_price(article_id, doc.get("product_group_name")),
        image_url=f"/products/{article_id}/image",
    )


def to_detail(doc: dict) -> ProductDetail:
    return ProductDetail(
        **to_summary(doc).model_dump(),
        detail_desc=doc.get("detail_desc"),
        department_name=doc.get("department_name"),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/products", response_model=ProductPage)
async def list_products(
    q: Optional[str] = Query(None, description="Free-text match on product name"),
    product_group_name: Optional[str] = None,
    section_name: Optional[str] = None,
    index_name: Optional[str] = None,
    article_ids: Optional[str] = Query(
        None, description="Comma-separated article ids; overrides other filters"
    ),
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    if article_ids:
        try:
            keys = [
                normalize_article_id(a) for a in article_ids.split(",") if a.strip()
            ]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        cursor = app.state.db["articles"].find(
            {"article_id": {"$in": keys}}, PRODUCT_FIELDS
        )
        found = {d["article_id"]: d async for d in cursor}
        ordered = [found[k] for k in keys if k in found]
        return ProductPage(
            items=[to_summary(d) for d in ordered],
            total=len(ordered),
            limit=limit,
            offset=0,
        )

    query: dict = {}
    if q:
        query["prod_name"] = {"$regex": re.escape(q.strip()), "$options": "i"}
    if product_group_name:
        query["product_group_name"] = product_group_name
    if section_name:
        query["section_name"] = section_name
    if index_name:
        query["index_name"] = index_name

    collection = app.state.db["articles"]
    cursor = collection.find(query, PRODUCT_FIELDS).skip(offset).limit(limit)
    docs = await cursor.to_list(length=limit)
    total = await collection.count_documents(query, maxTimeMS=5000)

    return ProductPage(
        items=[to_summary(d) for d in docs],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/products/facets", response_model=CatalogFacets)
async def product_facets():
    collection = app.state.db["articles"]
    return CatalogFacets(
        product_group_name=sorted(await collection.distinct("product_group_name")),
        section_name=sorted(await collection.distinct("section_name")),
        index_name=sorted(await collection.distinct("index_name")),
    )


@app.get("/products/{article_id}", response_model=ProductDetail)
async def get_product(article_id: str):
    try:
        key = normalize_article_id(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    doc = await app.state.db["articles"].find_one({"article_id": key}, PRODUCT_FIELDS)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Article {article_id} not found")
    return to_detail(doc)


@app.get("/products/{article_id}/image")
async def get_product_image(article_id: str):
    try:
        key = normalize_article_id(article_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    path = image_path(key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"No image for article {article_id}")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/customers/sample", response_model=list[CustomerSummary])
async def sample_customers(
    n: int = Query(8, ge=1, le=50),
    min_purchases: int = Query(5, ge=0),
):
    """Random customers with enough history to make recommendations interesting.

    Stands in for authentication in this demo.
    """
    # $sample first: matching on purchased_articles across 1.3M unindexed docs
    # before sampling turns this into a ~20s collection scan.
    pipeline = [
        {"$sample": {"size": max(n * 40, 200)}},
        {"$match": {f"purchased_articles.{min_purchases}": {"$exists": True}}},
        {"$limit": n},
        {
            "$project": {
                "_id": 0,
                "customer_id": 1,
                "age": 1,
                "club_member_status": 1,
                "fashion_news_frequency": 1,
                "purchase_count": {"$size": {"$ifNull": ["$purchased_articles", []]}},
            }
        },
    ]
    docs = await app.state.db["customers"].aggregate(pipeline).to_list(length=n)
    return [CustomerSummary(**d) for d in docs]


async def build_cart(customer_id: str) -> Cart:
    doc = await app.state.db["carts"].find_one({"customer_id": customer_id})
    if not doc or not doc.get("items"):
        return Cart(
            customer_id=customer_id,
            items=[],
            item_count=0,
            subtotal=0.0,
            updated_at=doc.get("updated_at") if doc else None,
        )

    keys = [normalize_article_id(i["article_id"]) for i in doc["items"]]
    cursor = app.state.db["articles"].find({"article_id": {"$in": keys}}, PRODUCT_FIELDS)
    products = {str(d["article_id"]): d async for d in cursor}

    items: list[CartItem] = []
    for raw in doc["items"]:
        key = str(normalize_article_id(raw["article_id"]))
        product = products.get(key, {})
        price = compute_price(key, product.get("product_group_name"))
        quantity = int(raw.get("quantity", 1))
        items.append(
            CartItem(
                article_id=key,
                quantity=quantity,
                prod_name=product.get("prod_name"),
                product_type_name=product.get("product_type_name"),
                price=price,
                line_total=round(price * quantity, 2),
                image_url=f"/products/{key}/image",
            )
        )

    return Cart(
        customer_id=customer_id,
        items=items,
        item_count=sum(i.quantity for i in items),
        subtotal=round(sum(i.line_total for i in items), 2),
        updated_at=doc.get("updated_at"),
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/cart/{customer_id}", response_model=Cart)
async def get_cart(customer_id: str):
    return await build_cart(customer_id)


@app.post("/cart/{customer_id}/items", response_model=Cart)
async def add_cart_item(customer_id: str, payload: AddItemRequest):
    try:
        key = str(normalize_article_id(payload.article_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    exists = await app.state.db["articles"].count_documents(
        {"article_id": int(key)}, limit=1
    )
    if not exists:
        raise HTTPException(
            status_code=404, detail=f"Article {payload.article_id} not found"
        )

    carts = app.state.db["carts"]
    updated = await carts.update_one(
        {"customer_id": customer_id, "items.article_id": key},
        {
            "$inc": {"items.$.quantity": payload.quantity},
            "$set": {"updated_at": now_iso()},
        },
    )
    if updated.matched_count == 0:
        await carts.update_one(
            {"customer_id": customer_id},
            {
                "$push": {
                    "items": {
                        "article_id": key,
                        "quantity": payload.quantity,
                        "added_at": now_iso(),
                    }
                },
                "$set": {"updated_at": now_iso()},
            },
            upsert=True,
        )
    return await build_cart(customer_id)


@app.patch("/cart/{customer_id}/items/{article_id}", response_model=Cart)
async def update_cart_item(customer_id: str, article_id: str, payload: UpdateItemRequest):
    try:
        key = str(normalize_article_id(article_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    carts = app.state.db["carts"]
    if payload.quantity == 0:
        await carts.update_one(
            {"customer_id": customer_id},
            {"$pull": {"items": {"article_id": key}}, "$set": {"updated_at": now_iso()}},
        )
    else:
        result = await carts.update_one(
            {"customer_id": customer_id, "items.article_id": key},
            {
                "$set": {
                    "items.$.quantity": payload.quantity,
                    "updated_at": now_iso(),
                }
            },
        )
        if result.matched_count == 0:
            raise HTTPException(
                status_code=404, detail=f"Article {article_id} is not in the cart"
            )
    return await build_cart(customer_id)


@app.delete("/cart/{customer_id}/items/{article_id}", response_model=Cart)
async def delete_cart_item(customer_id: str, article_id: str):
    try:
        key = str(normalize_article_id(article_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await app.state.db["carts"].update_one(
        {"customer_id": customer_id},
        {"$pull": {"items": {"article_id": key}}, "$set": {"updated_at": now_iso()}},
    )
    return await build_cart(customer_id)


@app.delete("/cart/{customer_id}", response_model=Cart)
async def clear_cart(customer_id: str):
    await app.state.db["carts"].update_one(
        {"customer_id": customer_id},
        {"$set": {"items": [], "updated_at": now_iso()}},
        upsert=True,
    )
    return await build_cart(customer_id)
