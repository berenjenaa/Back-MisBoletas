"""
Test simple para verificar que OCR asincrónico funciona.

Prueba:
1. Upload de documento
2. Verificar que responde < 100ms
3. Verificar que estado_ocr es 'pendiente'
4. Esperar 2 segundos
5. Verificar que estado_ocr cambió a 'completado' o 'error'
"""

import asyncio
import time
from uuid import UUID
import httpx
import json

# Configuración de test
API_BASE_URL = "http://localhost:8000"
USER_TOKEN = "YOUR_JWT_TOKEN_HERE"  # Obtener de login
PRODUCTO_ID = "YOUR_PRODUCTO_ID_HERE"  # UUID de un producto existente

# Headers para autenticación
headers = {
    "Authorization": f"Bearer {USER_TOKEN}",
    "Content-Type": "application/json",
}


async def test_ocr_async():
    """Test de OCR asincrónico."""

    async with httpx.AsyncClient() as client:
        # 1. Crear documento de prueba
        print("[1] Subiendo documento...")
        with open("test_boleta.jpg", "rb") as f:
            files = {"file": ("test_boleta.jpg", f, "image/jpeg")}

            start_time = time.time()

            response = await client.post(
                f"{API_BASE_URL}/documentos/upload/{PRODUCTO_ID}",
                headers={"Authorization": f"Bearer {USER_TOKEN}"},
                files=files,
            )

            elapsed = time.time() - start_time

        print(f"   Status: {response.status_code}")
        print(f"   Tiempo respuesta: {elapsed:.2f}ms ✅ (debe ser < 100ms)")

        if response.status_code != 201:
            print(f"   Error: {response.text}")
            return

        data = response.json()
        documento = data["documento"]
        documento_id = documento["id"]

        print(f"   Documento ID: {documento_id}")
        print(f"   Estado inicial: {documento.get('estado_ocr', 'N/A')}")

        if elapsed > 100:
            print("   ❌ FALLO: La respuesta tardó más de 100ms")
            return

        print("   ✅ ÉXITO: Respuesta inmediata (< 100ms)")

        # 2. Verificar que estado_ocr es 'pendiente'
        print("\n[2] Verificando estado OCR...")
        response = await client.get(
            f"{API_BASE_URL}/documentos/{documento_id}",
            headers=headers,
        )
        data = response.json()
        estado = data.get("estado_ocr", "N/A")
        print(f"   Estado: {estado}")

        if estado == "pendiente":
            print("   ✅ Correcto: Estado es 'pendiente'")
        else:
            print(f"   ⚠️ Estado inesperado: {estado}")

        # 3. Esperar a que OCR complete (máximo 2 minutos)
        print("\n[3] Esperando a que OCR complete...")
        max_wait = 120  # 2 minutos
        check_interval = 5  # Chequear cada 5 segundos

        for i in range(0, max_wait, check_interval):
            await asyncio.sleep(check_interval)

            response = await client.get(
                f"{API_BASE_URL}/documentos/{documento_id}",
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                estado = data.get("estado_ocr", "N/A")
                print(f"   [{i+check_interval}s] Estado: {estado}")

                if estado == "completado":
                    print("   ✅ OCR completado exitosamente")
                    metadata = data.get("metadata_ocr")
                    if metadata:
                        entities = metadata.get("total_entities", 0)
                        confidence = metadata.get("confianza", 0)
                        print(f"      - Entidades extraídas: {entities}")
                        print(f"      - Confianza promedio: {confidence:.1%}")
                    return

                elif estado == "error":
                    error = data.get("error_ocr", "Unknown error")
                    print(f"   ❌ OCR falló: {error}")
                    return

        print("   ❌ Timeout: OCR tardó más de 2 minutos")


def main():
    """Ejecutar test."""

    print("=" * 60)
    print("TEST: OCR Asincrónico")
    print("=" * 60)

    # Validar token
    if USER_TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("\n❌ ERROR: Configura USER_TOKEN primero")
        print("   1. Login en la app")
        print("   2. Obtener JWT del response")
        print("   3. Pegar en USER_TOKEN arriba")
        return

    if PRODUCTO_ID == "YOUR_PRODUCTO_ID_HERE":
        print("\n❌ ERROR: Configura PRODUCTO_ID primero")
        print("   1. Listar productos del usuario")
        print("   2. Copiar UUID de un producto")
        print("   3. Pegar en PRODUCTO_ID arriba")
        return

    # Ejecutar test
    try:
        asyncio.run(test_ocr_async())
    except Exception as e:
        print(f"\n❌ Error durante test: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Test completado")
    print("=" * 60)


if __name__ == "__main__":
    main()
