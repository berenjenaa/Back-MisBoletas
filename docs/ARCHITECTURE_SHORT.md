# 🏗️ Arquitectura - MisBoletas Backend

## Stack Tecnológico

```
FastAPI 0.116.1
├─ Supabase 2.10.0 (DB + Auth)
├─ Google Cloud Storage (Archivos)
├─ Google Document AI (OCR)
└─ Uvicorn (ASGI Server)
```

## Estructura del Proyecto

```
Back-MisBoletas/
├── app/
│   ├── api/v1/          → Endpoints (users, productos, etc)
│   ├── core/            → Config + Auth
│   ├── services/        → GCS + OCR
│   ├── models/          → Pydantic schemas
│   └── db/              → Session
├── requirements.txt
└── Dockerfile
```

## Base de Datos (Supabase PostgreSQL)

| Tabla      | Campos                                                 |
| ---------- | ------------------------------------------------------ |
| profiles   | id, email, nombre_usuario, avatar_url                  |
| productos  | id, user_id, nombre, marca, precio, fecha_compra       |
| categorias | id, user_id, nombre_categoria, color                   |
| documentos | id, producto_id, nombre_archivo, url_gcs, metadata_ocr |

**Seguridad**:

- RLS: `auth.uid() = user_id`
- Cascade delete en relaciones
- IDs: UUID v4
- Naming: snake_case

## Google Cloud Storage

```
Bucket: misboletas-bucket
Estructura: /user_{uuid}/product_{uuid}/documento.pdf
Seguridad: Signed URLs (24h de validez)
OCR: Procesado por Document AI
```

## Autenticación

```
Supabase Auth (JWT tokens)
├─ POST /users/register  (público)
├─ POST /users/login     (público)
└─ HTTPBearer validator para endpoints protegidos

Headers:
Authorization: Bearer {access_token}
```

## Flujo Principal

```
1. Usuario → POST /register → Supabase Auth + profile creado
2. Usuario → POST /login → JWT token retornado
3. Usuario → POST /productos → Crea producto en Supabase
4. Usuario → POST /documentos/upload/{producto_id}
   → Upload GCS + Proceso OCR + Almacena en Supabase
```

## Endpoints por Categoría

### Usuarios (User)

```
GET  /api/v1/users/me         - Obtener perfil
PUT  /api/v1/users/me         - Actualizar perfil
DEL  /api/v1/users/me         - Eliminar cuenta
POST /api/v1/users/register   - Registrarse
POST /api/v1/users/login      - Login
```

### Productos

```
GET  /api/v1/productos        - Listar
POST /api/v1/productos        - Crear
GET  /api/v1/productos/{id}   - Obtener
PUT  /api/v1/productos/{id}   - Actualizar
DEL  /api/v1/productos/{id}   - Eliminar
```

### Categorías

```
GET  /api/v1/categorias       - Listar
POST /api/v1/categorias       - Crear
GET  /api/v1/categorias/{id}  - Obtener
PUT  /api/v1/categorias/{id}  - Actualizar
DEL  /api/v1/categorias/{id}  - Eliminar
```

### Documentos

```
POST /api/v1/documentos/upload/{producto_id}     - Subir + OCR
GET  /api/v1/documentos/by-product/{producto_id} - Listar por producto
GET  /api/v1/documentos/{id}                     - Obtener
GET  /api/v1/documentos/{id}/signed-url          - Descargar (URL firmada)
DEL  /api/v1/documentos/{id}                     - Eliminar
```

## Seguridad

✅ JWT tokens (Supabase Auth)  
✅ HTTPBearer authentication  
✅ Row-Level Security (RLS) en BD  
✅ Signed URLs para archivos (24h)  
✅ Ownership verification en mutations  
✅ Errores sin exponer detalles

## Costos Aproximados (Mensual)

| Servicio    | Costo        |
| ----------- | ------------ |
| Cloud Run   | $10-50       |
| Supabase    | $25          |
| GCS         | $5-20        |
| Document AI | $0-10        |
| **TOTAL**   | **~$50/mes** |

## Estatus

✅ **Production Ready**

Todo funcional, testeado y listo para producción.
