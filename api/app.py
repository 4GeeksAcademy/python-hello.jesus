import csv
import os
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PRODUCTS_FILE = "products.csv"
FIELDNAMES = ["id", "name", "quantity", "unit", "min_threshold"]

app = FastAPI(title="Inventory API — Suministros Carla")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# CSV helpers
# ──────────────────────────────────────────────

def _read_products() -> list[dict]:
    if not os.path.isfile(PRODUCTS_FILE):
        return []
    with open(PRODUCTS_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["quantity"] = float(row["quantity"])
        row["min_threshold"] = float(row["min_threshold"])
    return rows


def _write_products(products: list[dict]) -> None:
    with open(PRODUCTS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(products)


def _find_by_id(products: list[dict], product_id: str) -> Optional[dict]:
    return next((p for p in products if p["id"] == product_id), None)


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class NewProduct(BaseModel):
    name: str
    quantity: float
    unit: str
    min_threshold: float = 10.0


class StockUpdate(BaseModel):
    delta: float  # positivo = entrada, negativo = salida


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Inventory API active"}


@app.get("/inventory")
def get_inventory():
    """Devuelve la lista completa de productos con sus cantidades."""
    return {"products": _read_products()}


@app.post("/inventory", status_code=201)
def add_product(product: NewProduct):
    """Añade un nuevo producto al catálogo."""
    products = _read_products()
    if any(p["name"].lower() == product.name.lower() for p in products):
        raise HTTPException(
            status_code=409,
            detail=f"El producto '{product.name}' ya existe en el inventario.",
        )
    new = {
        "id": str(uuid.uuid4())[:8],
        "name": product.name,
        "quantity": product.quantity,
        "unit": product.unit,
        "min_threshold": product.min_threshold,
    }
    products.append(new)
    _write_products(products)
    return {"product": new}


@app.patch("/inventory/{product_id}")
def update_stock(product_id: str, update: StockUpdate):
    """Actualiza el stock de un producto. delta positivo = entrada, negativo = salida."""
    products = _read_products()
    product = _find_by_id(products, product_id)
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Producto con id '{product_id}' no encontrado.",
        )
    new_qty = product["quantity"] + update.delta
    if new_qty < 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Stock insuficiente. Stock actual de '{product['name']}': "
                f"{product['quantity']} {product['unit']}. Delta solicitado: {update.delta}."
            ),
        )
    product["quantity"] = new_qty
    _write_products(products)
    return {
        "product": product,
        "low_stock_alert": new_qty <= product["min_threshold"],
    }


@app.get("/inventory/alerts")
def get_alerts():
    """Devuelve los productos cuya cantidad está igual o por debajo de su umbral mínimo."""
    products = _read_products()
    alerts = [p for p in products if p["quantity"] <= p["min_threshold"]]
    return {"alerts": alerts, "total": len(alerts)}
