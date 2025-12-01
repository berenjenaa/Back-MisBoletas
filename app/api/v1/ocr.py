# En app/api/v1/ocr.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
import logging
from uuid import UUID

from app.core.dependencies import get_current_user, CurrentUser
from app.db.supabase import supabase

# Importa el servicio OCR
from app.services import ocr_service

router = APIRouter()


@router.post("/ocr/procesar-boleta", tags=["OCR"], summary="Procesar boleta con OCR")
async def procesar_boleta_ocr(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Recibe una imagen (JPG, PNG) o PDF de una boleta, la procesa
    con Google Document AI y devuelve los datos estructurados.

    Args:
        file: Imagen o PDF de boleta
        current_user: Usuario autenticado

    Returns:
        {
            "file_name": "boleta.pdf",
            "content_type": "application/pdf",
            "message": "Procesada exitosamente",
            "ocr_results": {
                "texto_extraído": "...",
                "entidades": [...],
                "confidencia": 0.95
            }
        }
    """
    # 1. Validar tipo de archivo
    if (
        not file.content_type.startswith("image/")
        and file.content_type != "application/pdf"
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo no soportado. Usa JPG, PNG o PDF.",
        )

    try:
        # 2. Procesar con Document AI
        ocr_results = await ocr_service.process_boleta_image(
            file=file, user_id=current_user.id  # UUID string
        )

        # 3. Guardar referencia en Supabase (opcional)
        # Puedes guardar el resultado del OCR si lo necesitas
        try:
            supabase.get_table("ocr_logs").insert(
                {
                    "user_id": current_user.id,
                    "file_name": file.filename,
                    "content_type": file.content_type,
                    "resultado": ocr_results,
                }
            ).execute()
        except Exception as e:
            print(f"⚠️  No se pudo guardar log de OCR: {e}")
            # No es crítico, continuar

        # 4. Devolver respuesta
        return {
            "file_name": file.filename,
            "content_type": file.content_type,
            "message": "Boleta procesada exitosamente con OCR",
            "ocr_results": ocr_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Error en OCR: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando boleta. Por favor intenta más tarde.",
        )


@router.get("/ocr/health", tags=["OCR"], summary="Verificar disponibilidad de OCR")
async def ocr_health_check():
    """Verifica que el servicio de OCR está disponible."""
    try:
        # Intentar obtener el procesador
        from app.core.config import settings

        if not settings.DOCUMENTAI_PROJECT_ID:
            return {"status": "unavailable", "reason": "Not configured"}

        return {
            "status": "available",
            "provider": "Google Document AI",
            "processor_id": (
                settings.DOCUMENTAI_PROCESSOR_ID[:8] + "..."
                if settings.DOCUMENTAI_PROCESSOR_ID
                else "N/A"
            ),
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}
