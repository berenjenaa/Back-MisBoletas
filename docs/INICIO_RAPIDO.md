# Inicio Rapido - API MisBoletas

## Iniciar el Servidor

`bash
cd Back-MisBoletas
venv\Scripts\Activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --log-level info
`

Acceso: http://localhost:8080/docs

## 5 Pasos Basicos

### 1. Registrarse

POST /api/v1/users/register

`json
{
  "correo": "usuario@example.com",
  "contrasena": "Pass123!",
  "nombre": "Mi Nombre"
}
`

Guarda el access_token de la respuesta.

### 2. Autorizar

En Swagger UI, click en Authorize e ingresa: Bearer {access_token}

### 3. Crear Producto

POST /api/v1/productos

`json
{
  "nombre": "iPhone 15",
  "marca": "Apple",
  "precio": 999.999
}
`

Guarda el id_producto.

### 4. Subir Documento

POST /api/v1/documentos/upload/{id_producto}

Sube un PDF o imagen. El OCR se procesa automaticamente.

### 5. Ver Resultados OCR

GET /api/v1/documentos/{id_documento}

Respuesta incluye metadata_ocr con datos extraidos.

## Endpoints Principales

| Metodo | Endpoint                        | Descripcion             |
| ------ | ------------------------------- | ----------------------- |
| POST   | /users/register                 | Crear cuenta            |
| POST   | /users/login                    | Iniciar sesion          |
| GET    | /users/me                       | Obtener perfil          |
| POST   | /productos                      | Crear producto          |
| GET    | /productos                      | Listar productos        |
| POST   | /categorias                     | Crear categoria         |
| GET    | /categorias                     | Listar categorias       |
| POST   | /documentos/upload/{product_id} | Subir documento con OCR |
| GET    | /documentos/{id}/signed-url     | Descargar documento     |

Ver documentacion completa en los archivos USUARIOS.md, PRODUCTOS.md, DOCUMENTOS.md, CATEGORIAS.md
