#!/usr/bin/env python
"""
Script de validación de arquitectura post-migración.

Verifica que no haya residuos de SQLAlchemy/SQL Server en el codebase.
Puede ser usado en CI/CD para evitar regresiones.

Uso:
    python scripts/validate_architecture.py
"""

import os
import sys
from pathlib import Path

# Rutas a verificar - usar Path relativo
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parent.parent
BASE_PATH = PROJECT_ROOT / "app"

# Patrones que NO deben existir
FORBIDDEN_PATTERNS = [
    "from app.crud",
    "from app.models",
    "from app.db.session",
    "from sqlalchemy",
    "import sqlalchemy",
    "from sqlalchemy",
    "SQLAlchemy",
    "ORM",
    "declarative_base",
    "Column(",
    "__tablename__",
]

# Directorios que DEBEN estar eliminados
FORBIDDEN_DIRS = [
    BASE_PATH / "crud",
    BASE_PATH / "models",
]

# Archivos que DEBEN estar eliminados
FORBIDDEN_FILES = [
    BASE_PATH / "db" / "session.py",
    BASE_PATH / "db" / "base.py",
    BASE_PATH / "services" / "product_service.py",
]


def validate_directories():
    """Verifica que las carpetas obsoletas no existan."""
    print("[*] Validando que carpetas obsoletas fueron eliminadas...")
    for forbidden_dir in FORBIDDEN_DIRS:
        if forbidden_dir.exists():
            print(f"[ERROR] Carpeta obsoleta aún existe: {forbidden_dir}")
            return False
        print(f"[OK] No encontrada: {forbidden_dir.relative_to(BASE_PATH.parent)}")
    return True


def validate_files():
    """Verifica que los archivos obsoletos no existan."""
    print("\n[*] Validando que archivos obsoletos fueron eliminados...")
    for forbidden_file in FORBIDDEN_FILES:
        if forbidden_file.exists():
            print(f"[ERROR] Archivo obsoleto aún existe: {forbidden_file}")
            return False
        print(f"[OK] No encontrado: {forbidden_file.relative_to(BASE_PATH.parent)}")
    return True


def validate_imports():
    """Verifica que no haya imports de módulos eliminados."""
    print("\n[*] Validando imports en archivos .py...")

    errors = []

    # Patrones que son peligrosos solo si NO están en un comentario
    import_patterns = [
        "from app.crud",
        "from app.models",
        "from app.db.session",
        "from sqlalchemy import",
        "import sqlalchemy",
    ]

    for py_file in BASE_PATH.rglob("*.py"):
        # Ignorar __pycache__
        if "__pycache__" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Ignorar líneas comentadas
                if line.strip().startswith("#"):
                    continue

                for pattern in import_patterns:
                    if pattern in line:
                        rel_path = py_file.relative_to(BASE_PATH.parent)
                        errors.append(f"{rel_path}:{i}: {pattern}")

        except Exception as e:
            print(f"[WARNING] No se pudo leer {py_file}: {e}")

    if errors:
        print(f"[ERROR] Se encontraron {len(errors)} imports peligrosos:")
        for error in errors:
            print(f"  {error}")
        return False

    print("[OK] No hay imports de SQLAlchemy, SQL Server o módulos eliminados")
    return True


def validate_app_import():
    """Intenta importar la app principal para verificar que no hay errores."""
    print("\n[*] Validando que app.main importa sin errores...")

    try:
        # Cambiar al directorio del proyecto
        os.chdir(PROJECT_ROOT)

        # Agregar al path
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

        # Importar
        from app.main import app

        print("[OK] app.main importada correctamente")

        # Verificar rutas
        if not app.routes:
            print("[WARNING] La app no tiene rutas registradas")
            return False

        print(f"[OK] App tiene {len(app.routes)} rutas registradas")
        return True

    except ImportError as e:
        print(f"[ERROR] No se puede importar app.main: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return False


def main():
    """Ejecuta todas las validaciones."""
    print("=" * 60)
    print("VALIDACIÓN DE ARQUITECTURA - POST MIGRACIÓN")
    print("=" * 60)

    all_passed = True

    all_passed &= validate_directories()
    all_passed &= validate_files()
    all_passed &= validate_imports()
    all_passed &= validate_app_import()

    print("\n" + "=" * 60)

    if all_passed:
        print("[SUCCESS] Todas las validaciones pasaron")
        print("[OK] Arquitectura limpia y lista para producción")
        print("=" * 60)
        return 0
    else:
        print("[FAILURE] Algunas validaciones fallaron")
        print("[ERROR] Hay residuos de código viejo en el codebase")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
