# Modulo Usuarios

Autenticacion y gestion de perfiles de usuario.

## Registrarse

POST /users/register

Crear una cuenta nueva.

Solicitud:

`json
{
  "correo": "usuario@example.com",
  "contrasena": "Pass123!",
  "nombre": "Juan Perez"
}
`

Respuesta (201):

`json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id_usuario": "123e4567-e89b-12d3-a456-426614174000",
    "email": "usuario@example.com",
    "nombre_completo": "Juan Perez",
    "fecha_registro": "2025-11-30T10:30:00"
  }
}
`

Validaciones:

- Email valido y unico
- Contraseña minimo 8 caracteres, mayuscula, numero y simbolo

Errores:

- 400: Email ya existe o contraseña debil

## Iniciar Sesion

POST /users/login

Autenticarse con email y contraseña.

Solicitud:

`json
{
  "correo": "usuario@example.com",
  "contrasena": "Pass123!"
}
`

Respuesta (200):

`json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id_usuario": "123e4567-e89b-12d3-a456-426614174000",
    "email": "usuario@example.com",
    "nombre_completo": "Juan Perez",
    "fecha_registro": "2025-11-30T10:30:00"
  }
}
`

Errores:

- 401: Credenciales invalidas

## Obtener Perfil

GET /users/me

Obtener perfil del usuario autenticado.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

`json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "usuario@example.com",
  "nombre_usuario": "juan_perez",
  "avatar_url": "https://...",
  "fecha_registro": "2025-11-30T10:30:00"
}
`

Errores:

- 401: Token invalido o expirado

## Actualizar Perfil

PUT /users/me

Actualizar informacion del perfil.

Headers:

Authorization: Bearer {access_token}

Solicitud:

`json
{
  "nombre_usuario": "juan_p",
  "avatar_url": "https://..."
}
`

Todos los campos son opcionales.

Respuesta (200):

`json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "usuario@example.com",
  "nombre_usuario": "juan_p",
  "avatar_url": "https://...",
  "fecha_registro": "2025-11-30T10:30:00"
}
`

## Eliminar Cuenta

DELETE /users/me

Eliminar la cuenta de usuario y todos los datos asociados.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

`json
{
  "message": "Usuario eliminado correctamente"
}
`

## Flujo de Autenticacion

1. Usuario llama POST /users/register o POST /users/login
2. Recibe access_token en respuesta
3. Guarda token en almacenamiento del cliente
4. Incluye token en header Authorization para todos los requests autenticados
5. Si recibe 401, token expiro - debe hacer login nuevamente

Notas:

- Tokens validos por 1 hora
- Todos los datos encriptados en transito (HTTPS)
- Row-Level Security asegura que solo veas tus datos
