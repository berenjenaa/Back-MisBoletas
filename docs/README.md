# Documentacion del Backend MisBoletas

Esta carpeta contiene la documentacion completa de la API.

## Por donde empezar

1. Lee INDICE.md - Indice general
2. Lee INICIO_RAPIDO.md - 5 pasos para probar
3. Consulta los modulos individuales segun necesites

## Archivos Disponibles

INDICE.md

- Indice general y navegacion

INICIO_RAPIDO.md

- 5 pasos basicos para probar la API
- Endpoints principales
- Guia rapida

USUARIOS.md

- Autenticacion (registro, login)
- Gestion de perfiles
- Cambio de contraseña
- Endpoints: /users/register, /users/login, /users/me

PRODUCTOS.md

- Crear, listar y gestionar productos
- Actualizar y eliminar
- Endpoints: /productos

DOCUMENTOS.md

- Subir archivos (boletas, garantias)
- OCR automatico
- Descargar con URL firmada
- Endpoints: /documentos/upload, /documentos

CATEGORIAS.md

- Crear categorias para organizar productos
- Gestionar categorias
- Endpoints: /categorias

ARQUITECTURA.md

- Stack tecnologico
- Estructura del proyecto
- Flujo general de datos
- Seguridad

## Estructura

Cada documento incluye:

- Descripcion del modulo
- Endpoints disponibles
- Solicitud y respuesta de ejemplo
- Validaciones y errores
- Modelo de datos
