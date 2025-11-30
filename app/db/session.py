from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from typing import Generator

# Usamos directamente la DATABASE_URL que es leída desde el .env
SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL

# Configuración de conexión para Supabase (requiere SSL)
connect_args = {
    "sslmode": "require",  # Obligatorio para Supabase
    "connect_timeout": 10,
}

# Crear el motor de SQLAlchemy
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    echo=False,  # Cambiar a True para debug
    connect_args=connect_args,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # Reciclar conexiones cada hora
)

# Crear la sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()

# Dependencia para obtener la sesión de la base de datos (inyección de dependencias de FastAPI)
def get_db() -> Generator:
    """Proporciona una sesión de base de datos y la cierra al finalizar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
