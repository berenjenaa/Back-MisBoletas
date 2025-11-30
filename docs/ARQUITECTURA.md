# Arquitectura - Backend MisBoletas

## Stack Tecnologico

FastAPI 0.116.1
Supabase 2.10.0 (Base de datos + Autenticacion)
Google Cloud Storage (Almacenamiento de archivos)
Google Document AI (OCR)
Uvicorn (Servidor ASGI)

## Estructura del Proyecto

Back-MisBoletas/
app/
api/v1/ - Endpoints (usuarios, productos, documentos, categorias)
core/ - Configuracion y autenticacion
services/ - Servicios GCS y OCR
schemas/ - Modelos de datos Pydantic
db/ - Conexion a base de datos

## Google Cloud Storage

Bucket: misboletas-bucket
Estructura: /user*{uuid}/product*{uuid}/archivo.pdf
URLs firmadas: Validas por 24 horas
OCR: Procesado por Google Document AI

## Autenticacion

Supabase Auth con JWT tokens

POST /users/register - Crear cuenta (publico)
POST /users/login - Iniciar sesion (publico)
Otros endpoints - Requieren Bearer token

Header: Authorization: Bearer {access_token}
Vigencia: 1 hora

## Flujo de Datos

1. Usuario registra cuenta -> Supabase Auth + Perfil creado
2. Usuario inicia sesion -> Obtiene JWT token
3. Usuario crea producto -> Se guarda en base de datos
4. Usuario sube documento -> Se sube a GCS y OCR procesa automaticamente
5. Usuario obtiene resultado -> Datos extraidos en metadata_ocr

## OCR - Procesamiento Automatico

El OCR se ejecuta automaticamente al subir documentos.
No hay endpoint separado de OCR.
Los datos extraidos se guardan en el campo metadata_ocr del documento.

## Seguridad

- Autenticacion JWT via Supabase
- Bearer token authentication
- Row-Level Security en base de datos
- URLs firmadas para descargas (24 horas)
- Validacion de propiedad en cambios
- HTTPS en todas las comunicaciones
- Datos encriptados en transito

## Estado

Backend completamente funcional.
Todos los endpoints operativos.
OCR y GCS integrados.
