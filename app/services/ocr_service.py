import logging
import json
from fastapi import HTTPException, status, UploadFile
from app.core.config import settings

# Importar librerías de Google Document AI
try:
    from google.api_core.client_options import ClientOptions
    from google.cloud import documentai
except ImportError:
    documentai = None
    ClientOptions = None

logger = logging.getLogger(__name__)

# --- VALIDACIÓN INICIAL ---
if documentai is None:
    logger.critical("[ERROR] google-cloud-documentai library not installed")
elif not all(
    [
        settings.DOCUMENTAI_PROJECT_ID,
        settings.DOCUMENTAI_LOCATION,
        settings.DOCUMENTAI_PROCESSOR_ID,
    ]
):
    logger.critical(
        "[ERROR] Document AI environment variables not configured (PROJECT_ID, LOCATION, PROCESSOR_ID)"
    )


def _get_documentai_client():
    """Crea y configura el cliente de Document AI."""
    if documentai is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "OCR service not installed"
        )

    try:
        opts = ClientOptions(
            api_endpoint=f"{settings.DOCUMENTAI_LOCATION}-documentai.googleapis.com"
        )
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize Document AI client: {e}")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "OCR service initialization failed"
        )

    return client


async def process_boleta_image(file: UploadFile, user_id: str) -> dict:
    """
    Procesa la imagen de una boleta con Google Document AI (Receipt Processor).

    Args:
        file: UploadFile con la imagen
        user_id: ID del usuario (para logging)

    Returns:
        Dict con texto completo y datos estructurados extraídos
    """
    client = _get_documentai_client()

    # 1. Construir el 'name' completo del procesador
    name = client.processor_path(
        settings.DOCUMENTAI_PROJECT_ID,
        settings.DOCUMENTAI_LOCATION,
        settings.DOCUMENTAI_PROCESSOR_ID,
    )

    # 2. Leer los bytes del archivo y el tipo de contenido
    image_content = await file.read()
    mime_type = file.content_type

    # 3. Crear el documento "crudo" para enviar
    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)

    # 4. Crear la petición
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    # 5. Llamar a la API de Document AI
    logger.info(f"[INFO] Sending image to Document AI (User: {user_id})...")
    try:
        result = client.process_document(request=request)
        document = result.document
    except Exception as e:
        logger.error(f"[ERROR] Document AI API error: {e}", exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"OCR external error: {str(e)}"
        )

    # 6. Extraer y estructurar los datos
    extracted_data = {}
    for entity in document.entities:
        value = entity.mention_text
        extracted_data[entity.type_] = value

    logger.info(f"[OK] Data extracted for User {user_id}: {len(extracted_data)} fields")

    return {"texto_completo": document.text, "datos_estructurados": extracted_data}


async def process_boleta_from_gcs_uri(gcs_uri: str, user_id: str = None) -> dict:
    """
    Procesa una imagen de boleta directamente desde GCS (gs://...).

    Ventajas:
    - No requiere descargar bytes (más rápido)
    - Usa GcsSource de Document AI (procesamiento directo en Google Cloud)
    - Ideal para archivos grandes

    Args:
        gcs_uri: URI completa en Google Cloud Storage (ej: gs://bucket-name/path/to/file.jpg)
        user_id: ID del usuario (para logging)

    Returns:
        Dict con:
        - "texto_completo": Texto extraído de la imagen
        - "datos_estructurados": Entidades organizadas por tipo (key: tipo, value: texto)
        - "confianza": Puntuación de confianza promedio (0-1)
        - "raw_entities": Lista completa de entidades con metadata completa
        - "total_entities": Cantidad de entidades extraídas
    """
    client = _get_documentai_client()

    # 1. Construir el 'name' completo del procesador
    name = client.processor_path(
        settings.DOCUMENTAI_PROJECT_ID,
        settings.DOCUMENTAI_LOCATION,
        settings.DOCUMENTAI_PROCESSOR_ID,
    )

    # 2. Validar que sea URI de GCS
    if not gcs_uri.startswith("gs://"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URI format. Must start with 'gs://'. Got: {gcs_uri}",
        )

    # 3. Validar bucket si está configurado
    if settings.GCS_BUCKET_NAME:
        expected_prefix = f"gs://{settings.GCS_BUCKET_NAME}/"
        if not gcs_uri.startswith(expected_prefix):
            logger.warning(
                f"[WARNING] GCS URI from unexpected bucket. Expected: {expected_prefix}, Got: {gcs_uri}"
            )

    # 4. Crear documento usando GCS URI (sin descargar bytes)
    gcs_document = documentai.GcsDocument(gcs_uri=gcs_uri)

    # 5. Crear la petición con referencia a GCS
    request = documentai.ProcessRequest(name=name, gcs_document=gcs_document)

    # 6. Llamar a la API de Document AI
    user_log = f"User: {user_id}" if user_id else "System"
    logger.info(f"[INFO] Sending GCS image to Document AI ({user_log}). URI: {gcs_uri}")
    try:
        result = client.process_document(request=request)
        document = result.document
    except Exception as e:
        logger.error(f"[ERROR] Document AI API error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR external error: {str(e)}")

    # 7. Extraer y estructurar los datos
    extracted_data = {}
    raw_entities = []
    total_confidence = 0.0
    entity_count = 0

    for entity in document.entities:
        value = entity.mention_text
        confidence = entity.confidence if hasattr(entity, "confidence") else 0.0

        # Guardar entidad con metadata completa
        entity_info = {
            "type": entity.type_,
            "value": value,
            "confidence": round(confidence, 3),
        }

        # Agregar bounding box si existe
        if entity.bounding_poly and entity.bounding_poly.vertices:
            entity_info["bounding_box"] = {
                "vertices": [
                    {"x": round(v.x, 4), "y": round(v.y, 4)}
                    for v in entity.bounding_poly.vertices
                ]
            }

        raw_entities.append(entity_info)

        # Agregar al diccionario estructurado (última entidad de cada tipo gana)
        extracted_data[entity.type_] = value

        total_confidence += confidence
        entity_count += 1

    # Calcular confianza promedio
    avg_confidence = (total_confidence / entity_count) if entity_count > 0 else 0.0

    logger.info(
        f"[OK] OCR completed ({user_log}). "
        f"Entities: {entity_count}, "
        f"Avg Confidence: {avg_confidence:.1%}"
    )

    return {
        "texto_completo": document.text,
        "datos_estructurados": extracted_data,
        "confianza": round(avg_confidence, 3),
        "raw_entities": raw_entities,
        "total_entities": entity_count,
    }


async def background_process_ocr(documento_id: str, gcs_uri: str, user_id: str) -> None:
    """
    Procesa OCR en background sin bloquear la respuesta HTTP.

    Actualiza directamente en Supabase:
    - estado_ocr: 'pendiente' -> 'procesando' -> 'completado'/'error'
    - metadata_ocr: Resultado del OCR
    - error_ocr: Mensaje de error (si falla)

    Esta función se llama via asyncio.create_task() desde el endpoint.
    No está en el request HTTP, por lo que el usuario recibe respuesta inmediatamente.

    Args:
        documento_id: UUID del documento
        gcs_uri: URI de Google Cloud Storage (gs://...)
        user_id: UUID del usuario (para logging)
    """
    from app.db.supabase import supabase_admin

    try:
        # 1. Marcar como procesando
        logger.info(f"[BACKGROUND] Starting OCR processing for document {documento_id}")
        supabase_admin.get_table("documentos").update({"estado_ocr": "procesando"}).eq(
            "id", documento_id
        ).execute()

        # 2. Procesar OCR
        ocr_result = await process_boleta_from_gcs_uri(gcs_uri=gcs_uri, user_id=user_id)

        # 3. Guardar resultado en Supabase
        supabase_admin.get_table("documentos").update(
            {
                "metadata_ocr": json.dumps(ocr_result),
                "estado_ocr": "completado",
                "error_ocr": None,
            }
        ).eq("id", documento_id).execute()

        logger.info(
            f"[BACKGROUND] OCR completed successfully for document {documento_id}"
        )

    except Exception as e:
        # 4. Guardar error en Supabase
        error_msg = str(e)[:500]  # Limitar a 500 caracteres
        logger.error(
            f"[BACKGROUND] OCR failed for document {documento_id}: {e}",
            exc_info=True,
        )

        try:
            supabase_admin.get_table("documentos").update(
                {"estado_ocr": "error", "error_ocr": error_msg}
            ).eq("id", documento_id).execute()
        except Exception as db_error:
            logger.error(
                f"[BACKGROUND] Failed to update error state: {db_error}",
                exc_info=True,
            )
