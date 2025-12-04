"""
Router para Organizaciones y Miembros.
Gestión de organizaciones familiares, empresariales, jjvv y clubes deportivos.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from datetime import datetime, timezone
import logging

from app.core.dependencies import get_active_user_id
from app.db.supabase import supabase_admin
from app.schemas.organization import (
    OrganizacionCreate,
    OrganizacionRead,
    OrganizacionWithMembers,
    OrganizacionUpdate,
    MiembroCreate,
    MiembroRead,
)

router = APIRouter(prefix="/organizaciones", tags=["Organizaciones"])
logger = logging.getLogger(__name__)


# ===== ENDPOINTS DE ORGANIZACIONES =====


@router.post("/", response_model=OrganizacionRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org: OrganizacionCreate,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Crear una nueva organización.
    El usuario actual es el propietario.
    """
    try:
        org_data = {
            "nombre": org.nombre,
            "id_tipo": org.id_tipo,
            "descripcion": org.descripcion,
            "ruc": org.ruc,
            "id_propietario": str(user_id),
            "fecha_creacion": datetime.now(timezone.utc).isoformat(),
        }

        response = supabase_admin.get_table("organizaciones").insert(org_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creando organización",
            )

        logger.info(
            f"[INFO] Organización creada: {response.data[0]['id_organizacion']}"
        )
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to create organization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creando organización",
        )


@router.get("/", response_model=List[OrganizacionRead])
async def list_my_organizations(
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Obtener todas las organizaciones donde el usuario es propietario (excluyendo eliminadas).
    """
    try:
        # Organizaciones como propietario
        org_response = (
            supabase_admin.get_table("organizaciones")
            .select("*")
            .eq("id_propietario", str(user_id))
            .is_("fecha_eliminacion", "null")  # Soft delete filter
            .execute()
        )

        organizations = org_response.data or []

        # Agregar count de miembros
        for org in organizations:
            miembros_response = (
                supabase_admin.get_table("miembros")
                .select("id_miembro", count="exact")
                .eq("id_organizacion", str(org["id_organizacion"]))
                .eq("estado", "activo")
                .execute()
            )
            org["miembros_count"] = miembros_response.count or 0

        logger.info(f"[INFO] User {user_id} has {len(organizations)} organizations")
        return organizations

    except Exception as e:
        logger.error(f"[ERROR] Failed to list organizations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo organizaciones",
        )


@router.get("/{org_id}", response_model=OrganizacionWithMembers)
async def get_organization(
    org_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Obtener una organización con sus miembros.
    Solo el propietario puede verla.
    """
    try:
        # Verificar permisos
        org_response = (
            supabase_admin.get_table("organizaciones")
            .select("*")
            .eq("id_organizacion", str(org_id))
            .eq("id_propietario", str(user_id))
            .execute()
        )

        if not org_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organización no encontrada o sin permisos",
            )

        org = org_response.data[0]

        # Obtener miembros
        miembros_response = (
            supabase_admin.get_table("miembros")
            .select("*")
            .eq("id_organizacion", str(org_id))
            .execute()
        )

        org["miembros"] = miembros_response.data or []

        return org

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to get organization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo organización",
        )


@router.put("/{org_id}", response_model=OrganizacionRead)
async def update_organization(
    org_id: UUID,
    org_update: OrganizacionUpdate,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Actualizar una organización.
    Solo el propietario puede hacerlo.
    """
    try:
        # Verificar permisos
        org_response = (
            supabase_admin.get_table("organizaciones")
            .select("id_organizacion")
            .eq("id_organizacion", str(org_id))
            .eq("id_propietario", str(user_id))
            .execute()
        )

        if not org_response.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para actualizar esta organización",
            )

        # Preparar datos a actualizar
        update_data = org_update.model_dump(exclude_unset=True)

        response = (
            supabase_admin.get_table("organizaciones")
            .update(update_data)
            .eq("id_organizacion", str(org_id))
            .execute()
        )

        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to update organization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando organización",
        )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Eliminar una organización (Soft Delete).
    Solo el propietario puede hacerlo.
    """
    try:
        # Verificar permisos
        org_response = (
            supabase_admin.get_table("organizaciones")
            .select("id_organizacion")
            .eq("id_organizacion", str(org_id))
            .eq("id_propietario", str(user_id))
            .execute()
        )

        if not org_response.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para eliminar esta organización",
            )

        # Soft delete
        supabase_admin.get_table("organizaciones").update(
            {"fecha_eliminacion": datetime.now(timezone.utc).isoformat()}
        ).eq("id_organizacion", str(org_id)).execute()

        logger.info(f"[INFO] Organization {org_id} deleted (soft delete)")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to delete organization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error eliminando organización",
        )


# ===== ENDPOINTS DE MIEMBROS =====


@router.post(
    "/{org_id}/miembros",
    response_model=MiembroRead,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    org_id: UUID,
    miembro: MiembroCreate,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Invitar un miembro a la organización.
    Solo el propietario puede hacerlo.
    """
    try:
        # Verificar permisos
        org_response = (
            supabase_admin.get_table("organizaciones")
            .select("id_organizacion")
            .eq("id_organizacion", str(org_id))
            .eq("id_propietario", str(user_id))
            .execute()
        )

        if not org_response.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para agregar miembros",
            )

        # Crear miembro
        miembro_data = {
            "id_organizacion": str(org_id),
            "email": miembro.email,
            "estado": miembro.estado,
            "fecha_union": datetime.now(timezone.utc).isoformat(),
        }

        response = supabase_admin.get_table("miembros").insert(miembro_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error invitando miembro",
            )

        logger.info(f"[INFO] Member {miembro.email} invited to org {org_id}")
        return response.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to invite member: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error invitando miembro",
        )


@router.get("/{org_id}/miembros", response_model=List[MiembroRead])
async def list_members(
    org_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Listar miembros de una organización.
    Solo el propietario puede verlos.
    """
    try:
        # Verificar permisos
        org_response = (
            supabase_admin.get_table("organizaciones")
            .select("id_organizacion")
            .eq("id_organizacion", str(org_id))
            .eq("id_propietario", str(user_id))
            .execute()
        )

        if not org_response.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para ver los miembros",
            )

        response = (
            supabase_admin.get_table("miembros")
            .select("*")
            .eq("id_organizacion", str(org_id))
            .execute()
        )

        return response.data or []

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to list members: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo miembros",
        )


@router.delete("/{org_id}/miembros/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: UUID,
    member_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Remover un miembro de la organización (Soft Delete).
    Solo el propietario puede hacerlo.
    """
    try:
        # Verificar permisos
        org_response = (
            supabase_admin.get_table("organizaciones")
            .select("id_organizacion")
            .eq("id_organizacion", str(org_id))
            .eq("id_propietario", str(user_id))
            .execute()
        )

        if not org_response.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos",
            )

        # Soft delete del miembro
        supabase_admin.get_table("miembros").update(
            {
                "estado": "suspendido",
                "fecha_salida": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id_miembro", str(member_id)).eq("id_organizacion", str(org_id)).execute()

        logger.info(f"[INFO] Member {member_id} removed from org {org_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to remove member: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error removiendo miembro",
        )
