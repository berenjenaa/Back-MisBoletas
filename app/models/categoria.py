"""
Modelos SQLAlchemy para Categorías y relación Producto-Categoría (M2M).
Permite a los usuarios organizar sus productos con categorías personalizadas.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Categoria(Base):
    """
    Tabla principal de categorías.
    Cada usuario puede crear sus propias categorías con colores personalizados.
    """
    __tablename__ = "categorias"
    
    # Clave Primaria
    CategoriaID = Column("categoriaid", Integer, primary_key=True, index=True)
    
    # Campos de datos
    NombreCategoria = Column("nombrecategoria", String(100), nullable=False)
    Color = Column("color", String(7), default="#007BFF")  # Hex color code
    
    # Clave Foránea al Usuario
    UsuarioID = Column("usuarioid", Integer, ForeignKey("usuarios.usuarioid", ondelete="CASCADE"), nullable=False)
    
    # Timestamp
    FechaCreacion = Column("fechacreacion", DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="categorias")
    
    # Relación M2M con productos a través de ProductoCategoria
    producto_categorias = relationship(
        "ProductoCategoria",
        back_populates="categoria",
        cascade="all, delete-orphan"
    )


class ProductoCategoria(Base):
    """
    Tabla de relación muchos-a-muchos entre Productos y Categorías.
    Un producto puede tener múltiples categorías y una categoría puede tener múltiples productos.
    """
    __tablename__ = "productocategorias"
    
    # Clave Primaria
    ID = Column("id", Integer, primary_key=True, index=True)
    
    # Claves Foráneas
    ProductoID = Column("productoid", Integer, ForeignKey('productos.productoid', ondelete='CASCADE'), nullable=False)
    CategoriaID = Column("categoriaid", Integer, ForeignKey('categorias.categoriaid', ondelete='CASCADE'), nullable=False)
    
    # Timestamp
    FechaAsignacion = Column("fechaasignacion", DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    producto = relationship("Producto", back_populates="producto_categorias")
    categoria = relationship("Categoria", back_populates="producto_categorias")
