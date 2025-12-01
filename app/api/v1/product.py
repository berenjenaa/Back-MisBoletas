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
    """Obtiene todos los productos del usuario autenticado (excluyendo eliminados)."""
    try:
        # Cambio: Usar RPC en lugar de tabla directa
        response = supabase.rpc(
            'api_listar_productos',
            {'p_id_usuario': str(user_id)}
        ).execute()

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
    """Obtiene un producto específico por ID (con verificación de ownership, excluyendo eliminados)."""
    try:
        # Cambio: Usar RPC en lugar de tabla directa
        response = supabase.rpc(
            'api_obtener_producto',
            {
                'p_id_producto': str(product_id),
                'p_id_usuario': str(user_id)
            }
        ).execute()

        producto_list = response.data or []
        if not producto_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )

        return ProductRead(**producto_list[0])

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
        # Cambio: Usar RPC en lugar de insert directo
        response = supabase.rpc(
            'api_crear_producto',
            {
                'p_id_usuario': str(user_id),
                'p_nombre': product_data.nombre,
                'p_fecha_compra': product_data.fecha_compra,
                'p_duracion_garantia': product_data.duracion_garantia_meses,
                'p_marca': product_data.marca,
                'p_modelo': product_data.modelo,
                'p_tienda': product_data.tienda,
                'p_notas': product_data.notas,
                'p_precio': float(product_data.precio) if product_data.precio else None,
                'p_id_categoria': None  # Por ahora sin categoría en creación
            }
        ).execute()

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
        # Cambio: Usar RPC en lugar de update directo
        response = supabase.rpc(
            'api_actualizar_producto',
            {
                'p_id_producto': str(product_id),
                'p_id_usuario': str(user_id),
                'p_nombre': product_data.nombre,
                'p_fecha_compra': product_data.fecha_compra,
                'p_duracion_garantia': product_data.duracion_garantia_meses,
                'p_marca': product_data.marca,
                'p_modelo': product_data.modelo,
                'p_tienda': product_data.tienda,
                'p_notas': product_data.notas,
                'p_precio': float(product_data.precio) if product_data.precio else None,
                'p_id_categoria': None
            }
        ).execute()

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
    summary="Eliminar un producto (Soft Delete)",
)
async def delete_product(
    product_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Realiza un Soft Delete (borrado lógico) de un producto.

    El producto no se elimina físicamente, solo se marca con una fecha_eliminacion.
    Esto permite recuperarlo si es necesario desde la tabla de auditoría.
    """
    try:
        # Cambio: Usar RPC en lugar de update directo
        response = supabase.rpc(
            'api_eliminar_producto',
            {
                'p_id_producto': str(product_id),
                'p_id_usuario': str(user_id)
            }
        ).execute()

        # api_eliminar_producto devuelve VOID, así que no verificamos response.data
        # Si no hay error, el delete fue exitoso

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar producto",
        )
