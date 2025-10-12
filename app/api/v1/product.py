"""
Endpoints API simplificados para Productos.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.schemas.product import ProductRead, ProductCreate, ProductUpdate, Product
from app.schemas.user import UserRead
from app.crud import product as crud_product
from app.db.session import get_db
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/products", response_model=List[ProductRead])
async def get_products(
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Obtiene todos los productos del usuario autenticado."""
    products = crud_product.get_products_by_user(db, current_user.idUsuario)
    return [ProductRead.model_validate(p) for p in products]

@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int, 
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Obtiene un producto específico por ID."""
    product = crud_product.get_product_by_id(db, product_id, current_user.idUsuario)
    return ProductRead.model_validate(product)

@router.post("/products", response_model=ProductRead, status_code=201)
async def create_product(
    product_data: ProductCreate, 
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Crea un nuevo producto asociado al usuario autenticado."""
    print(f"📝 Creando producto para usuario {current_user.idUsuario}")
    print(f"📋 Datos recibidos: {product_data.model_dump()}")
    
    product = Product(
        ProductoID=0,
        NombreProducto=product_data.NombreProducto,
        FechaCompra=product_data.FechaCompra,
        DuracionGarantia=product_data.DuracionGarantia,
        Marca=product_data.Marca or "",
        Modelo=product_data.Modelo or "",
        Tienda=product_data.Tienda or "",
        Notas=product_data.Notas or "",
        UsuarioID=current_user.idUsuario
    )
    
    # Crear producto y asignar categoría si se proporcionó
    created = crud_product.create_product(db, product, categoria_id=product_data.categoria_id)
    
    if product_data.categoria_id:
        print(f"✅ Producto creado y asignado a categoría {product_data.categoria_id}")
    else:
        print(f"✅ Producto creado sin categoría")
    
    return ProductRead.model_validate(created)

@router.put("/products/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int, 
    product_data: ProductUpdate, 
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Actualiza un producto existente del usuario autenticado."""
    # Obtener producto existente
    existing = crud_product.get_product_by_id(db, product_id, current_user.idUsuario)
    
    # Actualizar con nuevos datos
    updated_product = Product(
        ProductoID=product_id,
        NombreProducto=product_data.NombreProducto or existing.NombreProducto,
        FechaCompra=product_data.FechaCompra or existing.FechaCompra,
        DuracionGarantia=product_data.DuracionGarantia or existing.DuracionGarantia,
        Marca=product_data.Marca or existing.Marca,
        Modelo=product_data.Modelo or existing.Modelo,
        Tienda=product_data.Tienda or existing.Tienda,
        Notas=product_data.Notas or existing.Notas,
        UsuarioID=current_user.idUsuario
    )
    updated = crud_product.update_product(db, updated_product)
    return ProductRead.model_validate(updated)

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int, 
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Elimina un producto del usuario autenticado."""
    return crud_product.delete_product(db, product_id, current_user.idUsuario)