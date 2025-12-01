# En app/api/v1/tickets.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_mail import FastMail, MessageSchema, MessageType
from typing import List
from uuid import UUID
import logging
from datetime import datetime

from app.schemas.tickets import TicketRead, TicketCreate
from app.core.config import supabase, settings
from app.core.dependencies import get_current_user_id, get_current_user, get_active_user_id
from app.core.email_config import fast_mail
from app.core.dependencies import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])


# =======================================================================
# === ENDPOINTS DE TICKETS DE SOPORTE (SUPABASE)
# =======================================================================


@router.post(
    "",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo ticket de soporte",
)
async def create_ticket(
    ticket_data: TicketCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Crea un nuevo ticket de soporte.

    El usuario autenticado puede reportar un problema con asunto, mensaje y prioridad.
    El estado inicial es 'abierto'.
    Además, se envía un email de confirmación.
    """
    try:
        user_id = current_user.id
        email_usuario = current_user.email

        # 1. Insertar ticket en Supabase usando RPC
        # Cambio: Usar RPC en lugar de insert directo
        response = supabase.rpc(
            "api_crear_ticket",
            {
                "p_id_usuario": str(user_id),
                "p_asunto": ticket_data.asunto,
                "p_descripcion": ticket_data.mensaje,
                "p_prioridad": ticket_data.prioridad or "media",
            },
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al crear el ticket",
            )

        ticket = response.data[0]

        # 2. Enviar email de confirmación de forma asíncrona
        try:
            asunto_email = f"Nuevo Ticket de {email_usuario}: {ticket_data.asunto}"

            # Crear el mensaje HTML del email
            mensaje_html = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; }}
                        .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                        .content {{ background-color: white; padding: 20px; border-radius: 0 0 5px 5px; }}
                        .footer {{ margin-top: 20px; font-size: 12px; color: #666; text-align: center; }}
                        .ticket-id {{ background-color: #ecf0f1; padding: 10px; border-radius: 5px; margin: 10px 0; font-weight: bold; }}
                        .prioridad {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
                        .prioridad-baja {{ background-color: #3498db; color: white; }}
                        .prioridad-media {{ background-color: #f39c12; color: white; }}
                        .prioridad-alta {{ background-color: #e74c3c; color: white; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>✓ Ticket de Soporte Registrado</h1>
                        </div>
                        <div class="content">
                            <p>¡Hola!</p>
                            <p>Tu ticket de soporte ha sido registrado exitosamente. Nuestro equipo te contactará pronto.</p>
                            
                            <div class="ticket-id">
                                ID del Ticket: {ticket['id_ticket']}
                            </div>
                            
                            <h3>Detalles del Ticket:</h3>
                            <ul>
                                <li><strong>Asunto:</strong> {ticket_data.asunto}</li>
                                <li><strong>Mensaje:</strong> {ticket_data.mensaje}</li>
                                <li><strong>Prioridad:</strong> <span class="prioridad prioridad-{ticket_data.prioridad}">{ticket_data.prioridad}</span></li>
                                <li><strong>Estado:</strong> Abierto</li>
                                <li><strong>Fecha de Creación:</strong> {ticket['fecha_creacion']}</li>
                            </ul>
                            
                            <p>Puedes verificar el estado de tu ticket en cualquier momento en nuestra plataforma.</p>
                        </div>
                        <div class="footer">
                            <p>Este es un email automático, por favor no responder a este correo.</p>
                            <p>MisBoletas Support Team</p>
                        </div>
                    </div>
                </body>
            </html>
            """

            # Enviar email solo si está configurado
            if fast_mail:
                # Crear objeto de mensaje
                message = MessageSchema(
                    subject=asunto_email,
                    recipients=[
                        settings.MAIL_FROM
                    ],  # Enviar a la dirección configurada
                    body=mensaje_html,
                    subtype=MessageType.html,
                )

                # Enviar email
                await fast_mail.send_message(message)
                logger.info(f"[INFO] Email sent for ticket {ticket['id_ticket']}")
            else:
                logger.warning(
                    f"[WARNING] Email not configured - skipping notification for ticket {ticket['id_ticket']}"
                )
        except Exception as e:
            logger.warning(f"[WARNING] Failed to send email for ticket: {e}")
            # No lanzar excepción aquí, el ticket fue creado exitosamente

        return TicketRead(**ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to create ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear el ticket. Por favor intenta más tarde.",
        )


@router.get("", response_model=List[TicketRead], summary="Listar mis tickets")
async def get_tickets(
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Obtiene todos los tickets de soporte del usuario autenticado.

    Solo el usuario puede ver sus propios tickets.
    Los tickets se ordenan por fecha de creación (más recientes primero).
    """
    try:
        # Cambio: Usar RPC en lugar de select directo
        response = supabase.rpc(
            "api_listar_tickets", {"p_id_usuario": str(user_id)}
        ).execute()

        tickets = response.data or []
        return [TicketRead(**t) for t in tickets]

    except Exception as e:
        logger.error(f"[ERROR] Failed to list tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener tickets. Por favor intenta más tarde.",
        )


@router.get(
    "/{ticket_id}", response_model=TicketRead, summary="Obtener un ticket por ID"
)
async def get_ticket(
    ticket_id: UUID,
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Obtiene un ticket específico por ID (con verificación de ownership).
    """
    try:
        # Cambio: Usar RPC en lugar de select directo
        response = supabase.rpc(
            "api_obtener_ticket",
            {"p_id_ticket": str(ticket_id), "p_id_usuario": str(user_id)},
        ).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket no encontrado",
            )

        ticket = response.data[0]
        return TicketRead(**ticket)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to get ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el ticket. Por favor intenta más tarde.",
        )
