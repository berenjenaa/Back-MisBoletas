import logging
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from app.core.config import settings
from fastapi import HTTPException
import re
from app.db.supabase import supabase_admin

logger = logging.getLogger(__name__)


def parse_receipt_data(text: str) -> dict:
    """
    Analiza el texto crudo del OCR para extraer datos clave usando Regex avanzados.
    Intenta llenar: Tienda, Fecha, Total, Marca, Modelo, Garantía.
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

    # 1. Extraer FECHA (Formatos: DD/MM/AAAA, DD-MM-AAAA, AAAA-MM-DD)
    # Busca fechas válidas en el texto
    date_pattern = r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|(\d{4}[-/]\d{1,2}[-/]\d{1,2})"
    date_match = re.search(date_pattern, text)
    if date_match:
        data["fecha"] = date_match.group(0)

    # 2. Extraer TOTAL
    # Busca patrones como: Total $10.000, Total: 10000, evitando códigos de producto muy largos
    # Estrategia: buscar TODOS los "TOTAL" y tomar el ÚLTIMO (es el más probable que sea el final)
    lines = text.split("\n")
    total_candidates = []

    for i, line in enumerate(lines):
        # Busca líneas que contengan "TOTAL" (pero no SUBTOTAL, NETO, etc. como primer token)
        if re.search(r"(?i)^\s*total\s", line) and not re.search(
            r"(?i)^\s*(?:neto|subtotal)\s", line
        ):
            # Extrae todos los números de esta línea
            numbers = re.findall(r"\d+", line)
            if numbers:
                # Filtra códigos de producto muy largos (típicamente > 10 dígitos)
                filtered = [int(n) for n in numbers if len(n) <= 10]
                if filtered:
                    # Toma el número más grande de los filtrados (generalmente es el total)
                    total_candidates.append(max(filtered))

    # Si tenemos candidatos, toma el ÚLTIMO (es el total final, no descuentos intermedios)
    if total_candidates:
        data["total"] = total_candidates[-1]

    # Si no encuentra por método principal, intenta patrón regex más flexible
    if not data["total"]:
        # Busca específicamente la línea "TOTAL" seguida de un número
        total_pattern = r"(?i)^\s*total\s+(?:\$)?(?:CHI)?[\s]*(\d+(?:[.,]\d{2})?)"
        total_matches = list(re.finditer(total_pattern, text, re.MULTILINE))
        if total_matches:
            # Toma el ÚLTIMO match (es el total final)
            last_match = total_matches[-1]
            raw_amount = last_match.group(1).replace(".", "").replace(",", "")
            try:
                amount = int(raw_amount)
                # Solo aceptar si está en rango razonable (0 a 50 millones CLP aprox)
                if 0 < amount < 50000000:
                    data["total"] = amount
            except:
                pass

    # 3. Extraer COMERCIO (Lista de tiendas comunes en Chile)
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
        lines = text.split("\n")
        for line in lines[:5]:  # Mira las primeras 5 líneas
            clean_line = line.strip()
            if len(clean_line) > 3 and not any(char.isdigit() for char in clean_line):
                # Evitar líneas que parezcan direcciones o códigos
                if (
                    "rut" not in clean_line.lower()
                    and "boleta" not in clean_line.lower()
                ):
                    data["comercio"] = clean_line
                    break

    # 4. Extraer MARCA (Lista de marcas comunes)
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
    ]
    for marca in marcas_comunes:
        if marca.lower() in text_lower:
            data["marca"] = marca
            break

    # 5. Extraer MODELO (Busca palabras clave como 'Mod', 'Modelo' o SKU)
    # Patrón: "Modelo: XYZ-123"
    modelo_pattern = r"(?i)(?:modelo|mod\.|sku)[\s:.]*([A-Za-z0-9\-\/]+)"
    modelo_match = re.search(modelo_pattern, text)
    if modelo_match:
        val = modelo_match.group(1)
        if len(val) > 2:  # Evitar falsos positivos cortos
            data["modelo"] = val

    # 6. Extraer GARANTÍA (Busca "Garantía X meses" o "Garantía X años")
    garantia_pattern = r"(?i)garant[ií]a.*?(\d+)\s*(mes|año|dia)"
    garantia_match = re.search(garantia_pattern, text)
    if garantia_match:
        cantidad = int(garantia_match.group(1))
        unidad = garantia_match.group(2).lower()
        if "año" in unidad:
            data["garantia"] = cantidad * 12  # Convertir a meses
        elif "mes" in unidad:
            data["garantia"] = cantidad
        # Si son días, lo ignoramos o aproximamos a 1 mes si es > 20 días

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
