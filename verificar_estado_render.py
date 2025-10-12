"""
Script para verificar el estado de las tablas de categorías en Render.
"""

import os
import sys

def verificar_tablas_render():
    """Verifica que las tablas de categorías tengan la estructura correcta."""
    
    from sqlalchemy import create_engine, text, inspect
    
    database_url = "postgresql://misboletas_user:huu5fmqT3OqshOqB2ZJ1KXNVcdWP7I7D@dpg-d3jd0n9r0fns7385rgb0-a.oregon-postgres.render.com/misboletas_a93l"
    
    print("=" * 80)
    print("VERIFICACIÓN DE TABLAS EN RENDER")
    print("=" * 80)
    
    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # 1. Verificar que existen las tablas
        print("\n📊 TABLAS EXISTENTES:")
        tables = inspector.get_table_names()
        for table in sorted(tables):
            print(f"   ✅ {table}")
        
        # 2. Verificar estructura de categorias
        if "categorias" in tables:
            print("\n📋 ESTRUCTURA DE 'categorias':")
            columns = inspector.get_columns('categorias')
            for col in columns:
                print(f"   - {col['name']}: {col['type']}")
        else:
            print("\n❌ Tabla 'categorias' NO EXISTE")
        
        # 3. Verificar estructura de productocategorias
        if "productocategorias" in tables:
            print("\n📋 ESTRUCTURA DE 'productocategorias':")
            columns = inspector.get_columns('productocategorias')
            for col in columns:
                print(f"   - {col['name']}: {col['type']}")
            
            # Verificar que tiene categoriaid y NO categoria
            col_names = [col['name'] for col in columns]
            if 'categoriaid' in col_names:
                print("\n   ✅ Tiene columna 'categoriaid' (CORRECTO)")
            else:
                print("\n   ❌ NO tiene columna 'categoriaid'")
            
            if 'categoria' in col_names:
                print("   ⚠️  Tiene columna 'categoria' (INCORRECTO - estructura antigua)")
        else:
            print("\n❌ Tabla 'productocategorias' NO EXISTE")
        
        # 4. Contar registros
        print("\n📊 CONTEO DE REGISTROS:")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM categorias"))
            count_categorias = result.scalar()
            print(f"   - categorias: {count_categorias} registro(s)")
            
            result = conn.execute(text("SELECT COUNT(*) FROM productocategorias"))
            count_pc = result.scalar()
            print(f"   - productocategorias: {count_pc} registro(s)")
        
        print("\n" + "=" * 80)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("=" * 80)
        
        # Verificar que la estructura es correcta
        if "categorias" in tables and "productocategorias" in tables:
            pc_cols = [col['name'] for col in inspector.get_columns('productocategorias')]
            if 'categoriaid' in pc_cols and 'categoria' not in pc_cols:
                print("\n🎉 ¡Las tablas tienen la estructura CORRECTA!")
                print("   Puedes probar crear categorías desde la app móvil")
                return True
            else:
                print("\n⚠️  Las tablas tienen estructura INCORRECTA")
                print("   Ejecuta recrear_tablas_render.py de nuevo")
                return False
        else:
            print("\n❌ Faltan tablas")
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        print(f"\nTraceback:\n{traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = verificar_tablas_render()
    sys.exit(0 if success else 1)
