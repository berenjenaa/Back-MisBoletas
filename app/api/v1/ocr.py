# En app/api/v1/ocr.py (o donde lo hayas creado)

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import logging

from app.core.dependencies import get_current_user_id
from app.db.session import get_db

# Importa el servicio real
from app.services import ocr_service

router = APIRouter()


@router.post("/ocr/procesar-boleta", tags=["OCR"])
async def procesar_boleta_ocr(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),  # db se mantiene por si el servicio lo necesita
):
    """
    Recibe una imagen (JPG, PNG) o PDF de una boleta, la procesa
    con Document AI y devuelve los datos estructurados.
    """
    # 1. Validar el tipo de archivo (Imágenes o PDF)
    if (
        not file.content_type.startswith("image/")
        and file.content_type != "application/pdf"
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de archivo no soportado. Por favor, sube una imagen (JPG, PNG) o un PDF.",
        )

    # 2. Llamar al servicio para que haga el trabajo
    try:
        ocr_results = await ocr_service.process_boleta_image(file=file, user_id=user_id)

        # 3. Devolver la respuesta exitosa
        return {
            "file_name": file.filename,
            "content_type": file.content_type,
            "message": "Imagen procesada exitosamente con Document AI.",
            "ocr_results": ocr_results,  # Devuelve lo que el servicio encontró
        }

    except HTTPException as e:
        # Si el servicio lanza un error HTTP (ej. 400, 503)
        raise e
    except Exception as e:
        # Si el servicio tiene un error inesperado
        logging.error(f"Error interno en OCR: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocurrió un error inesperado al procesar la imagen.",
        )
