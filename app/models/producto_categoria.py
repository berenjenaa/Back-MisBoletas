from sqlalchemy import Table, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


# ==========================================
# Modelo de ProductoCategoria (M2M)
# ==========================================
class ProductoCategoria(Base):

    __tablename__ = "productocategorias"

    # Clave Primaria
    ID = Column("id", Integer, primary_key=True, index=True)

    # Claves Foráneas
    ProductoID = Column(
        "productoid",
        Integer,
        ForeignKey("productos.productoid", ondelete="CASCADE"),
        nullable=False,
    )
    CategoriaID = Column(
        "categoriaid",
        Integer,
        # CAMBIO: De 'CASCADE' a 'NO ACTION' para evitar el error de múltiples rutas de cascada en SQL Server.
        ForeignKey("categorias.categoriaid", ondelete="NO ACTION"),
        nullable=False,
    )

    # Timestamp
    FechaAsignacion = Column(
        "fechaasignacion", DateTime(timezone=True), server_default=func.now()
    )

    # Relaciones
    producto = relationship("Producto", back_populates="producto_categorias")
    categoria = relationship("Categoria", back_populates="producto_categorias")
