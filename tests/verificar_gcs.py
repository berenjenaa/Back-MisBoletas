"""
Script para verificar archivos en Google Cloud Storage.
Muestra todos los archivos subidos al bucket.
"""

from app.services.gcs_service import get_gcs_service
from app.core.config import settings
from datetime import datetime


def verificar_gcs():
    """
    Lista todos los archivos en el bucket de GCS.
    """
    print("=" * 60)
    print("VERIFICACIÓN DE GOOGLE CLOUD STORAGE")
    print("=" * 60)

    print(f"\n📦 Bucket: {settings.GCS_BUCKET_NAME}")
    print(f"🔧 GCS Enabled: {settings.gcs_enabled}")

    if not settings.gcs_enabled:
        print("\n❌ GCS no está habilitado en la configuración")
        return

    try:
        print("\n🔄 Conectando a GCS...")
        gcs_service = get_gcs_service()

        if not gcs_service:
            print("❌ No se pudo inicializar el servicio GCS")
            return

        print("✅ Conexión establecida\n")

        # Obtener el bucket
        bucket = gcs_service.client.bucket(settings.GCS_BUCKET_NAME)

        # Verificar que existe
        if not bucket.exists():
            print(f"❌ El bucket '{settings.GCS_BUCKET_NAME}' no existe")
            return

        print(f"✅ Bucket '{settings.GCS_BUCKET_NAME}' encontrado\n")

        # Listar todos los archivos
        print("📁 ARCHIVOS EN EL BUCKET:")
        print("-" * 60)

        blobs = list(bucket.list_blobs())

        if not blobs:
            print("❌ No hay archivos en el bucket")
            return

        print(f"✅ Se encontraron {len(blobs)} archivo(s)\n")

        for i, blob in enumerate(blobs, 1):
            print(f"\n{i}. 📄 {blob.name}")
            print(f"   📊 Tamaño: {format_size(blob.size)}")
            print(f"   🕐 Fecha: {blob.time_created.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   📝 Content-Type: {blob.content_type}")
            print(
                f"   🔗 URL: https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{blob.name}"
            )

            # Verificar si es accesible públicamente
            try:
                blob.reload()
                print(f"   ✅ Archivo accesible")
            except Exception as e:
                print(f"   ⚠️  Error al acceder: {e}")

        print("\n" + "=" * 60)
        print(f"✅ Verificación completada - {len(blobs)} archivo(s) encontrado(s)")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"Tipo de error: {type(e).__name__}")
        import traceback

        print(f"\nTraceback:\n{traceback.format_exc()}")


def format_size(size_bytes):
    """Formatear tamaño de archivo en KB, MB, etc."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


if __name__ == "__main__":
    verificar_gcs()
