"""
CRUD operations para Productos usando SQLAlchemy ORM.
"""

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from typing import List, Optional

from app.models.producto import Producto
from app.models.categoria import ProductoCategoria, Categoria
from app.schemas.product import Product

def check_product_ownership(product: Producto, user_id: int):
    """Verifica que el producto pertenezca al usuario."""
    if product.UsuarioID != user_id:
        raise HTTPException(403, "No tienes permiso para acceder a este producto")

# ===== CREAR PRODUCTO =====
def create_product(db: Session, product: Product, categoria_id: Optional[int] = None) -> Producto:
    """Crea un nuevo producto en la BD y opcionalmente lo asigna a una categoría."""
    db_product = Producto(
        NombreProducto=product.NombreProducto,
        FechaCompra=product.FechaCompra,
        DuracionGarantia=product.DuracionGarantia,
        Marca=product.Marca,
        Modelo=product.Modelo,
        Tienda=product.Tienda,
        Notas=product.Notas,
        UsuarioID=product.UsuarioID
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # Si se proporcionó una categoría, crear la relación
    if categoria_id:
        producto_categoria = ProductoCategoria(
            ProductoID=db_product.ProductoID,
            CategoriaID=categoria_id
        )
        db.add(producto_categoria)
        db.commit()
        print(f"✅ Producto {db_product.ProductoID} asignado a categoría {categoria_id}")
    
    return db_product

# ===== OBTENER PRODUCTO POR ID =====
def get_product_by_id(db: Session, product_id: int, user_id: int) -> Producto:
    """Obtiene un producto por ID verificando ownership y cargando categorías."""
    product = db.query(Producto)\
        .filter(Producto.ProductoID == product_id)\
        .options(joinedload(Producto.producto_categorias).joinedload(ProductoCategoria.categoria))\
        .first()
    if not product:
        raise HTTPException(404, "Producto no encontrado")
    check_product_ownership(product, user_id)
    return product

# ===== OBTENER PRODUCTOS POR USUARIO =====
def get_products_by_user(db: Session, user_id: int) -> List[Producto]:
    """Obtiene todos los productos de un usuario con sus categorías."""
    productos = db.query(Producto)\
        .filter(Producto.UsuarioID == user_id)\
        .options(joinedload(Producto.producto_categorias).joinedload(ProductoCategoria.categoria))\
        .all()
    
    return productos

# ===== ACTUALIZAR PRODUCTO =====
def update_product(db: Session, product: Product) -> Producto:
    """Actualiza un producto existente."""
    db_product = db.query(Producto).filter(
        Producto.ProductoID == product.ProductoID
    ).first()
    
    if not db_product:
        raise HTTPException(404, "Producto no encontrado")
    
    check_product_ownership(db_product, product.UsuarioID)
    
    # Actualizar campos
    db_product.NombreProducto = product.NombreProducto
    db_product.FechaCompra = product.FechaCompra
    db_product.DuracionGarantia = product.DuracionGarantia
    db_product.Marca = product.Marca
    db_product.Modelo = product.Modelo
    db_product.Tienda = product.Tienda
    db_product.Notas = product.Notas
    
    db.commit()
    db.refresh(db_product)
    return db_product

# ===== ELIMINAR PRODUCTO =====
def delete_product(db: Session, product_id: int, user_id: int) -> dict:
    """Elimina un producto verificando ownership."""
    product = db.query(Producto).filter(Producto.ProductoID == product_id).first()
    
    if not product:
        raise HTTPException(404, "Producto no encontrado")
    
    check_product_ownership(product, user_id)
    
    db.delete(product)
    db.commit()
    
    return {"message": "Producto eliminado correctamente"}