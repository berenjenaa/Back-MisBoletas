# En app/api/v1/product.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from uuid import UUID
import logging

from app.schemas.product import ProductRead, ProductCreate, ProductUpdate
from app.db.supabase import supabase_admin
from app.core.dependencies import get_current_user_id, get_active_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/productos")


@router.get("", response_model=List[ProductRead], summary="Listar mis productos")
async def get_products(
    user_id: UUID = Depends(get_current_user_id),
    categoria: str = Query(None, description="Filtrar por categoria ID (UUID)"),
):
    """Obtiene los productos del usuario autenticado, opcionalmente filtrados por categoría."""
    try:
        # Paso 1: Obtener productos
        if categoria:
            # Si se proporciona un ID de categoría, filtrar por esa categoría
            cat_response = (
                supabase_admin.get_table("producto_categorias")
                .select("id_producto")
                .eq("id_categoria", categoria)
                .execute()
            )
            producto_ids = (
                [pc["id_producto"] for pc in cat_response.data]
                if cat_response.data
                else []
            )

            if not producto_ids:
                return []

            # Obtener esos productos específicos
            response = (
                supabase_admin.get_table("productos")
                .select("*")
                .eq("id_usuario", str(user_id))
                .is_("fecha_eliminacion", "null")
                .in_("id_producto", producto_ids)
                .execute()
            )
        else:
            # Si no hay filtro, obtener todos
            response = (
                supabase_admin.get_table("productos")
                .select("*")
                .eq("id_usuario", str(user_id))
                .is_("fecha_eliminacion", "null")
                .execute()
            )

        productos = response.data or []

        # Paso 2: Para cada producto, obtener sus categorías y contar documentos
        for producto in productos:
            try:
                cat_response = (
                    supabase_admin.get_table("producto_categorias")
                    .select("id_categoria, categorias(id_categoria, nombre, color)")
                    .eq("id_producto", str(producto["id_producto"]))
                    .execute()
                )
                # Extraer solo las categorías (nested select)
                categorias = []
                if cat_response.data:
                    for pc in cat_response.data:
                        if pc.get("categorias"):
                            # Si viene como objeto nested
                            categorias.append(pc["categorias"])
                        else:
                            # Si viene como array
                            categorias.extend(pc.get("categorias", []))

                producto["categorias"] = categorias
            except Exception as cat_error:
                logger.warning(
                    f"[WARNING] Failed to fetch categories for product {producto['id_producto']}: {cat_error}"
                )
                producto["categorias"] = []

            # Contar documentos del producto
            try:
                doc_response = (
                    supabase_admin.get_table("documento_productos")
                    .select("count", count="exact")
                    .eq("id_producto", str(producto["id_producto"]))
                    .execute()
                )
                producto["numero_documentos"] = doc_response.count or 0
            except Exception as doc_error:
                logger.warning(
                    f"[WARNING] Failed to count documents for product {producto['id_producto']}: {doc_error}"
                )
                producto["numero_documentos"] = 0

        return [ProductRead(**p) for p in productos]
    except Exception as e:
        error_msg = str(e)
        # Si es error de RLS (permission denied), retornar lista vacía
        if "permission denied" in error_msg.lower() or "42501" in error_msg:
            logger.warning(
                f"[WARNING] RLS blocked query - returning empty list: {error_msg}"
            )
            return []
        logger.error(f"[ERROR] Failed to list products: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener productos",
        )


# --- HISTORIAL Y RESTAURACIÓN (ANTES DE /{product_id}) ---


@router.get(
    "/historial/eliminados",
    response_model=List[ProductRead],
    summary="Historial de eliminados",
)
async def get_deleted_products(
    user_id: UUID = Depends(get_current_user_id),
):
    """Obtiene los productos que han sido eliminados (Papelera)."""
    try:
        # Traemos productos donde fecha_eliminacion NO es null
        response = (
            supabase_admin.get_table("productos")
            .select("*")
            .eq("id_usuario", str(user_id))
            .not_.is_("fecha_eliminacion", "null")
            .order("fecha_eliminacion", desc=True)
            .execute()
        )
        productos = response.data or []

        # Opcional: Rellenar categorías vacías para cumplir el schema
        for p in productos:
            p["categorias"] = []

        return [ProductRead(**p) for p in productos]
    except Exception as e:
        logger.error(f"[ERROR] Failed to get history: {e}")
        return []


@router.get(
    "/{product_id}", response_model=ProductRead, summary="Obtener un producto por ID"
)
async def get_product(
    product_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Obtiene un producto específico por ID."""
    try:
        response = (
            supabase_admin.get_table("productos")
            .select("*")
            .eq("id_producto", str(product_id))
            .eq("id_usuario", str(user_id))
            .is_("fecha_eliminacion", "null")
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )

        producto = response.data[0]

        # Obtener categorías del producto
        try:
            cat_response = (
                supabase_admin.get_table("producto_categorias")
                .select("id_categoria, categorias(id_categoria, nombre, color)")
                .eq("id_producto", str(product_id))
                .execute()
            )
            categorias = []
            if cat_response.data:
                for pc in cat_response.data:
                    if pc.get("categorias"):
                        categorias.append(pc["categorias"])
                    else:
                        categorias.extend(pc.get("categorias", []))

            producto["categorias"] = categorias
        except Exception as cat_error:
            logger.warning(f"[WARNING] Failed to fetch categories: {cat_error}")
            producto["categorias"] = []

        return ProductRead(**producto)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to read product: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
        )


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo producto",
)
async def create_product(
    product_data: ProductCreate,
    user_id: UUID = Depends(get_active_user_id),
):
    """Crea un nuevo producto."""
    try:
        payload = {
            "id_usuario": str(user_id),
            "nombre": product_data.nombre,
            "fecha_compra": (
                str(product_data.fecha_compra) if product_data.fecha_compra else None
            ),
            "duracion_garantia_meses": product_data.duracion_garantia_meses,
            "marca": product_data.marca,
            "modelo": product_data.modelo,
            "tienda": product_data.tienda,
            "notas": product_data.notas,
            "precio": float(product_data.precio) if product_data.precio else None,
            "id_organizacion": (
                str(product_data.id_organizacion)
                if product_data.id_organizacion
                else None
            ),
        }

        response = supabase_admin.get_table("productos").insert(payload).execute()

        if not response.data or len(response.data) == 0:
            logger.error(f"[ERROR] Insert returned empty data: {response}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al crear producto",
            )

        producto_id = response.data[0]["id_producto"]

        # Guardar relación con categorías si existen
        if product_data.categoria_ids and len(product_data.categoria_ids) > 0:
            try:
                categoria_relations = [
                    {"id_producto": str(producto_id), "id_categoria": str(cat_id)}
                    for cat_id in product_data.categoria_ids
                ]
                supabase_admin.get_table("producto_categorias").insert(
                    categoria_relations
                ).execute()
                logger.info(f"[INFO] Categorías guardadas para producto {producto_id}")
            except Exception as e:
                logger.warning(f"[WARNING] Error saving categories: {e}")
                # No fallar si hay error al guardar categorías

        return ProductRead(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to create product: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear producto. Por favor intenta más tarde.",
        )


@router.put(
    "/{product_id}", response_model=ProductRead, summary="Actualizar un producto"
)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    user_id: UUID = Depends(get_active_user_id),
):
    """Actualiza un producto existente."""
    try:
        # Solo actualizar campos que fueron proporcionados (no None)
        payload = {}
        if product_data.nombre is not None:
            payload["nombre"] = product_data.nombre
        if product_data.fecha_compra is not None:
            payload["fecha_compra"] = str(product_data.fecha_compra)
        if product_data.duracion_garantia_meses is not None:
            payload["duracion_garantia_meses"] = product_data.duracion_garantia_meses
        if product_data.marca is not None:
            payload["marca"] = product_data.marca
        if product_data.modelo is not None:
            payload["modelo"] = product_data.modelo
        if product_data.tienda is not None:
            payload["tienda"] = product_data.tienda
        if product_data.notas is not None:
            payload["notas"] = product_data.notas
        if product_data.precio is not None:
            payload["precio"] = float(product_data.precio)
        if product_data.id_organizacion is not None:
            payload["id_organizacion"] = str(product_data.id_organizacion)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay campos para actualizar",
            )

        response = (
            supabase_admin.get_table("productos")
            .update(payload)
            .eq("id_producto", str(product_id))
            .eq("id_usuario", str(user_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )

        # Actualizar categorías si existen
        if (
            hasattr(product_data, "categoria_ids")
            and product_data.categoria_ids is not None
        ):
            try:
                # Eliminar categorías anteriores
                supabase_admin.get_table("producto_categorias").delete().eq(
                    "id_producto", str(product_id)
                ).execute()

                # Guardar nuevas categorías
                if len(product_data.categoria_ids) > 0:
                    categoria_relations = [
                        {"id_producto": str(product_id), "id_categoria": str(cat_id)}
                        for cat_id in product_data.categoria_ids
                    ]
                    supabase_admin.get_table("producto_categorias").insert(
                        categoria_relations
                    ).execute()
                    logger.info(
                        f"[INFO] Categorías actualizadas para producto {product_id}"
                    )
            except Exception as e:
                logger.warning(f"[WARNING] Error updating categories: {e}")
                # No fallar si hay error al guardar categorías

        return ProductRead(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to update product: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar producto",
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un producto (Soft Delete)",
)
async def delete_product(
    product_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """Realiza un Soft Delete de un producto y limpia sus relaciones."""
    try:
        from datetime import datetime, timezone

        # Soft delete del producto
        response = (
            supabase_admin.get_table("productos")
            .update({"fecha_eliminacion": datetime.now(timezone.utc).isoformat()})
            .eq("id_producto", str(product_id))
            .eq("id_usuario", str(user_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )

        # Limpiar relaciones con categorías (soft delete de la relación)
        try:
            supabase_admin.get_table("producto_categorias").delete().eq(
                "id_producto", str(product_id)
            ).execute()
            logger.info(f"[INFO] Categorías limpiadas para producto {product_id}")
        except Exception as e:
            logger.warning(
                f"[WARNING] Error cleaning categories for product {product_id}: {e}"
            )

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete product: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar producto",
        )


@router.put(
    "/{product_id}/restaurar",
    status_code=status.HTTP_200_OK,
    summary="Restaurar producto",
)
async def restore_product(
    product_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """Restaura un producto eliminado (pone fecha_eliminacion en null)."""
    try:
        response = (
            supabase_admin.get_table("productos")
            .update({"fecha_eliminacion": None})
            .eq("id_producto", str(product_id))
            .eq("id_usuario", str(user_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
        return {"message": "Producto restaurado exitosamente"}
    except Exception as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error al restaurar: {str(e)}"
        )
