from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.user import Usuario  # <-- Importamos el modelo
from app.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdate,
    UserUpdatePassword,
    UserLogin,
)
from app.schemas.token import LoginResponse, Token
from app.crud import user as crud_user
from app.core.security import create_access_token, verify_password
from app.core.dependencies import get_current_user  # , get_current_admin_user

router = APIRouter()

# =======================================================================
# === 1. ENDPOINTS PÚBLICOS (Registro y Login) 🔓
# =======================================================================


@router.post(
    "/users/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Auth"],
    summary="1. Registrar un nuevo usuario (para App)",
)
def register_new_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        nuevo_usuario_db = crud_user.create_user(db, user)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear usuario: {str(e)}")

    access_token = create_access_token(
        data={"sub": nuevo_usuario_db.Email}
    )  # <-- CORRECCIÓN

    # Pydantic convierte el objeto 'nuevo_usuario_db' a 'UserRead'
    user_response = UserRead.model_validate(nuevo_usuario_db)

    return LoginResponse(
        access_token=access_token, token_type="bearer", user=user_response
    )


# ================================================
# ENDPOINT DE LOGIN (PARA REACT NATIVE)
# ================================================
@router.post(
    "/users/login",
    response_model=LoginResponse,
    tags=["Auth"],
    summary="2. Iniciar sesión con JSON (para App)",
)
def login_user_with_json(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    (Este es el que te falló)
    """
    db_user = crud_user.get_user_for_login(db, email=user_credentials.correo)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    # --- CORRECCIÓN ---
    # Usamos acceso por atributo (objeto) en lugar de por clave (dict)
    if not verify_password(user_credentials.contrasena, db_user.ContrasenaHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )

    access_token = create_access_token(data={"sub": db_user.Email})

    # Pydantic valida el objeto db_user y lo convierte en el schema UserRead
    user_data = UserRead.model_validate(db_user)  # <-- ¡Esto ya no fallará!

    return LoginResponse(access_token=access_token, token_type="bearer", user=user_data)


# ================================================
# ENDPOINT DE TOKEN (PARA SWAGGER / OAUTH2)
# ================================================
@router.post(
    "/token",
    response_model=Token,
    tags=["Auth"],
    summary="3. Iniciar sesión con Form-Data (para Swagger)",
)
def login_for_access_token_form_data(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user_data = crud_user.get_user_for_login(db, email=form_data.username)

    # --- CORRECCIÓN ---
    # Usamos acceso por atributo (objeto)
    if not user_data or not verify_password(
        form_data.password, user_data.ContrasenaHash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user_data.Email})
    return Token(access_token=access_token, token_type="bearer")


# === 2. ENDPOINTS DE USUARIO AUTENTICADO (/me)


@router.get(
    "/users/me",
    response_model=UserRead,
    tags=["Usuarios"],
    summary="4. Obtener mi perfil de usuario",
)
def read_users_me(current_user: Usuario = Depends(get_current_user)):  # <-- CORRECCIÓN
    """
    Devuelve los datos del usuario actualmente autenticado.
    """
    # Pydantic valida el objeto 'current_user' y lo convierte
    return UserRead.model_validate(current_user)


@router.put(
    "/users/me",
    response_model=UserRead,
    tags=["Usuarios"],
    summary="5. Actualizar mi perfil (nombre/email)",
)
def update_my_profile(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),  # <-- CORRECCIÓN
):
    # --- CORRECCIÓN ---
    user_id = current_user.UsuarioID
    updated_user = crud_user.update_user(db, user_id, user_data)
    return UserRead.model_validate(updated_user)


@router.put(
    "/users/me/password",
    response_model=UserRead,
    tags=["Usuarios"],
    summary="6. Actualizar mi contraseña",
)
def update_my_password(
    password_data: UserUpdatePassword,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),  # <-- CORRECCIÓN
):
    # --- CORRECCIÓN ---
    user_id = current_user.UsuarioID
    if not verify_password(
        password_data.contrasena_actual, current_user.ContrasenaHash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual es incorrecta",
        )

    updated_user = crud_user.update_user_password(
        db, user_id, password_data.contrasena_nueva
    )
    return UserRead.model_validate(updated_user)


@router.delete(
    "/users/me",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Usuarios"],
    summary="7. Eliminar mi cuenta",
)
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),  # <-- CORRECCIÓN
):
    # --- CORRECCIÓN ---
    crud_user.delete_user(db, user_id=current_user.UsuarioID)
    return None


# =======================================================================
# === 3. ENDPOINTS DE ADMINISTRADOR (Comentados)
# =======================================================================
# (Requieren implementar 'is_admin' en el modelo y dependencia)
