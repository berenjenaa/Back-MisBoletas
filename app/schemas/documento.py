"""
Schemas Pydantic para Documentos.
Define la estructura de datos para requests y responses de la API.
"""

from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional


# ===== SCHEMA PARA LEER DOCUMENTOS (Response) =====
class DocumentoRead(BaseModel):
    """Schema para devolver información de un documento."""

    documentoid: int = Field(..., alias="DocumentoID")
    productoid: int = Field(..., alias="ProductoID")
    nombrearchivo: str = Field(..., alias="NombreArchivo")
    url_gcs: str = Field(..., alias="URL_GCS")
    blob_name: str = Field(..., alias="BlobName")
    content_type: Optional[str] = Field(None, alias="ContentType")
    size_bytes: Optional[int] = Field(None, alias="SizeBytes")
    fecha_subida: datetime = Field(..., alias="FechaSubida")

    class Config:
        from_attributes = True
        populate_by_name = True  # Permite usar tanto documentoid como DocumentoID


# ===== SCHEMA PARA CREAR DOCUMENTOS (Request) =====
class DocumentoUpload(BaseModel):
    """
    Schema para subir un documento.
    El archivo se envía como multipart/form-data, no en JSON.
    """

    productoid: int = Field(
        ..., description="ID del producto al que pertenece el documento", gt=0
    )


# ===== SCHEMA PARA RESPUESTA DE UPLOAD =====
class DocumentoUploadResponse(BaseModel):
    """Schema para la respuesta al subir un documento."""

    message: str
    documento: DocumentoRead


# ===== SCHEMA PARA ELIMINAR DOCUMENTOS =====
class DocumentoDelete(BaseModel):
    """Schema para la respuesta al eliminar un documento."""

    message: str
    documentoid: int


# ===== SCHEMA SIMPLIFICADO PARA LISTADO =====
class DocumentoListItem(BaseModel):
    """Schema simplificado para listar documentos."""

    documentoid: int = Field(..., alias="DocumentoID")
    nombrearchivo: str = Field(..., alias="NombreArchivo")
    url_gcs: str = Field(..., alias="URL_GCS")
    content_type: Optional[str] = Field(None, alias="ContentType")
    size_bytes: Optional[int] = Field(None, alias="SizeBytes")
    fecha_subida: datetime = Field(..., alias="FechaSubida")

    class Config:
        from_attributes = True
        populate_by_name = True
