"""
Servicio para eliminar archivos de GCS al borrar documentos.
Lógica simple: soft delete en BD + historial de auditoría.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID
from app.db.supabase import supabase_admin
from app.services.gcs_service import get_gcs_service

logger = logging.getLogger(__name__)


async def delete_gcs_file(blob_name: str) -> bool:
    """Intenta borrar un archivo de GCS."""
    try:
        gcs_service = get_gcs_service()
        if not gcs_service:
            logger.warning("[WARNING] GCS service not available")
            return False

        gcs_service.delete_file(blob_name)
        logger.info(f"[OK] Deleted from GCS: {blob_name}")
        return True
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete {blob_name}: {e}")
        return False


async def register_deletion_history(
    tabla: str, id_registro: UUID, datos_antiguos: dict, id_usuario: UUID = None
):
    """Registra en historial que un registro fue eliminado (soft delete)."""
    try:
        supabase_admin.get_table("historial_auditoria").insert(
            {
                "tabla_afectada": tabla,
                "accion": "SOFT_DELETE",
                "datos_antiguos": datos_antiguos,
                "id_usuario": str(id_usuario) if id_usuario else None,
                "fecha_evento": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

        logger.info(f"[OK] Registered deletion: {tabla} {id_registro}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to register deletion: {e}")
