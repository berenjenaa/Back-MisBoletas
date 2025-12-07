# Usuarios - Autenticación

## Endpoints

| Método | URL                      | Descripción            |
| ------ | ------------------------ | ---------------------- |
| POST   | `/users/register`        | Crear cuenta           |
| POST   | `/users/login`           | Iniciar sesión         |
| GET    | `/users/me`              | Ver perfil             |
| PUT    | `/users/me`              | Actualizar perfil      |
| POST   | `/users/forgot-password` | Recuperar contraseña   |
| POST   | `/users/reset-password`  | Restablecer contraseña |

## Ejemplos

### Registro

```bash
POST /api/v1/users/register
{
  "correo": "usuario@example.com",
  "contrasena": "Pass123!"
}
```

### Login

```bash
POST /api/v1/users/login
{
  "correo": "usuario@example.com",
  "contrasena": "Pass123!"
}
```

Retorna: `access_token` (usar en `Authorization: Bearer TOKEN`)

### Ver perfil

```bash
GET /api/v1/users/me
Authorization: Bearer TOKEN
```

## Validaciones

- Email: válido y único
- Contraseña: mín 8 chars, mayúscula, número, símbolo

---

**Documentación completa:** `/docs` en Swagger
