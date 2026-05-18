# Arquitectura - Backend MisBoletas

## 📚 Stack

| Componente | Versión              |
| ---------- | -------------------- |
| FastAPI    | 0.116.1              |
| Supabase   | 2.10.0               |
| GCS        | Google Cloud Storage |
| OCR        | Google Document AI   |

## 🏗️ Estructura

```
Back-MisBoletas/
├── app/
│   ├── api/v1/          # Endpoints
│   ├── core/            # Config & Auth
│   ├── services/        # GCS, OCR
│   ├── schemas/         # Modelos Pydantic
│   └── db/              # Supabase
```

## 🔐 Autenticación

- **Proveedor:** Supabase Auth (JWT)
- **Público:** POST /users/register, POST /users/login
- **Protegido:** Requiere `Authorization: Bearer {token}`
- **Vigencia:** 1 hora

## 🌐 Almacenamiento

- **Bucket:** misboletas-bucket (GCS)
- **Estructura:** `/user-{uuid}/product-{uuid}/file.pdf`
- **URLs:** Firmadas (válidas 24h)
- **OCR:** Procesado automáticamente al subir

## 📄 Flujo de Documento

1. Upload → GCS + metadata en DB
2. OCR inicia en background
3. Datos extraídos → metadata_ocr
4. Cliente obtiene vía GET /documentos/{id}

## 🔒 Seguridad

✅ JWT autenticación  
✅ Row-Level Security  
✅ URLs firmadas (24h)  
✅ Validación de propiedad  
✅ HTTPS / TLS  
✅ Datos encriptados en tránsito

---

**Env:** Desarrollo, Render (Producción)
