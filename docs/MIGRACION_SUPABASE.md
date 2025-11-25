# Migración a Supabase - Resumen de Cambios

## 📋 Cambios Principales

### 1. Base de Datos
- **Antes:** SQL Server + SQLAlchemy ORM
- **Ahora:** Supabase PostgreSQL + Client SDK
- Eliminadas: 16 archivos de ORM (modelos, CRUD, session managers)
- Actualizado: Todas las operaciones usan `supabase.table().select/insert/update/delete()`

### 2. Autenticación
- **Supabase Auth** reemplaza login manual
- JWT tokens validados contra Supabase
- Row Level Security (RLS) protege datos por usuario
- `get_current_user()` delega en `supabase.auth.get_user(token)`

### 3. Estructura de Carpetas
```
app/
├── api/v1/           ← Endpoints limpios (sin imports de ORM)
├── core/             ← Config, middleware, dependencias
├── db/               ← Solo supabase.py (singleton client)
├── schemas/          ← Pydantic models (sin ORM config)
└── services/         ← GCS + OCR (sin product_service.py)
```

### 4. Operaciones de Base de Datos

**Antes (SQLAlchemy):**
```python
from app.models import Producto
session.query(Producto).filter(Producto.user_id == user_id).all()
```

**Ahora (Supabase):**
```python
supabase.table("productos").select("*").eq("user_id", str(user_id)).execute()
```

---

## 🚀 Cómo Usar

### Autenticación
```bash
# 1. Register
POST /api/v1/users/register
{
  "nombre": "Juan",
  "correo": "juan@example.com",
  "contrasena": "SecurePass123!"
}

# 2. Login
POST /api/v1/users/login
{
  "correo": "juan@example.com",
  "contrasena": "SecurePass123!"
}
# Devuelve: {"access_token": "eyJ...", "token_type": "bearer"}

# 3. Usar token en requests
GET /api/v1/productos
Headers: Authorization: Bearer eyJ...
```

### Productos
```bash
# Crear
POST /api/v1/productos
{
  "nombre": "Laptop",
  "precio": 1299.99,
  "descripcion": "Dell XPS 13"
}

# Listar (solo del usuario autenticado - por RLS)
GET /api/v1/productos

# Actualizar
PUT /api/v1/productos/{id}
{
  "nombre": "Laptop Dell",
  "precio": 1199.99
}

# Eliminar
DELETE /api/v1/productos/{id}
```

### Categorías
```bash
# Similar a productos
POST /api/v1/categorias
GET /api/v1/categorias
PUT /api/v1/categorias/{id}
DELETE /api/v1/categorias/{id}
```

### Documentos (OCR)
```bash
# Subir boleta
POST /api/v1/documentos/upload/{product_id}
Content-Type: multipart/form-data
file: [archivo PDF/imagen]

# Flujo:
# 1. Valida JWT
# 2. Verifica ownership del producto
# 3. Sube a Google Cloud Storage
# 4. Procesa con Document AI
# 5. Guarda metadatos en Supabase
# Devuelve: {"id": "...", "url": "gs://...", "datos_ocr": {...}}
```

---

## 🔐 Row Level Security (RLS)

Supabase **bloquea automáticamente** acceso cruzado entre usuarios:

```sql
-- En Supabase: cada tabla tiene RLS habilitado
CREATE POLICY "users_can_access_own_data" 
  ON productos FOR SELECT 
  USING (auth.uid() = user_id);
```

**Ejemplo práctico:**
- Usuario A (uuid=111) intenta acceder a producto de Usuario B (uuid=222)
- FastAPI valida JWT de Usuario A
- Supabase RLS rechaza silenciosamente
- Resultado: `[]` (lista vacía)

---

## ⚙️ Configuración

### .env (desarrollo)
```bash
SUPABASE_URL=https://[project].supabase.co
SUPABASE_KEY=eyJ...
ENVIRONMENT=development
GCS_BUCKET=misbolletas-dev
```

### .env (Cloud Run)
```bash
SUPABASE_URL=https://[project].supabase.co
SUPABASE_KEY=eyJ...
ENVIRONMENT=production
GCS_BUCKET=misbolletas-prod
GOOGLE_APPLICATION_CREDENTIALS=/app/gcs-key.json
```

---

## 📊 Stack Tecnológico

| Componente | Antes | Ahora |
|-----------|-------|-------|
| Base de datos | SQL Server | Supabase PostgreSQL |
| ORM | SQLAlchemy | Client SDK |
| Autenticación | Custom JWT | Supabase Auth |
| Storage | Local/? | Google Cloud Storage |
| OCR | ? | Google Document AI |
| Deployment | ? | Google Cloud Run |

---

## ✅ Validaciones Completadas

- ✓ App inicia sin errores (29 endpoints registrados)
- ✓ 0 imports de SQLAlchemy en el código
- ✓ Config portable (no paths hardcodeados)
- ✓ Dockerfile listo para Cloud Run (puerto 8080)
- ✓ Dependencias limpias (sin librerías obsoletas)
- ✓ RLS policies creadas en Supabase

---

## 📦 Instalación & Deploy

### Local
```bash
# 1. Crear proyecto Supabase (supabase.com)
# 2. Ejecutar schema SQL en Supabase
# 3. Configurar .env
# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Iniciar app
python run.py
# Acceder: http://localhost:8000/docs
```

### Cloud Run
```bash
# 1. Deploy con Google Cloud
gcloud run deploy misbolletas \
  --source . \
  --region us-central1 \
  --set-env-vars SUPABASE_URL="https://..." \
  --set-env-vars SUPABASE_KEY="eyJ..."

# 2. Ver logs
gcloud run logs read misbolletas --tail
```

---

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| "Invalid JWT" | Haz login nuevamente, usa token fresco |
| "Row-level security violation" | Verifica que user_id = auth.uid() en RLS |
| "Table does not exist" | Ejecuta schema SQL en Supabase |
| "Connection refused" | Verifica SUPABASE_URL en .env |

---

## 📚 Documentación Adicional

- **ARQUITECTURA_SHORT.md** - Estructura general
- **INTEGRACION_SUPABASE.md** - Detalles técnicos (si existe)
- **CONFIGURACION_SUPABASE.md** - Setup paso a paso (si existe)
- **QUICK_START.md** - Guía rápida

---

**Rama:** `configuracion-supabase`  
**Estado:** ✅ Listo para deployment
