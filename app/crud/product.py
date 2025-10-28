"""
CRUD operations para Productos usando SQLAlchemy ORM.
"""

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from typing import List, Optional

# Importamos los modelos necesarios
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.producto_categoria import ProductoCategoria
from app.models.documento import Documento

# Importamos los schemas (Pydantic)
from app.schemas.product import ProductCreate, ProductUpdate, ProductRead


def check_product_ownership(product: Producto, user_id: int):
    """Verifica que el producto pertenezca al usuario."""
    if product.UsuarioID != user_id:
        raise HTTPException(403, "No tienes permiso para acceder a este producto")


# ===== CREAR PRODUCTO =====
def create_product(db: Session, product_data: ProductCreate, user_id: int) -> Producto:
    """Crea un nuevo producto en la BD."""

    # Creamos el objeto Producto usando los datos del schema
    # y el user_id de la dependencia
    db_product = Producto(
        NombreProducto=product_data.NombreProducto,
        FechaCompra=product_data.FechaCompra,
        DuracionGarantia=product_data.DuracionGarantia,
        Marca=product_data.Marca,
        Modelo=product_data.Modelo,
        Tienda=product_data.Tienda,
        Notas=product_data.Notas,
        UsuarioID=user_id,
        Precio=product_data.Precio,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # Manejar asignación de categoría inicial si viene en ProductCreate
    if product_data.categoria_id:
        # (Asegúrate que la función exista en crud/categorias.py)
        from .categorias import asignar_categoria_a_producto

        asignar_categoria_a_producto(
            db, db_product.ProductoID, product_data.categoria_id
        )
        db.refresh(db_product)

    return db_product


# ===== OBTENER PRODUCTO POR ID =====
def get_product_by_id(db: Session, product_id: int, user_id: int) -> Optional[Producto]:
    """Obtiene un producto por ID verificando ownership y cargando categorías."""
    product = (
        db.query(Producto)
        .filter(Producto.ProductoID == product_id)
        .options(
            joinedload(Producto.producto_categorias).joinedload(
                ProductoCategoria.categoria
            )
        )
        .first()
    )
    if not product:
        return None

    check_product_ownership(product, user_id)
    return product


# ===== OBTENER PRODUCTOS POR USUARIO =====
def get_products_by_user(db: Session, user_id: int) -> List[Producto]:
    """Obtiene todos los productos de un usuario con sus categorías."""
    productos = (
        db.query(Producto)
        .filter(Producto.UsuarioID == user_id)
        .options(
            joinedload(Producto.producto_categorias).joinedload(
                ProductoCategoria.categoria
            )
        )
        .order_by(Producto.FechaCompra.desc(), Producto.ProductoID.desc())
        .all()
    )
    return productos


# ===== ACTUALIZAR PRODUCTO =====
def update_product(
    db: Session, product_id: int, product_data: ProductUpdate, user_id: int
) -> Optional[Producto]:
    """Actualiza un producto existente."""
    db_product = db.query(Producto).filter(Producto.ProductoID == product_id).first()

    if not db_product:
        return None

    check_product_ownership(db_product, user_id)

    # Actualizar campos (solo los que vienen en el schema)
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)

    db.commit()
    db.refresh(db_product)
    return db_product


# ===== ELIMINAR PRODUCTO (CORREGIDO) =====
def delete_product(db: Session, product_id: int, user_id: int) -> Optional[Producto]:
    """
    Encuentra, carga los documentos y elimina un producto de la BD.

    Devuelve el objeto 'Producto' eliminado (con sus documentos cargados)
    o None si no se encuentra o no pertenece al usuario.
    """

    # 1. Buscamos el producto y CARGAMOS sus documentos asociados
    #    (joinedload) para tenerlos antes de borrar.
    product_to_delete = (
        db.query(Producto)
        .options(joinedload(Producto.documentos))  # Carga ansiosa de documentos
        .filter(Producto.ProductoID == product_id)
        .first()
    )

    if not product_to_delete:
        return None  # No se encontró

    # 2. Verificamos propiedad
    check_product_ownership(product_to_delete, user_id)

    # 3. Eliminamos el producto de la base de datos
    #    Gracias a "ondelete=CASCADE" en tus modelos,
    #    la BD también borrará las referencias en 'documentos'.
    db.delete(product_to_delete)
    db.commit()

    # 4. Devolvemos el objeto que acabamos de borrar
    #    (aún vive en la memoria de Python con sus documentos cargados)
    return product_to_delete
