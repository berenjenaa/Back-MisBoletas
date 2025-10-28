# En app/core/security.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.schemas.token import TokenData

# --- 1. Esquema de Seguridad (Actualizado) ---
# Apunta directamente al endpoint de login dentro del router de usuarios
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")


# --- 2. Configuración de Hasheo de Contraseñas ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra su hash."""
    return pwd_context.verify(plain_password, hashed_password)


# --- 3. Lógica de Creación/Decodificación de JWT ---
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un nuevo token de acceso JWT.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str, credentials_exception: HTTPException) -> TokenData:
    """
    Decodifica un token de acceso.
    Si falla, lanza la 'credentials_exception' provista.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    return token_data
