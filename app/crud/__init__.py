# app/crud/__init__.py

# Importar todo desde user.py
from .user import (
    create_user,
    get_user_for_login,
    update_user_password,
    delete_user,
    get_users_list,
    search_user,
    update_user,
)

# Importar todo desde product.py
from .product import (
    create_product,
    get_product_by_id,
    get_products_by_user,
    update_product,
    delete_product,
)

# Importar todo desde categorias.py
from .categorias import (
    get_categoria,
    get_categorias,
    get_categorias_with_product_count,
    create_categoria,
    update_categoria,
    delete_categoria,
    asignar_categoria_a_producto,
    quitar_categoria_de_producto,
)

# Importar todo desde documento.py
from .documento import (
    create_documento,
    get_documentos_by_producto,
    get_documento_by_id,
    delete_documento,
)

# Puedes añadir __all__ para ser explícito (opcional pero buena práctica)
__all__ = [
    # Funciones de user
    "create_user",
    "get_user_for_login",
    "update_user_password",
    "delete_user",
    "get_users_list",
    "search_user",
    "update_user",
    # Funciones de product
    "create_product",
    "get_product_by_id",
    "get_products_by_user",
    "update_product",
    "delete_product",
    # Funciones de categorias
    "get_categoria",
    "get_categorias",
    "get_categorias_with_product_count",
    "create_categoria",
    "update_categoria",
    "delete_categoria",
    "asignar_categoria_a_producto",
    "quitar_categoria_de_producto",
    # Funciones de documento
    "create_documento",
    "get_documentos_by_producto",
    "get_documento_by_id",
    "delete_documento",
]
