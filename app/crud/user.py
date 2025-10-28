from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from app.models.user import Usuario  # <-- Importamos el modelo
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.core.security import hash_password


# ===== CREAR USUARIO (REGISTER) =====
def create_user(db: Session, user: UserCreate) -> Usuario:  # <-- Devuelve el modelo
    """
    Crea un nuevo usuario en la base de datos.
    """
    existing = db.query(Usuario).filter(Usuario.Email == user.correo).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El email ya está registrado")

    db_user = Usuario(
        NombreUsuario=user.nombre,
        Email=user.correo,
        ContrasenaHash=hash_password(user.contrasena),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Devuelve el objeto Usuario, no el schema UserRead
    return db_user


# ===== OBTENER USUARIO (Login y Dependencias) =====
def get_user_for_login(db: Session, email: str) -> Optional[Usuario]:  # <-- CORRECCIÓN
    """
    Obtiene el objeto Usuario completo desde la BD.
    """
    # CORRECCIÓN: Simplemente devuelve el objeto modelo de SQLAlchemy
    user = db.query(Usuario).filter(Usuario.Email == email).first()
    return user


# ===== ACTUALIZAR CONTRASEÑA =====
def update_user_password(
    db: Session, user_id: int, new_password: str
) -> Usuario:  # <-- CORRECCIÓN
    """
    Actualiza la contraseña de un usuario específico.
    """
    user = db.query(Usuario).filter(Usuario.UsuarioID == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    user.ContrasenaHash = hash_password(new_password)
    db.commit()
    db.refresh(user)

    return user  # <-- Devuelve el objeto


# ===== ELIMINAR USUARIO =====
def delete_user(db: Session, user_id: int) -> None:
    """
    Elimina un usuario de la base de datos.
    """
    user = db.query(Usuario).filter(Usuario.UsuarioID == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    db.delete(user)
    db.commit()


# ===== OBTENER LISTA DE USUARIOS (Admin) =====
def get_users_list(db: Session) -> List[Usuario]:  # <-- CORRECCIÓN
    """
    Obtiene una lista de todos los usuarios.
    """
    users = db.query(Usuario).order_by(Usuario.FechaRegistro.desc()).all()
    return users


# ===== BUSCAR USUARIO POR ID (Admin) =====
def search_user(db: Session, user_id: int) -> Optional[Usuario]:  # <-- CORRECCIÓN
    """
    Busca un usuario por su ID.
    """
    user = db.query(Usuario).filter(Usuario.UsuarioID == user_id).first()
    return user


# ===== ACTUALIZAR USUARIO (Admin o /me) =====
def update_user(
    db: Session, user_id: int, user_data: UserUpdate
) -> Usuario:  # <-- CORRECCIÓN
    """
    Actualiza un usuario usando el schema UserUpdate (solo campos opcionales).
    """
    db_user = db.query(Usuario).filter(Usuario.UsuarioID == user_id).first()
    if not db_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    # Obtiene solo los datos que SÍ se enviaron en el JSON
    update_data = user_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)

    return db_user
