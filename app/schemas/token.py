# En app/schemas/token.py

from pydantic import BaseModel
from typing import Optional

# Importamos UserRead para anidarlo en la respuesta de login
from .user import UserRead


class Token(BaseModel):
    """
    Schema para la respuesta del token simple (como en /login).
    """

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Schema para los datos contenidos DENTRO del token JWT.
    Esto es lo que lee la función 'decode_access_token'
    """

    email: Optional[str] = None


class LoginResponse(BaseModel):
    """
    Schema para la respuesta completa al registrarse o iniciar sesión.
    """

    access_token: str
    token_type: str
    user: UserRead
