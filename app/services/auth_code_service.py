"""
Servicio de códigos de autenticación seguros.

En lugar de pasar tokens en URLs, usamos códigos temporales:
- El puente genera un código
- Se almacena en Supabase por 10 minutos
- La app envía el código al backend
- El backend valida y devuelve el token
- El código se marca como usado

Esto previene:
- Exposición de tokens en URLs
- Almacenamiento en historial del navegador
- Logging de tokens en servidores
"""

import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from app.db.supabase import supabase_admin

logger = logging.getLogger(__name__)


class AuthCodeService:
    """Servicio para generar y validar códigos de autenticación temporales."""

    CODE_LENGTH = 8
    CODE_EXPIRY_MINUTES = 10

    @staticmethod
    def generate_code() -> str:
        """Genera un código aleatorio seguro de 8 caracteres."""
        # Usar solo letras mayúsculas y números para evitar confusiones
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(alphabet) for _ in range(AuthCodeService.CODE_LENGTH))

    @staticmethod
    async def create_code(
        email: str,
        code_type: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Crea un código temporal y lo almacena en Supabase.

        Args:
            email: Email del usuario
            code_type: Tipo de código ('signup', 'recovery', etc)
            access_token: Token de Supabase (si aplica)
            refresh_token: Refresh token (si aplica)
            user_id: ID del usuario (si aplica)

        Returns:
            El código generado
        """
        try:
            code = AuthCodeService.generate_code()
            expires_at = (datetime.now() + timedelta(minutes=AuthCodeService.CODE_EXPIRY_MINUTES)).isoformat()

            data = {
                "code": code,
                "email": email,
                "type": code_type,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user_id": user_id,
                "expires_at": expires_at,
                "used": False,
            }

            response = supabase_admin.get_table("auth_codes").insert(data).execute()

            logger.info(f"[AUTH_CODE] Código creado para {email} tipo {code_type}")
            return code

        except Exception as e:
            logger.error(f"[AUTH_CODE] Error creando código: {e}")
            raise

    @staticmethod
    async def validate_code(code: str) -> Optional[Dict[str, Any]]:
        """
        Valida un código y retorna sus datos.

        Args:
            code: Código a validar

        Returns:
            Dict con los datos del código si es válido, None si no lo es
        """
        try:
            response = (
                supabase_admin.get_table("auth_codes")
                .select("*")
                .eq("code", code)
                .eq("used", False)
                .single()
                .execute()
            )

            code_data = response.data

            if not code_data:
                logger.warning(f"[AUTH_CODE] Código no encontrado o ya usado: {code}")
                return None

            # Verificar que no esté expirado
            expires_at = datetime.fromisoformat(code_data["expires_at"])
            if datetime.now() > expires_at:
                logger.warning(f"[AUTH_CODE] Código expirado: {code}")
                # Marcar como usado para no volver a procesarlo
                await AuthCodeService.mark_as_used(code)
                return None

            logger.info(f"[AUTH_CODE] Código validado: {code}")
            return code_data

        except Exception as e:
            logger.error(f"[AUTH_CODE] Error validando código: {e}")
            return None

    @staticmethod
    async def mark_as_used(code: str) -> None:
        """Marca un código como usado."""
        try:
            supabase_admin.get_table("auth_codes").update(
                {"used": True, "used_at": datetime.now().isoformat()}
            ).eq("code", code).execute()

            logger.info(f"[AUTH_CODE] Código marcado como usado: {code}")

        except Exception as e:
            logger.error(f"[AUTH_CODE] Error marcando código como usado: {e}")

    @staticmethod
    async def get_code_by_email(email: str, code_type: str) -> Optional[Dict[str, Any]]:
        """Obtiene el código más reciente sin usar para un email."""
        try:
            response = (
                supabase_admin.get_table("auth_codes")
                .select("*")
                .eq("email", email)
                .eq("type", code_type)
                .eq("used", False)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if response.data:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"[AUTH_CODE] Error obteniendo código: {e}")
            return None


# Usar de esta manera en los endpoints:
#
# 1. Al generar el puente:
#    code = await AuthCodeService.create_code(
#        email="user@example.com",
#        code_type="recovery",
#        access_token=access_token,
#        refresh_token=refresh_token,
#        user_id=user_id
#    )
#    deep_link = f"misboletas://reset-password?code={code}"
#
# 2. En la app, enviar el código:
#    POST /api/v1/auth/verify-code
#    { "code": "ABC12345" }
#
# 3. En el backend validar:
#    code_data = await AuthCodeService.validate_code(code)
#    if not code_data:
#        return error
#    access_token = code_data["access_token"]
#    await AuthCodeService.mark_as_used(code)
