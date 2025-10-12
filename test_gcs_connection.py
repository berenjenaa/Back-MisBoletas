"""
Script para verificar la conexión con Google Cloud Storage
Ejecutar: python test_gcs_connection.py
"""

from google.cloud import storage
from google.oauth2 import service_account

# Configuración
CREDENTIALS_FILE = "./misboletas-474520-fc9679606eb5.json"
BUCKET_NAME = "misboletas-storage"
PROJECT_ID = "misboletas-474520"

def test_gcs_connection():
    """Prueba la conexión con GCS"""
    try:
        print("🔄 Conectando a Google Cloud Storage...")
        
        # Crear credenciales
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE
        )
        
        # Crear cliente
        client = storage.Client(credentials=credentials, project=PROJECT_ID)
        print(f"✅ Cliente GCS creado correctamente")
        
        # Verificar bucket
        print(f"🔍 Verificando bucket: {BUCKET_NAME}")
        bucket = client.bucket(BUCKET_NAME)
        
        if bucket.exists():
            print(f"✅ Bucket '{BUCKET_NAME}' existe")
            
            # Listar algunos archivos
            print(f"\n📂 Primeros 10 archivos en el bucket:")
            blobs = list(bucket.list_blobs(max_results=10))
            
            if blobs:
                for i, blob in enumerate(blobs, 1):
                    print(f"  {i}. {blob.name} ({blob.size} bytes)")
            else:
                print("  ⚠️ El bucket está vacío")
                
            # Verificar permisos (intentar crear un archivo de prueba)
            print(f"\n🔐 Verificando permisos de escritura...")
            test_blob = bucket.blob("test_connection.txt")
            test_blob.upload_from_string("Test connection from Python")
            print(f"✅ Permisos de escritura: OK")
            
            # Eliminar archivo de prueba
            test_blob.delete()
            print(f"✅ Permisos de eliminación: OK")
            
            print("\n✅ ¡TODO CORRECTO! GCS está funcionando perfectamente")
            return True
            
        else:
            print(f"❌ El bucket '{BUCKET_NAME}' NO existe")
            print(f"   Crear el bucket en: https://console.cloud.google.com/storage/browser?project={PROJECT_ID}")
            return False
            
    except FileNotFoundError:
        print(f"❌ Archivo de credenciales no encontrado: {CREDENTIALS_FILE}")
        print(f"   Verifica que el archivo existe en la ruta correcta")
        return False
        
    except Exception as e:
        print(f"❌ Error al conectar con GCS: {str(e)}")
        print(f"   Tipo de error: {type(e).__name__}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  PRUEBA DE CONEXIÓN - GOOGLE CLOUD STORAGE")
    print("=" * 60)
    print()
    
    success = test_gcs_connection()
    
    print()
    print("=" * 60)
    if success:
        print("  ✅ RESULTADO: ÉXITO")
    else:
        print("  ❌ RESULTADO: ERROR")
    print("=" * 60)
