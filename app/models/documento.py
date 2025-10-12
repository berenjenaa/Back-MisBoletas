"""
Modelo SQLAlchemy para la tabla Documentos.
Define documentos adjuntos a productos (boletas, garantías, facturas)
Almacena URLs de Google Cloud Storage en lugar de rutas locales.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Documento(Base):
    __tablename__ = "documentos"
    
    # Clave Primaria Autoincremental
    DocumentoID = Column("documentoid", Integer, primary_key=True, index=True)
    ProductoID = Column("productoid", Integer, ForeignKey("productos.productoid", ondelete='CASCADE'), nullable=False, index=True)
    
    # Información del archivo
    NombreArchivo = Column("nombrearchivo", String(255), nullable=False)        # Nombre original del archivo
    URL_GCS = Column("url_gcs", String(500), nullable=False)              # URL completa de GCS (público o firmado)
    BlobName = Column("blob_name", String(500), nullable=False, unique=True)  # Nombre del blob en GCS (para eliminación)
    
    # Metadatos del archivo
    ContentType = Column("content_type", String(100))                         # Tipo MIME (application/pdf, image/jpeg, etc.)
    SizeBytes = Column("size_bytes", BigInteger)                            # Tamaño en bytes
    
    # Timestamps
    FechaSubida = Column("fecha_subida", DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relación con el producto
    producto = relationship("Producto", back_populates="documentos")
