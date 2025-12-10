from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List
from uuid import UUID
import logging
from datetime import datetime

from app.schemas.tickets import TicketRead, TicketCreate
from app.db.supabase import supabase_admin
from app.core.config import settings
from app.core.dependencies import get_current_user, get_active_user_id, CurrentUser
from app.core.email_config import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets")

# =======================================================================
# === FUNCIONES DE NOTIFICACIÓN
# =======================================================================


async def notificar_ticket_creado(
    datos_email: dict, email_usuario: str, ticket_id: str
):
    """
    Envía las alertas. Recibe un diccionario 'datos_email' que YA debe incluir la prioridad.
    """
    try:
        # --- CORREO 1: ALERTA A SOPORTE ---
        html_soporte = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e74c3c; border-radius: 8px;">
            <h2 style="color: #c0392b;">🔥 Nuevo Ticket de Soporte</h2>
            <p><strong>Usuario:</strong> {email_usuario}</p>
            <p><strong>ID Ticket:</strong> {ticket_id}</p>
            <p><strong>Prioridad:</strong> <span style="font-weight:bold; color:red">{datos_email['prioridad']}</span></p>
            <hr>
            <h3>Mensaje:</h3>
            <p style="background: #fdf2f2; padding: 15px; border-left: 4px solid #e74c3c;">{datos_email['mensaje']}</p>
        </div>
        """

        await send_email(
            recipient_email=settings.MAIL_SUPPORT,
            subject=f"[Soporte] {datos_email['asunto']} (P: {datos_email['prioridad']})",
            html_content=html_soporte,
        )
        logger.info(f"✅ Alerta enviada a soporte: {settings.MAIL_SUPPORT}")

        # --- CORREO 2: CONFIRMACIÓN AL USUARIO ---
        html_usuario = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
            <h2 style="color: #2c3e50;">Ticket Recibido</h2>
            <p>Hola,</p>
            <p>Hemos recibido tu solicitud "{datos_email['asunto']}".</p>
            <p>Nuestro equipo ya ha sido notificado y revisará tu caso.</p>
            <p><strong>ID de seguimiento:</strong> {ticket_id}</p>
            <hr>
            <p style="font-size: 12px; color: #999;">Equipo MisBoletas</p>
        </div>
        """

        await send_email(
            recipient_email=email_usuario,
            subject=f"Recibimos tu ticket: {datos_email['asunto']}",
            html_content=html_usuario,
        )

    except Exception as e:
        logger.error(f"❌ Error enviando notificaciones: {e}")


# =======================================================================
# === ENDPOINTS
# =======================================================================


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo ticket de soporte",
)
async def create_ticket(
    ticket_data: TicketCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        user_id = current_user.id
        email_usuario = current_user.email

        # 1. Definir prioridad por defecto (Regla de Negocio)
        PRIORIDAD_DEFAULT = "media"

        # 2. Insertar en Supabase
        ticket_payload = {
            "id_usuario": str(user_id),
            "asunto": ticket_data.asunto,
            "mensaje": ticket_data.mensaje,
            "prioridad": PRIORIDAD_DEFAULT,  # <--- ASIGNACIÓN AUTOMÁTICA
            "estado": "abierto",
            "fecha_creacion": datetime.now().isoformat(),
        }

        response = supabase_admin.get_table("tickets").insert(ticket_payload).execute()

        if not response.data:
            raise HTTPException(status_code=400, detail="Error al guardar el ticket")

        new_ticket = response.data[0]
        ticket_id = new_ticket.get("id_ticket") or new_ticket.get("id")

        # 3. Preparar datos para el correo (Inyectando la prioridad)
        # Como ticket_data (schema) ya no tiene prioridad, creamos un dict manual
        datos_para_email = ticket_data.dict()
        datos_para_email["prioridad"] = PRIORIDAD_DEFAULT  # <--- Agregamos lo que falta

        # 4. Enviar correos
        background_tasks.add_task(
            notificar_ticket_creado,
            datos_email=datos_para_email,  # Pasamos el dict completo
            email_usuario=email_usuario,
            ticket_id=str(ticket_id),
        )

        return TicketRead(**new_ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to create ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al procesar el ticket",
        )


# (Endpoints GET se mantienen igual...)
@router.get("", response_model=List[TicketRead])
async def get_tickets(user_id: UUID = Depends(get_active_user_id)):
    response = (
        supabase_admin.get_table("tickets")
        .select("*")
        .eq("id_usuario", str(user_id))
        .order("fecha_creacion", desc=True)
        .execute()
    )
    return [TicketRead(**t) for t in (response.data or [])]


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: UUID, user_id: UUID = Depends(get_active_user_id)):
    response = (
        supabase_admin.get_table("tickets")
        .select("*")
        .eq("id_ticket", str(ticket_id))
        .eq("id_usuario", str(user_id))
        .single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="No encontrado")
    return TicketRead(**response.data[0])
