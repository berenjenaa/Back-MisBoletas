"""
Schemas Pydantic para Documentos.
Define la estructura de datos para requests y responses de la API.
Incluye soporte para OCR metadata.
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from typing import Optional, Dict, Any
from uuid import UUID


# ===== SCHEMA PARA LEER DOCUMENTOS (Response) =====
class DocumentoRead(BaseModel):
    """Schema para devolver información de un documento desde Supabase."""

    id: UUID
    producto_id: UUID
    nombre_archivo: str
    url_gcs: str
    blob_name: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    metadata_ocr: Optional[Dict[str, Any]] = None  # OCR data
    estado_ocr: Optional[str] = (
        None  # 'pendiente' | 'procesando' | 'completado' | 'error'
    )
    error_ocr: Optional[str] = None  # Mensaje de error si OCR falló
    numero_boleta: Optional[str] = None  # Nuevo
    fecha_emision: Optional[date] = None  # Nuevo
    duracion_garantia_especifica: Optional[int] = None  # Nuevo (en días/meses)
    fecha_subida: datetime

    model_config = ConfigDict(from_attributes=True)


# ===== SCHEMA PARA RESPUESTA DE UPLOAD =====
class DocumentoUploadResponse(BaseModel):
    """Schema para la respuesta al subir un documento."""

    message: str
    documento: DocumentoRead
    ocr_processed: bool = False


# ===== SCHEMA PARA ELIMINAR DOCUMENTOS =====
class DocumentoDelete(BaseModel):
    """Schema para la respuesta al eliminar un documento."""

    message: str
    documento_id: UUID


# ===== SCHEMA SIMPLIFICADO PARA LISTADO =====
class DocumentoListItem(BaseModel):
    """Schema simplificado para listar documentos."""

    id: UUID
    producto_id: UUID
    nombre_archivo: str
    url_gcs: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    metadata_ocr: Optional[Dict[str, Any]] = None  # OCR summary
    estado_ocr: Optional[str] = (
        None  # 'pendiente' | 'procesando' | 'completado' | 'error'
    )
    error_ocr: Optional[str] = None  # Mensaje de error si OCR falló
    numero_boleta: Optional[str] = None
    fecha_emision: Optional[date] = None
    duracion_garantia_especifica: Optional[int] = None
    fecha_subida: datetime

    model_config = ConfigDict(from_attributes=True)


# ===== SCHEMA PARA GENERAR SIGNED URL =====
class SignedUrlResponse(BaseModel):
    """Response con URL firmada de GCS."""

    documento_id: UUID
    signed_url: str
    expires_in_seconds: int


# ===== SCHEMA PARA OCR RESULTADO =====
class OcrResult(BaseModel):
    """Schema para el resultado del OCR."""

    texto_completo: str
    datos_estructurados: Dict[str, Any]
    confianza: float
    raw_entities: list = []
    total_entities: int = 0
