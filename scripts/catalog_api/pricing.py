"""Synthetic pricing.

The H&M dataset ships no price column (transactions.csv holds a normalised,
non-monetary value), so prices here are generated for demo purposes only.
Derived from a hash of the article_id, so a given article always shows the
same price without needing a database migration.
"""
import hashlib

PRICE_BANDS = {
    "Accessories": (4.99, 24.99),
    "Bags": (12.99, 49.99),
    "Cosmetic": (3.99, 19.99),
    "Fun": (4.99, 19.99),
    "Furniture": (19.99, 99.99),
    "Garment Full body": (24.99, 89.99),
    "Garment Lower body": (14.99, 59.99),
    "Garment Upper body": (9.99, 49.99),
    "Garment and Shoe care": (3.99, 12.99),
    "Interior textile": (7.99, 39.99),
    "Items": (4.99, 24.99),
    "Nightwear": (12.99, 39.99),
    "Shoes": (19.99, 89.99),
    "Socks & Tights": (3.99, 14.99),
    "Stationery": (2.99, 9.99),
    "Swimwear": (9.99, 39.99),
    "Underwear": (5.99, 29.99),
    "Underwear/nightwear": (7.99, 34.99),
}
DEFAULT_BAND = (9.99, 49.99)


def compute_price(article_id, product_group_name: str | None) -> float:
    low, high = PRICE_BANDS.get(product_group_name or "", DEFAULT_BAND)
    digest = hashlib.md5(str(article_id).encode()).hexdigest()
    fraction = (int(digest[:8], 16) % 10_000) / 10_000
    return round(low + fraction * (high - low), 2)
