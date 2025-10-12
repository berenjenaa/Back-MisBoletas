from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas.user import UserRead, UserCreate, UserLogin, LoginResponse, PasswordChangeRequest, AccountDeleteRequest
from app.crud import user as crud_user
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()

# Obtener todos los usuarios
@router.get("/users", response_model=List[UserRead])
async def get_users(db: Session = Depends(get_db)):
    """Obtiene la lista completa de usuarios registrados."""
    usuarios = crud_user.get_users_list(db)
    if not usuarios:
        raise HTTPException(status_code=404, detail="No hay usuarios registrados")
    return usuarios

# Obtener un usuario por ID
@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Obtiene la información de un usuario específico por ID."""
    usuario = crud_user.search_user(db, user_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

# Crear un usuario nuevo
@router.post("/users", response_model=LoginResponse, status_code=201)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Registra un nuevo usuario en el sistema y devuelve token de acceso."""
    try:
        # Crear usuario
        nuevo_usuario = crud_user.create_user(db, user)
        
        # Crear token JWT automáticamente
        access_token = create_access_token(
            data={"sub": nuevo_usuario.correo, "user_id": nuevo_usuario.idUsuario}
        )
        
        # Devolver respuesta con token y datos del usuario
        user_response = UserRead(
            idUsuario=nuevo_usuario.idUsuario,
            nombre=nuevo_usuario.nombre,
            correo=nuevo_usuario.correo,
            fechaRegistro=nuevo_usuario.fechaRegistro
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear usuario: {str(e)}")

# LOGIN - Autenticar usuario
@router.post("/auth/login", response_model=LoginResponse)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Autentica un usuario y genera un token de acceso."""
    try:
        # Buscar usuario por email
        user_data = crud_user.get_user_for_login(db, user_credentials.correo)
        
        if not user_data:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        
        # Verificar contraseña
        if not verify_password(user_credentials.contrasena, user_data["contrasenaHash"]):
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        
        # Crear token JWT
        access_token = create_access_token(
            data={"sub": user_data["correo"], "user_id": user_data["idUsuario"]}
        )
        
        # Crear respuesta con token y datos del usuario
        user_response = UserRead(
            idUsuario=user_data["idUsuario"],
            nombre=user_data["nombre"],
            correo=user_data["correo"],
            fechaRegistro=user_data["fechaRegistro"]
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno en el login: {str(e)}")

# Actualizar un usuario existente
@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    """Actualiza la información de un usuario existente."""
    return crud_user.update_user(db, user_id, user)

# Eliminar un usuario
@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Elimina un usuario del sistema."""
    crud_user.delete_user(db, user_id)
    return {"message": "Usuario eliminado"}

# ===== ENDPOINTS ESENCIALES PARA GESTIÓN DE CUENTA =====

# Cambiar contraseña del usuario actual
@router.put("/auth/change-password", response_model=UserRead)
async def change_password(
    password_data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Permite al usuario autenticado cambiar su contraseña."""
    try:
        return crud_user.update_user_password(
            db, 
            current_user.idUsuario, 
            password_data.nueva_contrasena
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cambiar contraseña: {str(e)}")

# Eliminar cuenta del usuario actual
@router.delete("/auth/delete-account")
async def delete_my_account(
    delete_data: AccountDeleteRequest,
    db: Session = Depends(get_db),
    current_user: UserRead = Depends(get_current_user)
):
    """Permite al usuario autenticado eliminar su propia cuenta y todos sus datos."""
    if not delete_data.confirmar_eliminacion:
        raise HTTPException(
            status_code=400,
            detail="Debe confirmar explícitamente la eliminación de la cuenta"
        )
    
    try:
        result = crud_user.delete_user_account(db, current_user.idUsuario)
        return {
            "message": "Cuenta eliminada exitosamente",
            "detail": "Se han eliminado todos tus datos y productos asociados",
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar cuenta: {str(e)}")
