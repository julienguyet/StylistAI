from typing import List, Optional

from pydantic import BaseModel, Field


class ProductSummary(BaseModel):
    article_id: str
    prod_name: Optional[str] = None
    product_type_name: Optional[str] = None
    product_group_name: Optional[str] = None
    section_name: Optional[str] = None
    index_name: Optional[str] = None
    price: float
    currency: str = "EUR"
    image_url: str


class ProductDetail(ProductSummary):
    detail_desc: Optional[str] = None
    department_name: Optional[str] = None


class ProductPage(BaseModel):
    items: List[ProductSummary]
    total: int
    limit: int
    offset: int


class CatalogFacets(BaseModel):
    product_group_name: List[str]
    section_name: List[str]
    index_name: List[str]


class CustomerSummary(BaseModel):
    customer_id: str
    age: Optional[int] = None
    club_member_status: Optional[str] = None
    fashion_news_frequency: Optional[str] = None
    purchase_count: int = 0


class CartItem(BaseModel):
    article_id: str
    quantity: int
    prod_name: Optional[str] = None
    product_type_name: Optional[str] = None
    price: float
    line_total: float
    image_url: str


class Cart(BaseModel):
    customer_id: str
    items: List[CartItem]
    item_count: int
    subtotal: float
    currency: str = "EUR"
    updated_at: Optional[str] = None


class AddItemRequest(BaseModel):
    article_id: str
    quantity: int = Field(1, ge=1, le=99)


class UpdateItemRequest(BaseModel):
    quantity: int = Field(..., ge=0, le=99)
