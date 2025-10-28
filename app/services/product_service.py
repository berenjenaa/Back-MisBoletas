# En app/services/product_service.py

from sqlalchemy.orm import Session
import logging  # Usamos logging para reportar errores
from app.crud import product as crud_product
from app.services.gcs_service import get_gcs_service
from app.core.config import settings

# Configura un logger para este módulo
logger = logging.getLogger(__name__)


def delete_product_with_files(db: Session, product_id: int, user_id: int) -> bool:
    """
    Orquesta la eliminación de un producto:
    1. Llama al CRUD para eliminarlo de la BD.
    2. Si tiene archivos, los elimina de GCS.

    Devuelve True si tuvo éxito, False si no se encontró el producto.
    """

    # 1. El CRUD elimina de la BD y nos devuelve el objeto con sus documentos
    deleted_product = crud_product.delete_product(
        db, product_id=product_id, user_id=user_id
    )

    if not deleted_product:
        logger.warning(
            f"Intento de eliminar producto no encontrado (ID: {product_id}) por usuario (ID: {user_id})"
        )
        return False  # No se encontró el producto

    # 2. Extraemos los blob_names del objeto que nos devolvió el CRUD
    blob_names = [doc.BlobName for doc in deleted_product.documentos if doc.BlobName]

    # 3. Si hay archivos, los eliminamos de GCS
    if settings.gcs_enabled and blob_names:
        gcs_service = get_gcs_service()
        if not gcs_service:
            logger.error("GCS Service no disponible, no se pudieron borrar archivos.")
            return True  # El producto de BD se borró, pero GCS falló

        logger.info(
            f"Servicio eliminando {len(blob_names)} archivos de GCS para producto {product_id}..."
        )
        for blob_name in blob_names:
            try:
                gcs_service.delete_file(blob_name)
            except Exception as e:
                # No detenemos el proceso, solo lo advertimos
                logger.warning(
                    f"ADVERTENCIA: Servicio no pudo eliminar {blob_name} de GCS: {e}"
                )

    return True
