"""
Cliente singleton para Supabase.
Reemplaza session.py de SQLAlchemy.

Proporciona:
- Conexión única a Supabase
- Acceso a tablas mediante métodos de conveniencia
- Gestión de transacciones
"""

from typing import Optional
from supabase import create_client, Client
from app.core.config import settings


class SupabaseClient:
    """
    Cliente Singleton para Supabase.
    Garantiza una única conexión a la base de datos.
    """

    _instance: Optional["SupabaseClient"] = None
    _client: Optional[Client] = None

    def __new__(cls):
        """Patrón Singleton: crear una única instancia."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Inicializar el cliente de Supabase."""
        if self._client is None:
            try:
                self._client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_KEY,
                )
                print("[OK] Supabase client initialized successfully")
            except Exception as e:
                print(f"[ERROR] Error initializing Supabase: {e}")
                raise

    @property
    def client(self) -> Client:
        """Obtener el cliente de Supabase."""
        if self._client is None:
            self._initialize()
        return self._client

    def get_table(self, table_name: str):
        """Obtener referencia a una tabla de Supabase."""
        return self.client.table(table_name)

    def is_connected(self) -> bool:
        """Verificar si hay conexión activa."""
        try:
            return self._client is not None
        except Exception:
            return False


# Instancia global del cliente Supabase
supabase: SupabaseClient = SupabaseClient()


def get_supabase() -> SupabaseClient:
    """
    Dependencia para FastAPI: obtener el cliente Supabase.

    Uso en endpoints:
        @app.get("/users")
        async def get_users(db: SupabaseClient = Depends(get_supabase)):
            users = db.get_table("usuarios").select("*").execute()
            return users
    """
    return supabase
