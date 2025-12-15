import logging
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from app.core.config import settings
from fastapi import HTTPException
import re
from app.db.supabase import supabase_admin
from fastapi import UploadFile

logger = logging.getLogger(__name__)

# En app/services/ocr_service.py


def parse_receipt_data(text: str) -> dict:
    """
    Analiza el texto crudo del OCR para extraer datos clave.
    Optimizado para formato chileno (CLP) con separadores de miles.
    """
    data = {
        "comercio": None,
        "fecha": None,
        "total": None,
        "marca": None,
        "modelo": None,
        "garantia": None,
    }

    if not text:
        return data

    text_lower = text.lower()

    # 1. Extraer FECHA
    date_pattern = r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|(\d{4}[-/]\d{1,2}[-/]\d{1,2})"
    date_match = re.search(date_pattern, text)
    if date_match:
        data["fecha"] = date_match.group(0)

    # 2. Extraer TOTAL (Lógica mejorada para CLP)
    # Estrategia: Buscar la palabra "total" y capturar el número asociado limpiando el formato
    lines = text.split("\n")
    total_candidates = []

    for line in lines:
        line_clean = line.lower().strip()
        # Verificar si es una línea de Total válido
        if "total" in line_clean and not any(
            x in line_clean for x in ["subtotal", "neto", "iva", "descuento"]
        ):
            # Busca números que puedan tener puntos de miles (ej: 9.080, 10.000)
            # Regex: Captura digitos, permitiendo puntos entre medio
            matches = re.findall(r"[\d]+(?:[.]\d+)*", line_clean)

            for match in matches:
                # Limpieza CLP:
                # 1. Eliminar puntos de miles (9.080 -> 9080)
                clean_num = match.replace(".", "")

                # 2. Validación básica de integridad
                try:
                    val = int(clean_num)
                    # Filtro de rango lógico para una boleta (ej: $100 a $50M)
                    # Esto descarta códigos de barras o números pequeños como cantidades (1, 2)
                    if 100 <= val <= 50000000:
                        total_candidates.append(val)
                except ValueError:
                    continue

    # Si encontramos candidatos en las líneas, usamos el último (usualmente el Total Final)
    if total_candidates:
        data["total"] = total_candidates[-1]

    # Fallback: Si no se encontró en líneas, buscar patrón multilínea o formato con signo $
    if not data["total"]:
        # Busca "Total" seguido de espacio, signo opcional y número con formato chileno
        # Captura: 9.080, 10000, 1.200.500
        fallback_pattern = r"(?i)total\s+(?:\$|CLP)?\s*([\d]+(?:[.]\d+)*)"
        matches = re.finditer(fallback_pattern, text)

        fallback_candidates = []
        for m in matches:
            raw = m.group(1)
            clean = raw.replace(".", "")
            try:
                val = int(clean)
                if 100 <= val <= 50000000:
                    fallback_candidates.append(val)
            except:
                pass

        if fallback_candidates:
            data["total"] = fallback_candidates[-1]

    # ... (Mantener lógica de Comercio, Marca, Modelo y Garantía igual que antes) ...
    # 3. Extraer COMERCIO
    tiendas_comunes = [
        "LIDER",
        "JUMBO",
        "TOTTUS",
        "UNIMARC",
        "SANTA ISABEL",
        "FALABELLA",
        "RIPLEY",
        "PARIS",
        "LA POLAR",
        "HITES",
        "PC FACTORY",
        "EASY",
        "SODIMAC",
        "CONSTRUMART",
        "ZARA",
        "H&M",
        "MERCADO LIBRE",
        "ALIEXPRESS",
        "SHEIN",
        "CASA ROYAL",
        "ABCDIN",
    ]
    for tienda in tiendas_comunes:
        if tienda.lower() in text_lower:
            data["comercio"] = tienda
            break

    # Si no encuentra tienda conocida, intenta buscar en las primeras líneas
    if not data["comercio"]:
        for line in lines[:5]:
            clean_line = line.strip()
            if len(clean_line) > 3 and not any(char.isdigit() for char in clean_line):
                if (
                    "rut" not in clean_line.lower()
                    and "boleta" not in clean_line.lower()
                ):
                    data["comercio"] = clean_line
                    break

    # 4. Extraer MARCA (Incluyendo las nuevas que agregaste)
    marcas_comunes = [
        "SAMSUNG",
        "LG",
        "SONY",
        "APPLE",
        "HP",
        "DELL",
        "LENOVO",
        "ASUS",
        "ACER",
        "PHILIPS",
        "MIDEA",
        "FENSA",
        "MADEMSA",
        "BOSCH",
        "WHIRLPOOL",
        "ELECTROLUX",
        "THOMAS",
        "URSUS TROTTER",
        "PEUGEOT",
        "CHEVROLET",
        "TOYOTA",
        "NINTENDO",
        "PLAYSTATION",
        "XBOX",
        "XIAOMI",
        "MOTOROLA",
        "HUAWEI",
        "SYBILLA",
        "BASEMENT",
        "AMERICANINO",
        "DOO AUSTRALIA",
        "MANGATA",
        "INDEX",
        "CORONA",
        "TRICOT",
    ]
    for marca in marcas_comunes:
        if marca.lower() in text_lower:
            data["marca"] = marca
            break

    # 5. Extraer MODELO
    modelo_pattern = r"(?i)(?:modelo|mod\.|sku)[\s:.]*([A-Za-z0-9\-\/]+)"
    modelo_match = re.search(modelo_pattern, text)
    if modelo_match:
        val = modelo_match.group(1)
        if len(val) > 2:
            data["modelo"] = val

    # 6. Extraer GARANTÍA
    garantia_pattern = r"(?i)garant[ií]a.*?(\d+)\s*(mes|año|dia)"
    garantia_match = re.search(garantia_pattern, text)
    if garantia_match:
        cantidad = int(garantia_match.group(1))
        unidad = garantia_match.group(2).lower()
        if "año" in unidad:
            data["garantia"] = cantidad * 12
        elif "mes" in unidad:
            data["garantia"] = cantidad

    return data


async def process_boleta_from_gcs_uri(
    gcs_uri: str, mime_type: str, user_id: str
) -> dict:
    """
    Procesa un documento alojado en GCS usando Document AI.

    Args:
        gcs_uri: URI del archivo (gs://bucket/path)
        mime_type: Tipo MIME del archivo (ej: 'application/pdf', 'image/jpeg')
        user_id: ID del usuario (para logs)
    """
    project_id = settings.DOCUMENTAI_PROJECT_ID
    location = settings.DOCUMENTAI_LOCATION
    processor_id = settings.DOCUMENTAI_PROCESSOR_ID

    if not all([project_id, location, processor_id]):
        raise ValueError("Faltan configuraciones de Document AI")

    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(project_id, location, processor_id)

    logger.info(
        f"[INFO] Sending GCS image to Document AI (User: {user_id}). URI: {gcs_uri}, MIME: {mime_type}"
    )

    # Configurar el documento fuente en GCS
    # IMPORTANTE: mime_type es obligatorio para Google Document AI
    gcs_document = documentai.GcsDocument(gcs_uri=gcs_uri, mime_type=mime_type)

    request = documentai.ProcessRequest(
        name=name,
        gcs_document=gcs_document,
        skip_human_review=True,
    )

    try:
        result = client.process_document(request=request)
        document = result.document

        # Extraer texto completo
        full_text = document.text

        # Parsear datos con nuestra lógica mejorada
        parsed_data = parse_receipt_data(full_text)

        return {
            "texto_completo": full_text,
            "parsed_data": parsed_data,
            "raw_entities": [],  # Opcional: procesar entidades nativas de Google si las hay
        }

    except Exception as e:
        logger.error(f"[ERROR] Document AI API error: {e}")
        raise e


async def background_process_ocr(
    documento_id: str, gcs_uri: str, mime_type: str, user_id: str
):
    """
    Tarea en segundo plano que coordina el OCR y actualiza Supabase.
    Recibe mime_type para evitar errores de validación.
    """
    logger.info(f"[BACKGROUND] Starting OCR for doc {documento_id}, MIME: {mime_type}")

    try:
        # 1. Llamar al servicio de Google
        ocr_result = await process_boleta_from_gcs_uri(
            gcs_uri=gcs_uri, mime_type=mime_type, user_id=user_id
        )

        # 2. Actualizar documento en Supabase con éxito
        supabase_admin.get_table("documentos").update(
            {
                "estado_ocr": "completado",
                "metadata_ocr": ocr_result,
                "error_ocr": None,
                # Opcional: Guardar datos parseados en columnas si las creaste en la BD
                # "numero_boleta": ocr_result["parsed_data"].get("numero"),
            }
        ).eq("id_documento", documento_id).execute()

        logger.info(
            f"[BACKGROUND] OCR completed for {documento_id}. Data: {ocr_result['parsed_data']}"
        )

    except Exception as e:
        error_msg = f"500: OCR external error: {str(e)}"
        logger.error(
            f"[BACKGROUND] OCR failed for document {documento_id}: {error_msg}"
        )

        # 3. Actualizar error en Supabase
        supabase_admin.get_table("documentos").update(
            {"estado_ocr": "error", "error_ocr": error_msg}
        ).eq("id_documento", documento_id).execute()


async def process_boleta_image(file: UploadFile, user_id: str) -> dict:
    """
    Procesa un documento subido directamente (en memoria) usando Document AI.
    """
    project_id = settings.DOCUMENTAI_PROJECT_ID
    location = settings.DOCUMENTAI_LOCATION
    processor_id = settings.DOCUMENTAI_PROCESSOR_ID

    if not all([project_id, location, processor_id]):
        raise ValueError("Faltan configuraciones de Document AI")

    # Configurar cliente
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(project_id, location, processor_id)

    logger.info(
        f"[INFO] Processing raw file (User: {user_id}). Filename: {file.filename}"
    )

    # Leer contenido
    content = await file.read()
    await file.seek(0)  # Resetear cursor

    # Crear RawDocument (para archivos directos, NO GCS)
    raw_document = documentai.RawDocument(
        content=content, mime_type=file.content_type or "image/jpeg"  # Fallback común
    )

    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
        skip_human_review=True,
    )

    try:
        result = client.process_document(request=request)
        document = result.document
        full_text = document.text

        # Parsear los datos
        parsed_data = parse_receipt_data(full_text)

        return {
            "texto_completo": full_text,
            "parsed_data": parsed_data,
            "raw_entities": [],
        }

    except Exception as e:
        logger.error(f"[ERROR] Document AI API error (Raw): {e}")
        raise e
