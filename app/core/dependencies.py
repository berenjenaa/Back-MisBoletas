"""
Dependencias de autenticación para proteger endpoints.

Proporciona:
- get_current_user: Verifica token JWT y devuelve usuario actual
- get_current_user_id: Devuelve solo el ID del usuario
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError

# --- CORRECCIÓN 1: Importar la dependencia de seguridad correcta ---
# (Tu archivo security.py usa 'oauth2_scheme' pero no lo exportaba,
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/token"
)  # Asegúrate que esta URL sea la de form-data

# --- CORRECCIÓN 2: Importar la función con el nombre NUEVO ---
from app.core.security import decode_access_token
from app.crud import user as crud_user
from app.db.session import get_db
from app.models.user import Usuario

# =======================================================================
# === DEPENDENCIA DE USUARIO AUTENTICADO (Objeto Completo)
# =======================================================================


def get_current_user(
    token: str = Depends(oauth2_scheme),  # <-- Usamos el scheme
    db: Session = Depends(get_db),
) -> Usuario:  # <-- Devuelve el modelo SQLAlchemy, no el schema UserRead
    """
    Dependencia de FastAPI para obtener el objeto Usuario completo
    a partir del token en la cabecera Authorization.
    """

    # Define la excepción que se pasará a la función de decodificación
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Le pasamos el token y la excepción que debe lanzar si falla
        payload = decode_access_token(token, credentials_exception)

        # --- CORRECCIÓN 4: Acceder al email desde el objeto TokenData ---
        email: str = payload.email
        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # --- CORRECCIÓN 5: Buscar al usuario por EMAIL ---
    # buscar al usuario por email, no por ID.
    user = crud_user.get_user_for_login(db, email=email)

    if user is None:
        # Si el usuario no existe en la BD (ej. fue borrado pero el token aún es válido)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    # Devolvemos el objeto Usuario completo (el modelo SQLAlchemy)
    return user


# =======================================================================
# === DEPENDENCIA DE ID DE USUARIO (Para reducir código)
# =======================================================================


def get_current_user_id(current_user: Usuario = Depends(get_current_user)) -> int:
    """
    Dependencia simplificada que solo devuelve el ID del usuario actual.
    """
    return current_user.UsuarioID


# =======================================================================
# === DEPENDENCIA DE USUARIO ADMINISTRADOR (Comentado)
# =======================================================================

# def get_current_admin_user(
#     current_user: Usuario = Depends(get_current_user),
# ) -> Usuario:
#     """
#     (AÚN COMENTADO) - Requiere que el modelo 'Usuario' tenga 'is_admin'
#     """
#     if not current_user.is_admin:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="No tienes permisos de administrador",
#         )
#     return current_user
