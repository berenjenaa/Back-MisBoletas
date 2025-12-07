from fastapi import APIRouter, HTTPException, status
from typing import List
import logging

from app.schemas.faqs import FAQRead, FAQCreate
from app.db.supabase import supabase_admin

router = APIRouter(prefix="/faqs", tags=["faqs"])
logger = logging.getLogger(__name__)


@router.get(
    "", response_model=List[FAQRead], summary="Obtener todas las preguntas frecuentes"
)
async def list_faqs():
    """
    Obtiene todas las preguntas frecuentes (FAQs) de la plataforma.
    No requiere autenticación.
    """
    try:
        logger.info("[INFO] Fetching FAQs")
        response = (
            supabase_admin.get_table("faqs")
            .select("*")
            .order("orden", desc=False)
            .execute()
        )
        faqs = response.data or []
        logger.info(f"[INFO] {len(faqs)} FAQs fetched successfully")
        return [FAQRead(**faq) for faq in faqs]
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch FAQs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo preguntas frecuentes. Por favor intenta más tarde.",
        )


@router.get("/{faq_id}", response_model=FAQRead, summary="Obtener una FAQ específica")
async def get_faq(faq_id: int):
    """
    Obtiene una pregunta frecuente específica por ID.
    """
    try:
        response = (
            supabase_admin.get_table("faqs")
            .select("*")
            .eq("id", faq_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pregunta frecuente no encontrada",
            )

        return FAQRead(**response.data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch FAQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo pregunta frecuente. Por favor intenta más tarde.",
        )


@router.post(
    "",
    response_model=FAQRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva FAQ",
)
async def create_faq(faq: FAQCreate):
    """
    Crea una nueva pregunta frecuente.
    Solo para administradores.
    """
    try:
        payload = {
            "pregunta": faq.pregunta,
            "respuesta": faq.respuesta,
            "categoria": faq.categoria,
            "orden": faq.orden,
        }
        logger.info(f"[INFO] Creating FAQ: {faq.pregunta[:50]}...")

        response = supabase_admin.get_table("faqs").insert(payload).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creando pregunta frecuente",
            )

        logger.info(f"[INFO] FAQ created successfully")
        return FAQRead(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to create FAQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creando pregunta frecuente. Por favor intenta más tarde.",
        )


@router.put("/{faq_id}", response_model=FAQRead, summary="Actualizar una FAQ")
async def update_faq(faq_id: int, faq: FAQCreate):
    """
    Actualiza una pregunta frecuente existente.
    Solo para administradores.
    """
    try:
        payload = {
            "pregunta": faq.pregunta,
            "respuesta": faq.respuesta,
            "categoria": faq.categoria,
            "orden": faq.orden,
        }
        logger.info(f"[INFO] Updating FAQ {faq_id}")

        response = (
            supabase_admin.get_table("faqs").update(payload).eq("id", faq_id).execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pregunta frecuente no encontrada",
            )

        logger.info(f"[INFO] FAQ updated successfully")
        return FAQRead(**response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to update FAQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando pregunta frecuente. Por favor intenta más tarde.",
        )


@router.delete(
    "/{faq_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una FAQ"
)
async def delete_faq(faq_id: int):
    """
    Elimina una pregunta frecuente.
    Solo para administradores.
    """
    try:
        logger.info(f"[INFO] Deleting FAQ {faq_id}")

        response = supabase_admin.get_table("faqs").delete().eq("id", faq_id).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pregunta frecuente no encontrada",
            )

        logger.info(f"[INFO] FAQ deleted successfully")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete FAQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error eliminando pregunta frecuente. Por favor intenta más tarde.",
        )
