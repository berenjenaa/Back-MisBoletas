from sqlalchemy.orm import Session
from sqlalchemy import func, literal_column
from fastapi import HTTPException
from typing import List

from app.models.categoria import Categoria
from app.models.producto_categoria import ProductoCategoria
from app.schemas.categorias import (
    CategoriaCreate,
    CategoriaUpdate,
    CategoriaWithProducts,
)


def get_categoria(db: Session, categoria_id: int, usuario_id: int):
    categoria = (
        db.query(Categoria)
        .filter(
            Categoria.CategoriaID == categoria_id, Categoria.UsuarioID == usuario_id
        )
        .first()
    )
    return categoria


def get_categorias(db: Session, usuario_id: int):
    return db.query(Categoria).filter(Categoria.UsuarioID == usuario_id).all()


def get_categorias_with_product_count(db: Session, usuario_id: int) -> List[dict]:
    """
    Obtiene todas las categorías del usuario, incluyendo un conteo
    de cuántos productos están asociados a cada una.
    """

    query = (
        db.query(
            Categoria.CategoriaID,
            Categoria.NombreCategoria,
            Categoria.Color,
            Categoria.UsuarioID,
            Categoria.FechaCreacion,
            # --- INICIO DE LA CORRECCIÓN ---
            # El atributo en el modelo es 'ProductoID' (mayúscula)
            func.count(ProductoCategoria.ProductoID).label("TotalProductos"),
            # --- FIN DE LA CORRECCIÓN ---
        )
        .outerjoin(
            ProductoCategoria,
            Categoria.CategoriaID == ProductoCategoria.CategoriaID,
        )
        .filter(Categoria.UsuarioID == usuario_id)
        .group_by(
            # Agrupamos por todas las columnas de Categoria (para SQL Server)
            Categoria.CategoriaID,
            Categoria.NombreCategoria,
            Categoria.Color,
            Categoria.UsuarioID,
            Categoria.FechaCreacion,
        )
        .order_by(Categoria.NombreCategoria)
    )

    results = query.all()

    # Mapeamos los resultados a la estructura que espera el schema CategoriaWithProducts
    categorias_list = [
        {
            "CategoriaID": r.CategoriaID,
            "NombreCategoria": r.NombreCategoria,
            "Color": r.Color,
            "UsuarioID": r.UsuarioID,
            "FechaCreacion": r.FechaCreacion,
            "TotalProductos": r.TotalProductos,
        }
        for r in results
    ]

    return categorias_list


def create_categoria(
    db: Session, categoria: CategoriaCreate, usuario_id: int
) -> Categoria:
    db_categoria = Categoria(**categoria.model_dump(), UsuarioID=usuario_id)
    db.add(db_categoria)
    db.commit()
    db.refresh(db_categoria)
    return db_categoria


def update_categoria(
    db: Session,
    categoria_id: int,
    categoria: CategoriaUpdate,
    usuario_id: int,
):
    db_categoria = get_categoria(db, categoria_id, usuario_id)
    if not db_categoria:
        return None

    update_data = categoria.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_categoria, key, value)

    db.commit()
    db.refresh(db_categoria)
    return db_categoria


def delete_categoria(db: Session, categoria_id: int, usuario_id: int) -> bool:
    db_categoria = get_categoria(db, categoria_id, usuario_id)
    if not db_categoria:
        return False

    db.delete(db_categoria)
    db.commit()
    return True


def asignar_categoria_a_producto(db: Session, producto_id: int, categoria_id: int):
    # (El endpoint verifica que ambos IDs pertenezcan al usuario)
    db_relacion = ProductoCategoria(ProductoID=producto_id, CategoriaID=categoria_id)
    db.add(db_relacion)
    db.commit()
    db.refresh(db_relacion)
    return db_relacion


def quitar_categoria_de_producto(
    db: Session, producto_id: int, categoria_id: int
) -> bool:
    db_relacion = (
        db.query(ProductoCategoria)
        .filter(
            ProductoCategoria.ProductoID == producto_id,
            ProductoCategoria.CategoriaID == categoria_id,
        )
        .first()
    )

    if not db_relacion:
        return False

    db.delete(db_relacion)
    db.commit()
    return True
