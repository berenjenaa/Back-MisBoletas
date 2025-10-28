# En app/api/v1/product.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas.product import ProductRead, ProductCreate, ProductUpdate
from app.crud import product as crud_product
from app.db.session import get_db
from app.core.dependencies import get_current_user_id

# --- CORRECCIONES (Hallazgo 1) ---
# 1. Importamos el nuevo servicio
from app.services import product_service

# 2. Eliminamos imports innecesarios (gcs_service, settings)

router = APIRouter()


@router.get("/productos", response_model=List[ProductRead])
async def get_products(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Obtiene todos los productos del usuario autenticado."""
    products = crud_product.get_products_by_user(db, user_id)
    return [ProductRead.model_validate(p) for p in products]


@router.get("/productos/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Obtiene un producto específico por ID."""
    product = crud_product.get_product_by_id(db, product_id, user_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return ProductRead.model_validate(product)


@router.post("/productos", response_model=ProductRead, status_code=201)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Crea un nuevo producto asociado al usuario autenticado."""
    created = crud_product.create_product(
        db, product_data=product_data, user_id=user_id
    )
    return ProductRead.model_validate(created)


@router.put("/productos/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Actualiza un producto existente del usuario autenticado."""
    updated = crud_product.update_product(
        db, product_id=product_id, product_data=product_data, user_id=user_id
    )
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return ProductRead.model_validate(updated)


@router.delete("/productos/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Elimina un producto y sus documentos asociados (orquestado por el servicio).
    """
    # --- CORRECCIÓN DE ARQUITECTURA (Hallazgo 1) ---
    # 1. El router ya no tiene lógica de GCS.
    # 2. Llama al servicio de orquestación.
    success = product_service.delete_product_with_files(
        db, product_id=product_id, user_id=user_id
    )

    if not success:
        # El servicio devolvió False (no encontró el producto)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    # Si 'success' es True, FastAPI devuelve 204 No Content
    return None
