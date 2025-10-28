"""
Archivo base para registro de modelos SQLAlchemy.

Importa todos los modelos de la aplicación para que:
- Alembic pueda detectarlos automáticamente para migraciones
- SQLAlchemy tenga acceso a todas las tablas y relaciones
- Se mantenga un registro centralizado de todos los modelos

Modelos incluidos:
- Usuario: Gestión de usuarios del sistema
- Categoria: Categorías para organizar productos
- Producto: Productos con garantías y documentos
- Documento: Archivos adjuntos (boletas, garantías, etc.)
- productocategorias: Relación many-to-many productos-categorías
"""

from app.db.session import Base
from app.models.user import Usuario
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.documento import Documento

# Importar los modelos para que SQLAlchemy los detecte
# No se necesita hacer nada más aquí, solo importar

# Importar todos los modelos aquí para que Alembic los detecte
from app.models.user import Usuario
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.documento import Documento
from app.models.producto_categoria import ProductoCategorias

# Esto asegura que todos los modelos estén registrados con SQLAlchemy
