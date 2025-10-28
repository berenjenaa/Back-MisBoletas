import os

print("--- 1. INICIANDO RUN.PY ---")

try:
    print("--- 2. IMPORTANDO UVICORN Y CONFIG... ---")
    import uvicorn
    from app.core.config import settings

    print("--- 3. IMPORTACIÓN EXITOSA ---")

    if __name__ == "__main__":
        print("--- 4. DENTRO DEL IF __NAME__ ---")

        port = int(os.getenv("PORT", settings.PORT))

        print(
            f"--- 5. CONFIGURACIÓN LISTA (ENV={settings.ENV}, DEBUG={settings.DEBUG}) ---"
        )
        print(f"--- 6. BASE DE DATOS A USAR: {settings.SQLALCHEMY_DATABASE_URL} ---")

        print(f"--- 7. LANZANDO UVICORN EN PUERTO {port}... ---")

        uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=settings.DEBUG)
    else:
        print("--- X. SCRIPT IMPORTADO, NO EJECUTADO DIRECTAMENTE ---")

except Exception as e:
    print(f"ERROR DURANTE LA CARGA: {e}")
