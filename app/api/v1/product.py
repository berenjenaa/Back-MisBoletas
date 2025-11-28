# En app/api/v1/product.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
import logging

from app.schemas.product import ProductRead, ProductCreate, ProductUpdate
from app.core.config import supabase
from app.core.dependencies import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/productos", tags=["productos"])


# =======================================================================
# === ENDPOINTS DE PRODUCTOS (SUPABASE)
# =======================================================================


@router.get("", response_model=List[ProductRead], summary="Listar mis productos")
async def get_products(
    user_id: UUID = Depends(get_current_user_id),
):
    """Obtiene todos los productos del usuario autenticado."""
    try:
        response = (
            supabase.table("productos")
            .select("*")
            .eq("id_usuario", str(user_id))
            .execute()
        )

        productos = response.data or []
        return [ProductRead(**p) for p in productos]

    except Exception as e:
        logger.error(f"[ERROR] Failed to list products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener productos",
        )


@router.get(
    "/{product_id}", response_model=ProductRead, summary="Obtener un producto por ID"
)
async def get_product(
    product_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """Obtiene un producto específico por ID (con verificación de ownership)."""
    try:
        response = (
            supabase.table("productos")
            .select("*")
            .eq("id_producto", str(product_id))
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )

        producto = response.data
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )

        return ProductRead(**producto)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to read product: {e}")
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
    user_id: UUID = Depends(get_current_user_id),
):
    """Crea un nuevo producto asociado al usuario autenticado."""
    try:
        # Preparar datos para insertar
        insert_data = {
            "id_usuario": str(user_id),
            "nombre": product_data.nombre,
            "fecha_compra": product_data.fecha_compra,
            "duracion_garantia_meses": product_data.duracion_garantia_meses,
            "marca": product_data.marca,
            "modelo": product_data.modelo,
            "tienda": product_data.tienda,
            "notas": product_data.notas,
            "precio": float(product_data.precio) if product_data.precio else None,
        }

        response = supabase.table("productos").insert(insert_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al crear producto",
            )

        producto = response.data[0]
        return ProductRead(**producto)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to create product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear producto",
        )


@router.put(
    "/{product_id}", response_model=ProductRead, summary="Actualizar un producto"
)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    user_id: UUID = Depends(get_current_user_id),
):
    """Actualiza un producto existente del usuario autenticado."""
    try:
        # Preparar datos de actualización (solo campos no None)
        update_data = {}
        if product_data.nombre is not None:
            update_data["nombre"] = product_data.nombre
        if product_data.fecha_compra is not None:
            update_data["fecha_compra"] = product_data.fecha_compra
        if product_data.duracion_garantia_meses is not None:
            update_data["duracion_garantia_meses"] = (
                product_data.duracion_garantia_meses
            )
        if product_data.marca is not None:
            update_data["marca"] = product_data.marca
        if product_data.modelo is not None:
            update_data["modelo"] = product_data.modelo
        if product_data.tienda is not None:
            update_data["tienda"] = product_data.tienda
        if product_data.notas is not None:
            update_data["notas"] = product_data.notas
        if product_data.precio is not None:
            update_data["precio"] = float(product_data.precio)

        response = (
            supabase.table("productos")
            .update(update_data)
            .eq("id_producto", str(product_id))
            .eq("id_usuario", str(user_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )

        producto = response.data[0]
        return ProductRead(**producto)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to update product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar producto",
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un producto",
)
async def delete_product(
    product_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Elimina un producto y sus documentos asociados.

    Nota: Los documentos en GCS se eliminarán también.
    """
    try:
        # 1. Obtener documentos asociados para eliminar de GCS
        docs_response = (
            supabase.table("documentos")
            .select("blob_name, url_gcs")
            .eq("id_producto", str(product_id))
            .execute()
        )

        documentos = docs_response.data or []

        # 2. Importar gcs_service para eliminar archivos
        from app.services.gcs_service import get_gcs_service
        from app.core.config import settings

        if settings.gcs_enabled and documentos:
            gcs_service = get_gcs_service()
            if gcs_service:
                for doc in documentos:
                    try:
                        # Usar blob_name directamente si está disponible
                        blob_name = doc.get("blob_name")
                        if not blob_name:
                            url = doc.get("url_gcs", "")
                            if url:
                                blob_name = url.split(f"{settings.GCS_BUCKET_NAME}/")[
                                    -1
                                ]

                        if blob_name:
                            gcs_service.delete_file(blob_name)
                    except Exception as e:
                        logger.warning(
                            f"[WARNING] GCS deletion failed for document: {e}"
                        )

        # 3. Eliminar documentos de Supabase (cascade)
        supabase.table("documentos").delete().eq(
            "id_producto", str(product_id)
        ).execute()

        # 4. Eliminar producto
        response = (
            supabase.table("productos")
            .delete()
            .eq("id", str(product_id))
            .eq("user_id", str(user_id))
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar producto",
        )
