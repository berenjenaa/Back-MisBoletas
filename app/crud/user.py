"""
CRUD operations para Usuarios usando funciones de PostgreSQL.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from typing import List, Optional

from app.models.user import Usuario
from app.schemas.user import UserCreate, UserRead
from app.core.security import hash_password

# ===== CREAR USUARIO (REGISTER) =====
def create_user(db: Session, user: UserCreate) -> UserRead:
    """Crea un nuevo usuario usando la función PostgreSQL fn_createuser."""
    try:
        result = db.execute(
            text("""
                SELECT * FROM fn_createuser(:nombre, :email, :password)
            """),
            {
                "nombre": user.nombre,
                "email": user.correo,
                "password": hash_password(user.contrasena)
            }
        )
        
        # Obtener el resultado
        created_user = result.fetchone()
        
        # Hacer commit después de obtener los datos
        db.commit()
        
        if not created_user:
            raise HTTPException(status_code=400, detail="Error al crear usuario")
            
        return UserRead(
            idUsuario=created_user.usuarioid,
            nombre=created_user.nombreusuario,
            correo=created_user.email,
            fechaRegistro=created_user.fecharegistro
        )
        
    except Exception as e:
        db.rollback()
        error_message = str(e)
        if "ya está registrado" in error_message:
            raise HTTPException(status_code=400, detail="El email ya está registrado")
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {error_message}")

# ===== OBTENER USUARIO PARA LOGIN =====
def get_user_for_login(db: Session, email: str) -> Optional[dict]:
    """Obtiene usuario usando la función PostgreSQL fn_getuserforlogin."""
    try:
        result = db.execute(
            text("""
                SELECT * FROM fn_getuserforlogin(:email)
            """),
            {"email": email}
        )
        user = result.fetchone()
        
        if not user:
            return None
            
        return {
            "idUsuario": user.usuarioid,
            "nombre": user.nombreusuario,
            "correo": user.email,
            "contrasenaHash": user.contrasenahash,
            "fechaRegistro": user.fecharegistro
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en autenticación: {str(e)}")

# ===== ACTUALIZAR CONTRASEÑA =====
def update_user_password(db: Session, user_id: int, new_password: str) -> UserRead:
    """Actualiza la contraseña usando la función PostgreSQL fn_updateuserpassword."""
    try:
        result = db.execute(
            text("""
                SELECT * FROM fn_updateuserpassword(:user_id, :password)
            """),
            {
                "user_id": user_id,
                "password": hash_password(new_password)
            }
        )
        
        updated_user = result.fetchone()
        db.commit()
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        return UserRead(
            idUsuario=updated_user.usuarioid,
            nombre=updated_user.nombreusuario,
            correo=updated_user.email,
            fechaRegistro=updated_user.fecharegistro
        )
        
    except Exception as e:
        db.rollback()
        error_message = str(e)
        if "no encontrado" in error_message:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        raise HTTPException(status_code=500, detail=f"Error al actualizar contraseña: {error_message}")

# ===== ELIMINAR CUENTA =====
def delete_user(db: Session, user_id: int) -> None:
    """Elimina un usuario usando la función PostgreSQL fn_deleteuseraccount."""
    try:
        result = db.execute(
            text("""
                SELECT fn_deleteuseraccount(:user_id) as message
            """),
            {"user_id": user_id}
        )
        
        response = result.fetchone()
        db.commit()
        
        if not response:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
    except Exception as e:
        db.rollback()
        error_message = str(e)
        if "no encontrado" in error_message:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        raise HTTPException(status_code=500, detail=f"Error al eliminar usuario: {error_message}")

# ===== LISTAR USUARIOS =====
def get_users_list(db: Session) -> List[UserRead]:
    """Lista todos los usuarios."""
    try:
        result = db.execute(
            text("""
                SELECT usuarioid, nombreusuario, email, fecharegistro 
                FROM usuarios 
                ORDER BY fecharegistro DESC
            """)
        )
        users = result.fetchall()
        
        return [
            UserRead(
                idUsuario=user.usuarioid,
                nombre=user.nombreusuario,
                correo=user.email,
                fechaRegistro=user.fecharegistro
            ) for user in users
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar usuarios: {str(e)}")

# ===== BUSCAR USUARIO POR ID =====
def search_user(db: Session, user_id: int) -> Optional[UserRead]:
    """Busca un usuario por ID."""
    try:
        result = db.execute(
            text("""
                SELECT usuarioid, nombreusuario, email, fecharegistro 
                FROM usuarios 
                WHERE usuarioid = :user_id
            """),
            {"user_id": user_id}
        )
        user = result.fetchone()
        
        if not user:
            return None
            
        return UserRead(
            idUsuario=user.usuarioid,
            nombre=user.nombreusuario,
            correo=user.email,
            fechaRegistro=user.fecharegistro
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al buscar usuario: {str(e)}")

# ===== ACTUALIZAR USUARIO =====
def update_user(db: Session, user_id: int, user: UserCreate) -> UserRead:
    """Actualiza los datos de un usuario."""
    try:
        # Primero verificar si existe el usuario
        result = db.execute(
            text("""
                SELECT usuarioid FROM usuarios WHERE usuarioid = :user_id
            """),
            {"user_id": user_id}
        )
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Luego actualizar los datos
        result = db.execute(
            text("""
                UPDATE usuarios 
                SET nombreusuario = :nombre,
                    email = :email,
                    contrasenahash = CASE 
                        WHEN :password IS NOT NULL THEN :password 
                        ELSE contrasenahash 
                    END
                WHERE usuarioid = :user_id
                RETURNING usuarioid, nombreusuario, email, fecharegistro
            """),
            {
                "user_id": user_id,
                "nombre": user.nombre,
                "email": user.correo,
                "password": hash_password(user.contrasena) if user.contrasena else None
            }
        )
        
        updated_user = result.fetchone()
        db.commit()
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="Error al actualizar usuario")
            
        return UserRead(
            idUsuario=updated_user.usuarioid,
            nombre=updated_user.nombreusuario,
            correo=updated_user.email,
            fechaRegistro=updated_user.fecharegistro
        )
        
    except Exception as e:
        db.rollback()
        error_message = str(e)
        if "duplicate key" in error_message.lower():
            raise HTTPException(status_code=400, detail="El email ya está registrado")
        raise HTTPException(status_code=500, detail=f"Error al actualizar usuario: {error_message}")