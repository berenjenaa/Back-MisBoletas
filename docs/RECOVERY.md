# Recuperación de Contraseña

## Endpoints

| Método | URL                      | Descripción                     |
| ------ | ------------------------ | ------------------------------- |
| POST   | `/users/forgot-password` | Solicitar email de recuperación |
| POST   | `/users/reset-password`  | Restablecer con token           |

## Ejemplos

### 1. Solicitar recuperación

```bash
POST /users/forgot-password
{
  "correo": "usuario@example.com",
  "password": "temp_value"
}
```

### 2. Restablecer

```bash
POST /users/reset-password
{
  "token": "token_del_email",
  "password": "nueva_contraseña"
}
```

Retorna: `access_token` para auto-login

---

**Documentación completa:** [RECOVERY_FULL.md](RECOVERY_FULL.md)
