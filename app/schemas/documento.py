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

    id_documento: UUID
    id_usuario: UUID
    nombre_archivo: str
    url_gcs: str
    blob_name: str
    content_type: Optional[str] = None
    tipo_documento: Optional[str] = (
        None  # 'boleta', 'factura', 'garantia', 'manual', 'otro'
    )
    metadata_ocr: Optional[Dict[str, Any]] = None  # OCR data (full_text, etc)
    estado_ocr: Optional[str] = (
        None  # 'pendiente' | 'procesando' | 'completado' | 'error'
    )
    error_ocr: Optional[str] = None  # Mensaje de error si OCR falló
    numero_boleta: Optional[str] = None  # Extraído por OCR
    fecha_emision: Optional[date] = None  # Extraído por OCR
    duracion_garantia_especifica: Optional[int] = None  # En días/meses
    fecha_subida: Optional[datetime] = None
    fecha_eliminacion: Optional[datetime] = None  # Soft delete

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

    id_documento: UUID
    id_usuario: UUID
    nombre_archivo: str
    url_gcs: str
    blob_name: str
    content_type: Optional[str] = None
    tipo_documento: Optional[str] = (
        None  # 'boleta', 'factura', 'garantia', 'manual', 'otro'
    )
    metadata_ocr: Optional[Dict[str, Any]] = None  # OCR summary
    estado_ocr: Optional[str] = (
        None  # 'pendiente' | 'procesando' | 'completado' | 'error'
    )
    error_ocr: Optional[str] = None
    numero_boleta: Optional[str] = None
    fecha_emision: Optional[date] = None
    duracion_garantia_especifica: Optional[int] = None
    fecha_subida: Optional[datetime] = None
    fecha_eliminacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ===== SCHEMA PARA GENERAR SIGNED URL =====
class SignedUrlResponse(BaseModel):
    """Response con URL firmada de GCS."""

    documento_id: UUID
    signed_url: str
    expires_in_seconds: int


# ===== SCHEMA PARA ASOCIAR DOCUMENTO EXISTENTE =====
class DocumentoAssociateRequest(BaseModel):
    """Schema para asociar un documento existente a un producto."""

    id_documento: UUID
    id_producto: UUID

    model_config = ConfigDict(from_attributes=True)


class DocumentoAssociateResponse(BaseModel):
    """Response al asociar documento a producto."""

    message: str
    id_relacion: UUID
    documento: DocumentoRead


# ===== SCHEMA PARA OCR RESULTADO =====
class OcrResult(BaseModel):
    """Schema para el resultado del OCR."""

    texto_completo: str
    datos_estructurados: Dict[str, Any]
    confianza: float
    raw_entities: list = []
    total_entities: int = 0
