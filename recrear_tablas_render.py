"""
Script para eliminar y recrear tablas de categorías en Render PostgreSQL.
Usa la DATABASE_URL del archivo .env
"""

import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError

def recrear_tablas_categorias_render():
    """
    Conecta a Render PostgreSQL y recrea las tablas de categorías.
    """
    print("=" * 80)
    print("RECREAR TABLAS DE CATEGORÍAS EN RENDER")
    print("=" * 80)
    
    # Obtener DATABASE_URL del entorno o .env
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("\n❌ ERROR: No se encuentra DATABASE_URL en las variables de entorno")
        print("\n💡 Opciones:")
        print("   1. Crea un archivo .env.render con:")
        print("      DATABASE_URL=postgres://usuario:password@host.render.com:5432/db")
        print("   2. O pasa la URL como argumento al script")
        return False
    
    # PostgreSQL en Render usa 'postgresql://' no 'postgres://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    print(f"\n🔗 Conectando a: {database_url[:30]}...****")
    
    try:
        # Crear engine con la URL de Render
        engine = create_engine(database_url)
        
        # Probar conexión
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Conectado a PostgreSQL")
            print(f"   Versión: {version[:50]}...")
        
        inspector = inspect(engine)
        
        # 1. Verificar qué tablas existen
        print("\n📊 Tablas existentes:")
        tables = inspector.get_table_names()
        for table in tables:
            print(f"   - {table}")
        
        # 2. Eliminar tabla productocategorias si existe
        if "productocategorias" in tables:
            print("\n❌ Eliminando tabla productocategorias...")
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS productocategorias CASCADE;"))
                conn.commit()
            print("✅ Tabla productocategorias eliminada")
        
        # 3. Eliminar tabla categorias si existe
        if "categorias" in tables:
            print("❌ Eliminando tabla categorias...")
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS categorias CASCADE;"))
                conn.commit()
            print("✅ Tabla categorias eliminada")
        
        # 4. Crear las tablas nuevas
        print("\n➕ Creando tabla categorias...")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE categorias (
                    categoriaid SERIAL PRIMARY KEY,
                    nombrecategoria VARCHAR(100) NOT NULL,
                    color VARCHAR(7) DEFAULT '#007BFF',
                    usuarioid INTEGER NOT NULL REFERENCES usuarios(usuarioid) ON DELETE CASCADE,
                    fechacreacion TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            conn.commit()
        print("✅ Tabla categorias creada")
        
        print("➕ Creando tabla productocategorias...")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE productocategorias (
                    id SERIAL PRIMARY KEY,
                    productoid INTEGER NOT NULL REFERENCES productos(productoid) ON DELETE CASCADE,
                    categoriaid INTEGER NOT NULL REFERENCES categorias(categoriaid) ON DELETE CASCADE,
                    fechaasignacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(productoid, categoriaid)
                );
            """))
            conn.commit()
        print("✅ Tabla productocategorias creada")
        
        # 5. Crear índices
        print("\n📊 Creando índices...")
        with engine.connect() as conn:
            conn.execute(text("CREATE INDEX idx_categorias_usuarioid ON categorias(usuarioid);"))
            conn.execute(text("CREATE INDEX idx_productocategorias_productoid ON productocategorias(productoid);"))
            conn.execute(text("CREATE INDEX idx_productocategorias_categoriaid ON productocategorias(categoriaid);"))
            conn.commit()
        print("✅ Índices creados")
        
        # 6. Verificar estructura final
        print("\n📋 Estructura final de tablas:")
        inspector = inspect(engine)
        
        if inspector.has_table("categorias"):
            cols = [col['name'] for col in inspector.get_columns('categorias')]
            print(f"   ✅ categorias: {', '.join(cols)}")
        
        if inspector.has_table("productocategorias"):
            cols = [col['name'] for col in inspector.get_columns('productocategorias')]
            print(f"   ✅ productocategorias: {', '.join(cols)}")
        
        print("\n" + "=" * 80)
        print("✅ ¡TABLAS RECREADAS EXITOSAMENTE!")
        print("=" * 80)
        print("\n💡 Ahora redespliega tu backend desde Render Dashboard")
        print("   O espera unos minutos si ya está en auto-deploy")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"\nTipo de error: {type(e).__name__}")
        import traceback
        print(f"\nTraceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    import sys
    
    # Permitir pasar DATABASE_URL como argumento
    if len(sys.argv) > 1:
        os.environ["DATABASE_URL"] = sys.argv[1]
    
    success = recrear_tablas_categorias_render()
    sys.exit(0 if success else 1)
