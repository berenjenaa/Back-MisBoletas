"""
Endpoints para ver historial de eliminaciones (auditoría).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
import logging
from datetime import datetime, timezone, timedelta
from app.db.supabase import supabase_admin
from app.core.dependencies import get_active_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auditar", tags=["Auditoría"])


async def verify_admin_role(user_id: UUID):
    """Verifica que el usuario tenga rol admin."""
    try:
        response = (
            supabase_admin.get_table("perfiles")
            .select("id_rol")
            .eq("id_usuario", str(user_id))
            .single()
            .execute()
        )

        user = response.data
        if not user or user.get("id_rol") != 1:
            raise HTTPException(status_code=403, detail="Solo administradores")

        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to verify admin role: {e}")
        raise HTTPException(status_code=500, detail="Error verificando permisos")


@router.get("/eliminaciones", summary="Ver histórico de eliminaciones")
async def get_deletions(dias: int = 7, user_id: UUID = Depends(get_active_user_id)):
    """
    Lista productos/documentos eliminados en los últimos N días.
    Solo para administradores.

    Parámetros:
    - dias: Cuántos días atrás buscar (default: 7)
    """
    await verify_admin_role(user_id)

    try:
        fecha_limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

        response = (
            supabase_admin.get_table("historial_auditoria")
            .select("*")
            .eq("accion", "SOFT_DELETE")
            .gte("fecha_evento", fecha_limite)
            .order("fecha_evento", desc=True)
            .execute()
        )

        eliminaciones = response.data or []
        return {
            "total": len(eliminaciones),
            "dias_buscados": dias,
            "eliminaciones": eliminaciones,
        }
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch deletions: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo histórico")


@router.get("/cambios-usuario/{target_user_id}", summary="Ver cambios de un usuario")
async def get_user_activity(
    target_user_id: UUID, dias: int = 30, user_id: UUID = Depends(get_active_user_id)
):
    """
    Lista todas las acciones (INSERT, UPDATE, DELETE) de un usuario.
    Solo para administradores.
    """
    await verify_admin_role(user_id)

    try:
        fecha_limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

        response = (
            supabase_admin.get_table("historial_auditoria")
            .select("*")
            .eq("id_usuario", str(target_user_id))
            .gte("fecha_evento", fecha_limite)
            .order("fecha_evento", desc=True)
            .execute()
        )

        actividad = response.data or []
        return {
            "usuario": str(target_user_id),
            "total_acciones": len(actividad),
            "dias_buscados": dias,
            "acciones": actividad,
        }
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch user activity: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo actividad")
