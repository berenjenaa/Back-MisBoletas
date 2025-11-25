# 🚀 Quick Start - MisBoletas API

## Iniciar Servidor

```bash
cd Back-MisBoletas
venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --log-level info
```

**Acceso**: http://localhost:8080/docs

---

## 5 Pasos para Probar

### 1. Registrarse

```
POST /api/v1/users/register
{
  "email": "test@example.com",
  "password": "Pass123!"
}
```

Copia el `access_token`

### 2. Autorizar

Click "Authorize" → Pega: `Bearer {token}`

### 3. Crear Producto

```
POST /api/v1/productos
{
  "nombre": "iPhone 15",
  "marca": "Apple",
  "precio": 999.999
}
```

Copia el `id`

### 4. Subir Documento

```
POST /api/v1/documentos/upload/{producto_id}
- File: boleta.jpg
```

Automáticamente procesa OCR ✅

### 5. Ver Resultado OCR

```
GET /api/v1/documentos/{documento_id}
```

Ves: `metadata_ocr` con datos extraídos

---

## Endpoints Principales

| Método | Endpoint                    | Descripción       |
| ------ | --------------------------- | ----------------- |
| POST   | /users/register             | Registrarse       |
| POST   | /users/login                | Login             |
| GET    | /users/me                   | Mi perfil         |
| POST   | /productos                  | Crear producto    |
| GET    | /productos                  | Listar productos  |
| POST   | /categorias                 | Crear categoría   |
| GET    | /categorias                 | Listar categorías |
| POST   | /documentos/upload/{pid}    | Subir + OCR       |
| GET    | /documentos/{id}/signed-url | URL descarga      |

---

**Más info**: Ver `TESTING_GUIDE.md` para flujo completo
