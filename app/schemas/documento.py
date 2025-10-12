"""
Schemas Pydantic para Documentos.
Define la estructura de datos para requests y responses de la API.
"""

from pydantic import BaseModel
from typing import Optional

class DocumentoBase(BaseModel):
    """Schema base para documentos."""
    nombrearchivo: str
    rutaarchivo: str

class DocumentoCreate(DocumentoBase):
    """Schema para crear un documento."""
    pass

class DocumentoRead(DocumentoBase):
    """Schema para devolver información de un documento."""
    documentoid: int
    productoid: int

    class Config:
        from_attributes = True

class DocumentoResponse(BaseModel):
    """Schema para las respuestas de operaciones con documentos."""
    message: str
    documentoid: Optional[int] = None
    documento: Optional[DocumentoRead] = None

class DocumentoUpload(BaseModel):
    """Schema para subir un documento."""
    productoid: int

class DocumentoUploadResponse(BaseModel):
    """Schema para la respuesta al subir un documento."""
    message: str
    documento: DocumentoRead

class DocumentoDelete(BaseModel):
    """Schema para la respuesta al eliminar un documento."""
    message: str
    documentoid: int

class DocumentoListItem(BaseModel):
    """Schema simplificado para listar documentos."""
    documentoid: int
    nombrearchivo: str
    
    class Config:
        from_attributes = True
