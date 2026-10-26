from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, func, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL must be configured for the marketplace API")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "marketplace_products"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    price_cents: Mapped[int] = mapped_column("price_cents", Integer)
    category: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column("image_url", Text)
    seller_name: Mapped[str] = mapped_column("seller_name", Text)
    inventory: Mapped[int] = mapped_column(Integer, default=0)
    featured: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        "created_at", DateTime(timezone=True), server_default=func.now()
    )


class Order(Base):
    __tablename__ = "marketplace_orders"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    buyer_name: Mapped[str] = mapped_column("buyer_name", Text)
    email: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(Text)
    total_cents: Mapped[int] = mapped_column("total_cents", Integer)
    status: Mapped[str] = mapped_column(Text, default="processing")
    payment_status: Mapped[str] = mapped_column(
        "payment_status", Text, default="demo_paid"
    )
    created_at: Mapped[datetime] = mapped_column(
        "created_at", DateTime(timezone=True), server_default=func.now()
    )
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "marketplace_order_items"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    order_id: Mapped[str] = mapped_column(
        "order_id",
        ForeignKey("marketplace_orders.id", ondelete="CASCADE"),
    )
    product_id: Mapped[str] = mapped_column("product_id", Text)
    title: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price_cents: Mapped[int] = mapped_column("unit_price_cents", Integer)
    image_url: Mapped[str] = mapped_column("image_url", Text)
    order: Mapped[Order] = relationship(back_populates="items")


class ProductInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(max_length=2000)
    priceCents: int = Field(ge=0)
    category: str = Field(min_length=1, max_length=80)
    imageUrl: str = Field(min_length=1, max_length=1000)
    inventory: int = Field(ge=0)
    featured: bool = False


class ProductUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    priceCents: int | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    imageUrl: str | None = Field(default=None, min_length=1, max_length=1000)
    inventory: int | None = Field(default=None, ge=0)
    featured: bool | None = None


class OrderLineInput(BaseModel):
    productId: str
    quantity: int = Field(ge=1, le=100)


class OrderInput(BaseModel):
    buyerName: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=254)
    address: str = Field(min_length=1, max_length=1000)
    items: list[OrderLineInput] = Field(min_length=1, max_length=30)


class OrderStatusInput(BaseModel):
    status: Literal["pending", "processing", "shipped", "delivered", "cancelled"]


app = FastAPI(title="Marketlane API", version="1.0.0")


def product_response(product: Product) -> dict:
    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "priceCents": product.price_cents,
        "category": product.category,
        "imageUrl": product.image_url,
        "sellerName": product.seller_name,
        "inventory": product.inventory,
        "featured": product.featured,
        "createdAt": product.created_at.isoformat(),
    }


def order_response(order: Order) -> dict:
    return {
        "id": order.id,
        "buyerName": order.buyer_name,
        "email": order.email,
        "address": order.address,
        "items": [
            {
                "productId": item.product_id,
                "title": item.title,
                "quantity": item.quantity,
                "unitPriceCents": item.unit_price_cents,
                "imageUrl": item.image_url,
            }
            for item in order.items
        ],
        "totalCents": order.total_cents,
        "status": order.status,
        "paymentStatus": order.payment_status,
        "createdAt": order.created_at.isoformat(),
    }


def seed_catalog(session: Session) -> None:
    if session.scalar(select(func.count()).select_from(Product)):
        return
    session.add_all(
        [
            Product(
                id="carafe-01",
                title="Sculpted stoneware carafe",
                description="A hand-finished pourer with a soft, tactile glaze.",
                price_cents=6800,
                category="Home",
                image_url="/marketplace/products/ceramic-carafe.jpg",
                seller_name="Arc & Loom",
                inventory=12,
                featured=True,
            ),
            Product(
                id="lamp-01",
                title="Walnut atelier lamp",
                description="Solid walnut, a linen shade, and a warm evening glow.",
                price_cents=14200,
                category="Lighting",
                image_url="/marketplace/products/walnut-lamp.jpg",
                seller_name="Northwood Studio",
                inventory=7,
                featured=True,
            ),
            Product(
                id="tote-01",
                title="Everyday canvas market tote",
                description="A sturdy canvas carryall made for daily errands.",
                price_cents=5400,
                category="Accessories",
                image_url="/marketplace/products/canvas-tote.jpg",
                seller_name="Fieldwork Goods",
                inventory=18,
                featured=False,
            ),
        ]
    )
    session.commit()


@app.on_event("startup")
def initialize_catalog() -> None:
    # Tables are provisioned by the workspace's schema push; startup only seeds demo rows.
    with SessionLocal() as session:
        seed_catalog(session)


@app.get("/api/healthz")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/api/marketplace/products")
def list_products(
    search: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=80),
) -> list[dict]:
    with SessionLocal() as session:
        statement = select(Product).order_by(Product.featured.desc(), Product.created_at.desc())
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                Product.title.ilike(term)
                | Product.description.ilike(term)
                | Product.seller_name.ilike(term)
            )
        if category and category.lower() != "all":
            statement = statement.where(Product.category == category)
        return [product_response(product) for product in session.scalars(statement).all()]


@app.post("/api/marketplace/products", status_code=201)
def create_product(data: ProductInput) -> dict:
    image = data.imageUrl.strip()
    if not (image.startswith("/") or re.match(r"^https?://", image, re.IGNORECASE)):
        raise HTTPException(status_code=422, detail="Image must be a web URL or app path")
    with SessionLocal() as session:
        product = Product(
            id=str(uuid4()),
            title=data.title.strip(),
            description=data.description.strip(),
            price_cents=data.priceCents,
            category=data.category.strip(),
            image_url=image,
            seller_name="Your Studio",
            inventory=data.inventory,
            featured=data.featured,
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        return product_response(product)


@app.patch("/api/marketplace/products/{product_id}")
def update_product(product_id: str, data: ProductUpdate) -> dict:
    with SessionLocal() as session:
        product = session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        updates = data.model_dump(exclude_unset=True, by_alias=True)
        if "imageUrl" in updates:
            image = updates["imageUrl"].strip()
            if not (image.startswith("/") or re.match(r"^https?://", image, re.IGNORECASE)):
                raise HTTPException(status_code=422, detail="Image must be a web URL or app path")
            product.image_url = image
        for key, value in updates.items():
            if key != "imageUrl":
                setattr(product, {
                    "priceCents": "price_cents",
                    "inventory": "inventory",
                    "featured": "featured",
                    "title": "title",
                    "description": "description",
                    "category": "category",
                }[key], value)
        session.commit()
        session.refresh(product)
        return product_response(product)


@app.delete("/api/marketplace/products/{product_id}", status_code=204)
def delete_product(product_id: str) -> Response:
    with SessionLocal() as session:
        product = session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        session.delete(product)
        session.commit()
    return Response(status_code=204)


@app.get("/api/marketplace/orders")
def list_orders() -> list[dict]:
    with SessionLocal() as session:
        orders = session.scalars(
            select(Order).order_by(Order.created_at.desc())
        ).all()
        return [order_response(order) for order in orders]


@app.post("/api/marketplace/orders", status_code=201)
def create_order(data: OrderInput) -> dict:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", data.email.strip()):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    with SessionLocal() as session:
        try:
            order_id = str(uuid4())
            lines: list[OrderItem] = []
            total = 0
            with session.begin():
                order = Order(
                    id=order_id,
                    buyer_name=data.buyerName.strip(),
                    email=data.email.strip(),
                    address=data.address.strip(),
                    total_cents=0,
                    status="processing",
                    payment_status="demo_paid",
                )
                session.add(order)
                for item in data.items:
                    product = session.scalar(
                        select(Product)
                        .where(Product.id == item.productId)
                        .with_for_update()
                    )
                    if product is None:
                        raise HTTPException(status_code=404, detail="A product in this cart no longer exists")
                    if product.inventory < item.quantity:
                        raise HTTPException(
                            status_code=409,
                            detail=f"Not enough stock for {product.title}",
                        )
                    product.inventory -= item.quantity
                    total += product.price_cents * item.quantity
                    lines.append(
                        OrderItem(
                            id=str(uuid4()),
                            order_id=order_id,
                            product_id=product.id,
                            title=product.title,
                            quantity=item.quantity,
                            unit_price_cents=product.price_cents,
                            image_url=product.image_url,
                        )
                    )
                order.total_cents = total
                session.add_all(lines)
            created = session.get(Order, order_id)
            if created is None:
                raise HTTPException(status_code=500, detail="Order could not be created")
            return order_response(created)
        except HTTPException:
            raise


@app.patch("/api/marketplace/orders/{order_id}/status")
def update_order_status(order_id: str, data: OrderStatusInput) -> dict:
    with SessionLocal() as session:
        with session.begin():
            order = session.scalar(
                select(Order).where(Order.id == order_id).with_for_update()
            )
            if order is None:
                raise HTTPException(status_code=404, detail="Order not found")
            if order.status == "cancelled" and data.status != "cancelled":
                raise HTTPException(status_code=409, detail="Cancelled orders cannot be reopened")
            if data.status == "cancelled" and order.status != "cancelled":
                for item in order.items:
                    session.execute(
                        update(Product)
                        .where(Product.id == item.product_id)
                        .values(inventory=Product.inventory + item.quantity)
                    )
            order.status = data.status
        session.refresh(order)
        return order_response(order)


@app.get("/api/marketplace/dashboard")
def get_marketplace_dashboard() -> dict:
    with SessionLocal() as session:
        product_count = session.scalar(select(func.count()).select_from(Product)) or 0
        order_count = session.scalar(select(func.count()).select_from(Order)) or 0
        gross_sales = session.scalar(
            select(func.coalesce(func.sum(Order.total_cents), 0)).where(
                Order.status != "cancelled"
            )
        ) or 0
        low_stock_count = session.scalar(
            select(func.count()).select_from(Product).where(Product.inventory <= 5)
        ) or 0
        recent = session.scalars(
            select(Order).order_by(Order.created_at.desc()).limit(5)
        ).all()
        return {
            "productCount": product_count,
            "orderCount": order_count,
            "grossSalesCents": gross_sales,
            "lowStockCount": low_stock_count,
            "recentOrders": [order_response(order) for order in recent],
        }
