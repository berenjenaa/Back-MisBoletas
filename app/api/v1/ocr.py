# En app/api/v1/ocr.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
import logging
from uuid import UUID

from app.core.dependencies import get_current_user, CurrentUser
from app.db.supabase import supabase

# Importa el servicio OCR
from app.services import ocr_service

router = APIRouter()


def validate_file_magic_bytes(file_bytes: bytes) -> str:
    """
    Valida Magic Bytes (primeros bytes) del archivo.
    
    Returns:
        str: 'pdf', 'jpeg', 'png' si es válido
        
    Raises:
        ValueError: Si el tipo de archivo no es válido
    """
    if len(file_bytes) < 4:
        raise ValueError("Archivo muy pequeño")
    
    # PDF: %PDF (25 50 44 46)
    if file_bytes[:4] == b'%PDF':
        return 'pdf'
    
    # JPEG: FF D8 FF
    if file_bytes[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    
    # PNG: 89 50 4E 47
    if file_bytes[:4] == b'\x89PNG':
        return 'png'
    
    raise ValueError("Tipo de archivo no soportado. Solo PDF, JPEG o PNG.")


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
    try:
        # 1. Leer los primeros bytes del archivo para validar Magic Bytes
        file_bytes = await file.read(512)  # Leer primeros 512 bytes
        
        # Validar usando Magic Bytes (más seguro que content-type)
        try:
            file_type = validate_file_magic_bytes(file_bytes)
            logging.info(f"✅ Archivo validado: {file_type}")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        
        # 2. Volver al inicio del archivo para que Google Vision lo procese
        await file.seek(0)
        
        # 3. Procesar con Document AI
        ocr_results = await ocr_service.process_boleta_image(
            file=file, user_id=current_user.id
        )

        # 4. Parsear los datos extraídos
        texto_completo = ocr_results.get("texto_completo", "")
        parsed_data = ocr_service.parse_receipt_data(texto_completo)

        # 5. Guardar referencia en Supabase (opcional)
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

        # 6. Devolver respuesta con datos parseados
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
