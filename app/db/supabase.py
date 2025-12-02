"""
Cliente singleton para Supabase.
Reemplaza session.py de SQLAlchemy.

Proporciona:
- Conexión única a Supabase (anon key para cliente)
- Conexión admin con service role key para backend
- Acceso a tablas mediante métodos de conveniencia
- Gestión de transacciones
"""

from typing import Optional
from supabase import create_client, Client
from app.core.config import settings


class SupabaseClient:
    """
    Cliente Singleton para Supabase con anon key.
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

    def rpc(self, function_name: str, params: dict = None):
        """Llamar a una función RPC en Supabase."""
        if params is None:
            params = {}
        return self.client.rpc(function_name, params)

    def is_connected(self) -> bool:
        """Verificar si hay conexión activa."""
        try:
            return self._client is not None
        except Exception:
            return False


class SupabaseAdminClient:
    """
    Cliente Admin Singleton para Supabase con service role key.
    Bypassa RLS policies para operaciones backend.
    """

    _instance: Optional["SupabaseAdminClient"] = None
    _client: Optional[Client] = None

    def __new__(cls):
        """Patrón Singleton: crear una única instancia."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Inicializar el cliente admin de Supabase."""
        if self._client is None:
            try:
                # Solo inicializar si hay service role key
                if settings.SUPABASE_SERVICE_ROLE_KEY:
                    self._client = create_client(
                        supabase_url=settings.SUPABASE_URL,
                        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                    )
                    print(
                        "[OK] Supabase admin client initialized successfully with SERVICE_ROLE_KEY"
                    )
                else:
                    print("[WARNING] SUPABASE_SERVICE_ROLE_KEY not configured")
            except Exception as e:
                print(f"[ERROR] Error initializing Supabase admin client: {e}")

    @property
    def client(self) -> Client:
        """Obtener el cliente admin de Supabase."""
        if self._client is not None:
            return self._client
        else:
            # Usar anon key como fallback si no hay admin client
            return supabase.client

    def get_table(self, table_name: str):
        """Obtener referencia a una tabla de Supabase (admin)."""
        return self.client.table(table_name)

    def rpc(self, function_name: str, params: dict = None):
        """Llamar a una función RPC en Supabase (admin)."""
        if params is None:
            params = {}
        return self.client.rpc(function_name, params)

    def is_connected(self) -> bool:
        """Verificar si hay conexión activa."""
        try:
            return self._client is not None
        except Exception:
            return False


# Instancia global del cliente Supabase
supabase: SupabaseClient = SupabaseClient()

# Instancia global del cliente Supabase Admin
supabase_admin: SupabaseAdminClient = SupabaseAdminClient()


def get_supabase() -> SupabaseClient:
    """
    Dependencia para FastAPI: obtener el cliente Supabase (anon key).

    Usa RLS policies - respeta permisos del usuario.
    """
    return supabase


def get_supabase_admin() -> SupabaseAdminClient:
    """
    Dependencia para FastAPI: obtener el cliente admin de Supabase (service role key).

    Bypassea RLS policies - solo para operaciones backend confiables.
    """
    return supabase_admin
