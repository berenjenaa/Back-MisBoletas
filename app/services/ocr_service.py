import logging
from fastapi import HTTPException, status, UploadFile
from app.core.config import settings  # Importa los settings

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
    logger.critical("Librería 'google-cloud-documentai' no instalada.")
elif not all(
    [
        settings.DOCUMENTAI_PROJECT_ID,
        settings.DOCUMENTAI_LOCATION,
        settings.DOCUMENTAI_PROCESSOR_ID,
    ]
):
    logger.critical(
        "Variables de entorno de Document AI no configuradas (PROJECT_ID, LOCATION, PROCESSOR_ID)."
    )


def _get_documentai_client():
    """Crea y configura el cliente de Document AI."""
    if documentai is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio de OCR no instalado."
        )

    try:
        # Configura el cliente para que use la región correcta
        opts = ClientOptions(
            api_endpoint=f"{settings.DOCUMENTAI_LOCATION}-documentai.googleapis.com"
        )
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
    except Exception as e:
        logger.error(f"Error al instanciar Document AI: {e}")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Servicio de OCR no pudo iniciarse."
        )

    return client


async def process_boleta_image(file: UploadFile, user_id: int) -> dict:
    """
    Procesa la imagen de una boleta con Google Document AI (Receipt Processor).
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
    logger.info(f"Enviando imagen a Document AI (Usuario: {user_id})...")
    try:
        result = client.process_document(request=request)
        document = result.document
    except Exception as e:
        logger.error(f"Error en la API de Document AI: {e}", exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error externo de OCR: {e}"
        )

    # 6. Extraer y estructurar los datos (¡la mejor parte!)
    # No más RegEx. Document AI nos da los campos ("entities").

    extracted_data = {}
    for entity in document.entities:
        # 'entity.type_' es el nombre del campo (ej: 'total_amount')
        # 'entity.mention_text' es el valor (ej: '$12.345')

        # Opcional: Limpiar el valor (ej. quitar '$' o 'CLP')
        value = entity.mention_text
        if entity.type_ == "total_amount":
            # Aquí puedes añadir lógica para convertir "12.345" a 12345.0
            pass

        extracted_data[entity.type_] = value

    logger.info(f"Datos extraídos para Usuario {user_id}: {extracted_data}")

    return {"texto_completo": document.text, "datos_estructurados": extracted_data}
