"""
Router para Alertas de Vencimiento de Garantías.
Verifica productos que están próximos a vencer y envía notificaciones.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
import logging

from app.core.dependencies import get_active_user_id
from app.db.supabase import supabase_admin
from app.core.email_config import send_email_sync

router = APIRouter(prefix="/alertas", tags=["Alertas"])
logger = logging.getLogger(__name__)


class ExpirationAlert:
    """Modelo para alertas de vencimiento."""

    def __init__(
        self,
        producto_id: UUID,
        nombre_producto: str,
        dias_para_vencer: int,
        fecha_vencimiento: str,
    ):
        self.producto_id = producto_id
        self.nombre_producto = nombre_producto
        self.dias_para_vencer = dias_para_vencer
        self.fecha_vencimiento = fecha_vencimiento


@router.post("/verificar-vencimientos")
async def check_expirations(
    user_id: UUID = Depends(get_active_user_id),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Endpoint POST para verificar productos próximos a vencer.
    Simula búsqueda de productos y envía alertas por email.

    LÓGICA:
    - Busca productos del usuario donde:
      fecha_compra + duracion_garantia_meses estén a 7 días de vencer
    - Envía email de alerta al usuario
    - Retorna lista de productos a vencer
    """
    try:
        # Obtener todos los productos del usuario
        products_response = (
            supabase_admin.get_table("productos")
            .select("*")
            .eq("id_usuario", str(user_id))
            .execute()
        )

        products = products_response.data or []

        if not products:
            return {
                "message": "No hay productos registrados",
                "expiring_soon": [],
                "email_sent": False,
            }

        # Buscar productos que vencen en los próximos 7 días
        expiring_soon: List[ExpirationAlert] = []
        today = datetime.utcnow().date()
        alert_window = today + timedelta(days=7)

        for product in products:
            if not product.get("fecha_compra") or not product.get(
                "duracion_garantia_meses"
            ):
                continue

            try:
                fecha_compra = datetime.fromisoformat(product["fecha_compra"]).date()
                duracion_meses = product["duracion_garantia_meses"]

                # Calcular fecha de vencimiento
                from dateutil.relativedelta import relativedelta

                fecha_vencimiento = fecha_compra + relativedelta(months=duracion_meses)

                # Verificar si vence en los próximos 7 días
                dias_para_vencer = (fecha_vencimiento - today).days

                if 0 <= dias_para_vencer <= 7:
                    alert = ExpirationAlert(
                        producto_id=UUID(product["id_producto"]),
                        nombre_producto=product["nombre"],
                        dias_para_vencer=dias_para_vencer,
                        fecha_vencimiento=fecha_vencimiento.isoformat(),
                    )
                    expiring_soon.append(alert)

            except Exception as e:
                logger.warning(
                    f"[WARNING] Could not calculate expiration for product {product.get('id_producto')}: {e}"
                )
                continue

        # Obtener email del usuario
        usuario_response = (
            supabase_admin.get_table("perfiles")
            .select("email")
            .eq("id_usuario", str(user_id))
            .execute()
        )

        usuario_email = None
        if usuario_response.data:
            usuario_email = usuario_response.data[0].get("email")

        # Si hay productos próximos a vencer, enviar email en background
        email_sent = False
        if expiring_soon and usuario_email:
            background_tasks.add_task(
                send_expiration_alert_email, usuario_email, expiring_soon
            )
            email_sent = True
            logger.info(
                f"[INFO] Scheduled expiration alert email for {usuario_email} with {len(expiring_soon)} products"
            )

        # Construir respuesta
        alerts_data = [
            {
                "producto_id": str(alert.producto_id),
                "nombre_producto": alert.nombre_producto,
                "dias_para_vencer": alert.dias_para_vencer,
                "fecha_vencimiento": alert.fecha_vencimiento,
                "urgencia": (
                    "CRITICA"
                    if alert.dias_para_vencer == 0
                    else ("ALTA" if alert.dias_para_vencer <= 3 else "MEDIA")
                ),
            }
            for alert in expiring_soon
        ]

        return {
            "message": f"Se encontraron {len(expiring_soon)} productos próximos a vencer",
            "expiring_soon": alerts_data,
            "email_sent": email_sent,
            "total_products_checked": len(products),
        }

    except Exception as e:
        logger.error(f"[ERROR] Failed to check expirations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verificando vencimientos",
        )


@router.get("/resumen")
async def get_alerts_summary(
    user_id: UUID = Depends(get_active_user_id),
):
    """
    Obtener resumen de alertas activas.
    Retorna conteo de productos por urgencia.
    """
    try:
        # Obtener todos los productos del usuario
        products_response = (
            supabase_admin.get_table("productos")
            .select("*")
            .eq("id_usuario", str(user_id))
            .execute()
        )

        products = products_response.data or []

        urgency_counts = {"CRITICA": 0, "ALTA": 0, "MEDIA": 0, "BAJA": 0}
        today = datetime.utcnow().date()

        for product in products:
            if not product.get("fecha_compra") or not product.get(
                "duracion_garantia_meses"
            ):
                continue

            try:
                fecha_compra = datetime.fromisoformat(product["fecha_compra"]).date()
                duracion_meses = product["duracion_garantia_meses"]

                from dateutil.relativedelta import relativedelta

                fecha_vencimiento = fecha_compra + relativedelta(months=duracion_meses)
                dias_para_vencer = (fecha_vencimiento - today).days

                if dias_para_vencer < 0:
                    continue  # Ya vencido, no contar
                elif dias_para_vencer == 0:
                    urgency_counts["CRITICA"] += 1
                elif dias_para_vencer <= 3:
                    urgency_counts["ALTA"] += 1
                elif dias_para_vencer <= 7:
                    urgency_counts["MEDIA"] += 1
                else:
                    urgency_counts["BAJA"] += 1

            except Exception as e:
                logger.warning(f"[WARNING] Error calculating urgency: {e}")
                continue

        total_alerts = sum(urgency_counts.values())

        return {
            "total_alerts": total_alerts,
            "urgency_breakdown": urgency_counts,
            "total_products": len(products),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"[ERROR] Failed to get alerts summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo resumen de alertas",
        )


# ===== FUNCIONES AUXILIARES =====


async def send_expiration_alert_email(
    recipient_email: str, alerts: List[ExpirationAlert]
) -> None:
    """
    Envía email de alerta de vencimiento.
    Se ejecuta en background task.
    """
    try:
        # Construir HTML del email
        alerts_html = ""
        for alert in alerts:
            urgencia = (
                "🔴 CRÍTICA"
                if alert.dias_para_vencer == 0
                else ("🟠 ALTA" if alert.dias_para_vencer <= 3 else "🟡 MEDIA")
            )
            alerts_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    {alert.nombre_producto}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    {alert.fecha_vencimiento}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">
                    {alert.dias_para_vencer} días
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">
                    {urgencia}
                </td>
            </tr>
            """

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>⏰ Alertas de Vencimiento de Garantías</h2>
                <p>Hola,</p>
                <p>Tienes <strong>{len(alerts)}</strong> producto(s) cuya garantía está próxima a vencer:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <thead>
                        <tr style="background-color: #f0f0f0;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Producto</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Vencimiento</th>
                            <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Días</th>
                            <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Urgencia</th>
                        </tr>
                    </thead>
                    <tbody>
                        {alerts_html}
                    </tbody>
                </table>

                <p>
                    <strong>Acciones recomendadas:</strong>
                    <ul>
                        <li>Revisa tus documentos y garantías en la app</li>
                        <li>Considera renovar garantías antes de que venza el plazo</li>
                        <li>Contáctate con el proveedor si es necesario</li>
                    </ul>
                </p>

                <p>
                    Saludos,<br>
                    <strong>Equipo MisBoletas</strong>
                </p>
            </body>
        </html>
        """

        # Enviar email de forma sincrónica (para background task)
        success = send_email_sync(
            recipient_email=recipient_email,
            subject="⏰ Alertas de Vencimiento de Garantías - MisBoletas",
            html_content=html_content,
        )

        if success:
            logger.info(f"[INFO] Expiration alert email sent to {recipient_email}")
        else:
            logger.warning(
                f"[WARNING] Failed to send expiration alert email to {recipient_email}"
            )

    except Exception as e:
        logger.error(
            f"[ERROR] Failed to send expiration alert email: {e}", exc_info=True
        )


# ===== FUNCIÓN PARA SCHEDULER DIARIO =====


async def check_expiring_products() -> None:
    """
    Función ejecutada DIARIAMENTE por el scheduler a las 09:00 AM.

    Verifica TODOS los productos de TODOS los usuarios y alerta en múltiples umbrales:
    - 7 días antes del vencimiento
    - 4 días antes del vencimiento
    - 2 días antes del vencimiento
    - 1 día antes del vencimiento
    - El día del vencimiento (día 0)

    Se ejecuta de forma asincrónica sin bloquear la API.
    """
    try:
        logger.info("[SCHEDULER] Iniciando verificación de productos vencidos...")

        # Obtener TODOS los usuarios con al menos un producto
        usuarios_alertados = 0
        productos_vencidos = 0

        try:
            # Obtener todos los productos de la BD
            productos_response = (
                supabase_admin.get_table("productos").select("*").execute()
            )

            todos_productos = productos_response.data or []

            if not todos_productos:
                logger.info("[SCHEDULER] No hay productos registrados")
                return

            logger.info(f"[SCHEDULER] Verificando {len(todos_productos)} productos...")

            # Agrupar productos por usuario
            productos_por_usuario: Dict[str, List[ExpirationAlert]] = {}
            today = datetime.utcnow().date()

            # Umbrales de alerta (días antes del vencimiento)
            ALERT_THRESHOLDS = [7, 4, 2, 1, 0]

            for product in todos_productos:
                if not product.get("fecha_compra") or not product.get(
                    "duracion_garantia_meses"
                ):
                    continue

                try:
                    fecha_compra = datetime.fromisoformat(
                        product["fecha_compra"]
                    ).date()
                    duracion_meses = product["duracion_garantia_meses"]
                    user_id = product.get("id_usuario")

                    if not user_id:
                        continue

                    # Calcular fecha de vencimiento
                    from dateutil.relativedelta import relativedelta

                    fecha_vencimiento = fecha_compra + relativedelta(
                        months=duracion_meses
                    )
                    dias_para_vencer = (fecha_vencimiento - today).days

                    # Verificar si coincide con alguno de los umbrales de alerta
                    if dias_para_vencer in ALERT_THRESHOLDS:
                        alert = ExpirationAlert(
                            producto_id=product["id_producto"],
                            nombre_producto=product.get(
                                "nombre", "Producto sin nombre"
                            ),
                            dias_para_vencer=dias_para_vencer,
                            fecha_vencimiento=fecha_vencimiento.isoformat(),
                        )

                        # Agrupar por usuario
                        if user_id not in productos_por_usuario:
                            productos_por_usuario[user_id] = []

                        productos_por_usuario[user_id].append(alert)
                        productos_vencidos += 1

                        # Log detallado
                        dias_texto = {
                            7: "7 DÍAS",
                            4: "4 DÍAS",
                            2: "2 DÍAS",
                            1: "1 DÍA",
                            0: "HOY",
                        }
                        logger.info(
                            f"[SCHEDULER] ⏰ {product['nombre']} vence {dias_texto[dias_para_vencer]} - Usuario: {user_id}"
                        )

                except Exception as e:
                    logger.warning(
                        f"[SCHEDULER WARNING] No se pudo procesar producto {product.get('id_producto')}: {e}"
                    )
                    continue

            # Enviar alertas a cada usuario
            for user_id, alerts in productos_por_usuario.items():
                try:
                    # Obtener email del usuario
                    usuario_response = (
                        supabase_admin.get_table("perfiles")
                        .select("email")
                        .eq("id_usuario", str(user_id))
                        .execute()
                    )

                    if usuario_response.data:
                        usuario_email = usuario_response.data[0].get("email")

                        if usuario_email:
                            # Enviar email de alerta
                            await send_expiration_alert_email(usuario_email, alerts)
                            usuarios_alertados += 1
                            logger.info(
                                f"[SCHEDULER] ✅ Email enviado a {usuario_email} ({len(alerts)} productos)"
                            )

                except Exception as e:
                    logger.error(
                        f"[SCHEDULER ERROR] No se pudo procesar usuario {user_id}: {e}"
                    )
                    continue

            # Log final del scheduler
            logger.info(
                f"[SCHEDULER] ✅ Verificación completada: {productos_vencidos} productos, "
                f"{usuarios_alertados} usuarios alertados"
            )

        except Exception as e:
            logger.error(
                f"[SCHEDULER ERROR] Error crítico en check_expiring_products: {e}",
                exc_info=True,
            )

    except Exception as e:
        logger.error(f"[SCHEDULER ERROR] Error no capturado: {e}", exc_info=True)
