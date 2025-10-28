"""
Modelo SQLAlchemy para la tabla Productos.
Define productos con información de garantía y documentos
"""

# Se añade Numeric para el campo de precio
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
from app.db.session import Base


# ==========================================
# Modelo de Producto
# ==========================================
class Producto(Base):
    """
    Modelo SQLAlchemy para la tabla Productos.
    Define productos con información de garantía y documentos
    """

    __tablename__ = "productos"

    # Clave Primaria Autoincremental
    ProductoID = Column("productoid", Integer, primary_key=True, index=True)

    # Campos de datos
    NombreProducto = Column("nombreproducto", String(150), nullable=False)
    FechaCompra = Column("fechacompra", Date)
    DuracionGarantia = Column("duraciongarantia", Integer)
    Marca = Column("marca", String(100))
    Modelo = Column("modelo", String(100))
    Tienda = Column("tienda", String(100))
    Notas = Column("notas", Text)
    # --- CAMBIO AÑADIDO ---
    # Columna para el precio (para el dashboard y la IA)
    # Numeric(10, 2) permite números hasta 99,999,999.99
    Precio = Column("precio", Numeric(10, 2), nullable=True)

    # Clave Foránea al Usuario
    UsuarioID = Column(
        "usuarioid",
        Integer,
        ForeignKey("usuarios.usuarioid", ondelete="CASCADE"),
        nullable=False,
    )

    # Relaciones (Relationships)
    usuario = relationship("Usuario", back_populates="productos")

    documentos = relationship(
        "Documento", back_populates="producto", cascade="all, delete-orphan"
    )

    producto_categorias = relationship(
        "ProductoCategoria", back_populates="producto", cascade="all, delete-orphan"
    )

    @property
    def categorias(self):
        """Propiedad computada para obtener las categorías del producto"""
        return [pc.categoria for pc in self.producto_categorias]
