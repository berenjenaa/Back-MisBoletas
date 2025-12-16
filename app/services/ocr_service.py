import logging
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from app.core.config import settings
from fastapi import HTTPException, UploadFile
import re
from app.db.supabase import supabase_admin  # ✅ Necesario para background_process

logger = logging.getLogger(__name__)


def parse_receipt_data(text: str) -> dict:
    """
    Analiza el texto crudo del OCR para extraer datos clave y DETECTAR ÍTEMS.
    Optimizado para formato chileno (CLP) con separadores de miles.
    """
    data = {
        "comercio": None,
        "fecha": None,
        "total": None,
        "marca": None,
        "modelo": None,
        "garantia": None,
        "items_detectados": [],  # ✅ Lista de productos encontrados
        "cantidad_productos": 0,  # ✅ Cantidad
        "resumen_items": "",  # ✅ Texto formateado para notas
    }

    if not text:
        return data

    text_lower = text.lower()
    lines = text.split("\n")

    # --- 1. NUEVA LÓGICA: Extracción de Ítems ---
    palabras_exclusion = [
        "total",
        "subtotal",
        "iva",
        "neto",
        "descuento",
        "vuelto",
        "cambio",
        "efectivo",
        "tarjeta",
        "debito",
        "credito",
        "redcompra",
        "visa",
        "mastercard",
        "compra",
        "fecha",
        "hora",
        "cajero",
        "transaccion",
        "operacion",
        "boleta",
        "factura",
        "sii",
        "rut",
        "giro",
        "direccion",
        "fono",
        "tel",
        "gracias",
        "cliente",
        "atendido",
        "folio",
        "caja",
        "local",
        "tienda",
        "peso",
        "kg",
        "unid",
        "balanza",
    ]

    posibles_items = []

    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()

        if len(line_clean) < 5 or any(ex in line_lower for ex in palabras_exclusion):
            continue

        # Regex para buscar precio al final de la línea
        match_precio = re.search(r"\s+\$?\s*([\d]+(?:\.[\d]{3})*)", line_clean)

        if match_precio:
            try:
                precio_str = match_precio.group(1).replace(".", "")
                precio_val = int(precio_str)

                # Rango de precio "lógico"
                if 500 <= precio_val <= 5000000:
                    descripcion = line_clean[: match_precio.start()].strip()

                    if any(c.isalpha() for c in descripcion) and len(descripcion) > 3:
                        descripcion = re.sub(r"^[\d\W]+\s+", "", descripcion)
                        posibles_items.append(
                            f"• {descripcion} (${match_precio.group(1)})"
                        )
            except ValueError:
                continue

    data["items_detectados"] = posibles_items
    data["cantidad_productos"] = len(posibles_items)
    if posibles_items:
        data["resumen_items"] = "\n".join(posibles_items)

    # --- 2. Extraer FECHA ---
    date_pattern = r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|(\d{4}[-/]\d{1,2}[-/]\d{1,2})"
    date_match = re.search(date_pattern, text)
    if date_match:
        data["fecha"] = date_match.group(0)

    # --- 3. Extraer TOTAL ---
    total_candidates = []
    for line in lines:
        line_clean = line.lower().strip()
        if "total" in line_clean and not any(
            x in line_clean for x in ["subtotal", "neto", "iva", "descuento"]
        ):
            matches = re.findall(r"[\d]+(?:[.]\d+)*", line_clean)
            for match in matches:
                clean_num = match.replace(".", "")
                try:
                    val = int(clean_num)
                    if 100 <= val <= 50000000:
                        total_candidates.append(val)
                except ValueError:
                    continue

    if total_candidates:
        data["total"] = total_candidates[-1]

    if not data["total"]:
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

    # --- 4. Extraer COMERCIO ---
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
        "DECATHLON",
        "IKEA",
    ]
    for tienda in tiendas_comunes:
        if tienda.lower() in text_lower:
            data["comercio"] = tienda
            break

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

    # --- 5. Extraer MARCA ---
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
        "NIKE",
        "ADIDAS",
    ]
    for marca in marcas_comunes:
        if marca.lower() in text_lower:
            data["marca"] = marca
            break

    # --- 6. Extraer MODELO ---
    modelo_pattern = r"(?i)(?:modelo|mod\.|sku)[\s:.]*([A-Za-z0-9\-\/]+)"
    modelo_match = re.search(modelo_pattern, text)
    if modelo_match:
        val = modelo_match.group(1)
        if len(val) > 2:
            data["modelo"] = val

    # --- 7. Extraer GARANTÍA ---
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
    """Procesa un documento alojado en GCS usando Document AI."""
    project_id = settings.DOCUMENTAI_PROJECT_ID
    location = settings.DOCUMENTAI_LOCATION
    processor_id = settings.DOCUMENTAI_PROCESSOR_ID

    if not all([project_id, location, processor_id]):
        raise ValueError("Faltan configuraciones de Document AI")

    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(project_id, location, processor_id)

    logger.info(
        f"[INFO] Sending GCS image to Document AI (User: {user_id}). URI: {gcs_uri}"
    )

    gcs_document = documentai.GcsDocument(gcs_uri=gcs_uri, mime_type=mime_type)
    request = documentai.ProcessRequest(
        name=name, gcs_document=gcs_document, skip_human_review=True
    )

    try:
        result = client.process_document(request=request)
        document = result.document
        full_text = document.text
        parsed_data = parse_receipt_data(full_text)

        return {
            "texto_completo": full_text,
            "parsed_data": parsed_data,
            "raw_entities": [],
        }
    except Exception as e:
        logger.error(f"[ERROR] Document AI API error: {e}")
        raise e


# ✅ FUNCIÓN RESTAURADA (Causa del error)
async def background_process_ocr(
    documento_id: str, gcs_uri: str, mime_type: str, user_id: str
):
    """
    Tarea en segundo plano que coordina el OCR y actualiza Supabase.
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
    """Procesa un documento subido directamente (en memoria)."""
    project_id = settings.DOCUMENTAI_PROJECT_ID
    location = settings.DOCUMENTAI_LOCATION
    processor_id = settings.DOCUMENTAI_PROCESSOR_ID

    if not all([project_id, location, processor_id]):
        raise ValueError("Faltan configuraciones de Document AI")

    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(project_id, location, processor_id)

    logger.info(
        f"[INFO] Processing raw file (User: {user_id}). Filename: {file.filename}"
    )

    content = await file.read()
    await file.seek(0)

    raw_document = documentai.RawDocument(
        content=content, mime_type=file.content_type or "image/jpeg"
    )
    request = documentai.ProcessRequest(
        name=name, raw_document=raw_document, skip_human_review=True
    )

    try:
        result = client.process_document(request=request)
        document = result.document
        full_text = document.text
        parsed_data = parse_receipt_data(full_text)

        return {
            "texto_completo": full_text,
            "parsed_data": parsed_data,
            "raw_entities": [],
        }
    except Exception as e:
        logger.error(f"[ERROR] Document AI API error (Raw): {e}")
        raise e
