# 📋 Testing Guide - MisBoletas API

## Configuración Previa

```bash
cd Back-MisBoletas
venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --log-level info
```

**URL**: http://localhost:8080/docs (Swagger UI)

---

## 1. Registrarse

**Endpoint**: `POST /api/v1/users/register`

```json
{
  "email": "test@example.com",
  "password": "Pass123!",
  "nombre_usuario": "testuser"
}
```

**Response** (201):

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user_id": "uuid-123",
  "email": "test@example.com"
}
```

**Guardar**: `access_token` para las próximas requests

---

## 2. Autorizar en Swagger

1. Click en botón "🔒 Authorize"
2. Pegar: `Bearer {access_token}`
3. Click "Authorize" → "Close"

Ahora todos los endpoints protegidos funcionarán con tu token.

---

## 3. Crear Producto

**Endpoint**: `POST /api/v1/productos`

```json
{
  "nombre": "iPhone 15",
  "marca": "Apple",
  "precio": 999.99,
  "fecha_compra": "2024-11-20",
  "duracion_garantia": "12 meses",
  "tienda": "Apple Store"
}
```

**Guardar**: El `id` del producto para Upload

---

## 4. Subir Documento (con OCR)

**Endpoint**: `POST /api/v1/documentos/upload/{producto_id}`

- Seleccionar archivo (PDF, JPG, PNG)
- System procesa OCR automáticamente

**Response** (201):

```json
{
  "id": "doc-uuid",
  "url_gcs": "gs://bucket/path",
  "metadata_ocr": {
    "texto_completo": "...",
    "datos_estructurados": {...},
    "confianza": 0.95
  }
}
```

---

## 5. Ver Resultado OCR

**Endpoint**: `GET /api/v1/documentos/{documento_id}`

```json
{
  "id": "doc-uuid",
  "nombre_archivo": "boleta.pdf",
  "metadata_ocr": {
    "texto_completo": "Detalles de la boleta",
    "datos_estructurados": {
      "total": "$999.99",
      "fecha": "2024-11-20"
    }
  }
}
```

---

## 6. Descargar Documento

**Endpoint**: `GET /api/v1/documentos/{documento_id}/signed-url`

**Response**:

```json
{
  "signed_url": "https://storage.googleapis.com/..."
}
```

Copiar URL en navegador → Descarga automática

---

## Códigos de Respuesta

| Código | Significado                |
| ------ | -------------------------- |
| 200    | ✅ Éxito GET               |
| 201    | ✅ Creado (POST)           |
| 400    | ❌ Datos inválidos         |
| 401    | ❌ Token inválido/expirado |
| 404    | ❌ Recurso no encontrado   |
| 500    | ❌ Error servidor          |

---

## Troubleshooting

| Problema           | Solución                                  |
| ------------------ | ----------------------------------------- |
| 401 Unauthorized   | Re-hacer login, copiar token, autorizar   |
| 404 Not Found      | Verificar que el `id` sea correcto (UUID) |
| Token expirado     | Hacer nuevo login                         |
| Archivo muy grande | Máximo 50MB recomendado                   |
| OCR no procesa     | Asegurar formato: PDF, JPG, PNG válido    |

---

## Scripts Útiles

**Ver todos los productos**:

```bash
curl -H "Authorization: Bearer {token}" http://localhost:8080/api/v1/productos
```

**Eliminar producto**:

```bash
curl -X DELETE -H "Authorization: Bearer {token}" http://localhost:8080/api/v1/productos/{id}
```

---

**Documentación completa**: Ver `ARCHITECTURE_SHORT.md`
