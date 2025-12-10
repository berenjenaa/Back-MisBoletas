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
    con Google Document AI y devuelve los datos estructurados + parseados.

    Args:
        file: Imagen o PDF de boleta
        current_user: Usuario autenticado

    Returns:
        {
            "file_name": "boleta.pdf",
            "content_type": "application/pdf",
            "message": "Procesada exitosamente",
            "ocr_results": {...},
            "parsed_data": {
                "total": 25490,
                "fecha": "10/12/2024",
                "comercio": "DISTRIBUIDORA LÍDER"
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

        # 3. Parsear los datos extraídos (nuevo)
        texto_completo = ocr_results.get("texto_completo", "")
        parsed_data = ocr_service.parse_receipt_data(texto_completo)

        # 4. Guardar referencia en Supabase (opcional)
        try:
            supabase.get_table("ocr_logs").insert(
                {
                    "user_id": current_user.id,
                    "file_name": file.filename,
                    "content_type": file.content_type,
                    "resultado": ocr_results,
                    "parsed_data": parsed_data,
                }
            ).execute()
        except Exception as e:
            logging.warning(f"⚠️  No se pudo guardar log de OCR: {e}")

        # 5. Devolver respuesta con datos parseados
        return {
            "file_name": file.filename,
            "content_type": file.content_type,
            "message": "Boleta procesada exitosamente con OCR",
            "ocr_results": ocr_results,
            "parsed_data": parsed_data,
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
