# Documentación API MisBoletas - Guía Principal

Esta carpeta contiene la documentación completa de la API.

## 📚 Primeros Pasos

1. **[INICIO_RAPIDO.md](INICIO_RAPIDO.md)** - 5 pasos para probar
2. **[ARQUITECTURA.md](ARQUITECTURA.md)** - Stack y estructura
3. **Módulos específicos** - Según tu necesidad

## 📦 Módulos de la API

| Módulo             | Descripción                                 | Archivo                                |
| ------------------ | ------------------------------------------- | -------------------------------------- |
| **Usuarios**       | Registro, login, recuperación de contraseña | [USUARIOS.md](USUARIOS.md)             |
| **Productos**      | CRUD de productos                           | [PRODUCTOS.md](PRODUCTOS.md)           |
| **Categorías**     | Organizar productos                         | [CATEGORIAS.md](CATEGORIAS.md)         |
| **Documentos**     | Subir archivos y OCR                        | [DOCUMENTOS.md](DOCUMENTOS.md)         |
| **FAQs**           | Preguntas frecuentes                        | [FAQS.md](FAQS.md)                     |
| **Organizaciones** | Espacios compartidos                        | [ORGANIZACIONES.md](ORGANIZACIONES.md) |
| **Tickets**        | Sistema de soporte                          | [TICKETS.md](TICKETS.md)               |

## 🌐 Acceso

**Base URL:**

- Desarrollo: `http://localhost:8080/api/v1`
- Producción: `https://api.misboletas.tech/api/v1`

**Documentación Interactiva:**

- `/docs` - Swagger UI
- `/redoc` - ReDoc

## 🔐 Autenticación

Endpoints protegidos requieren:

```
Authorization: Bearer {access_token}
```

## ✅ Estado

- Completamente operativo
- Todos los endpoints implementados
- Listo para producción

---

**Última actualización:** 7 de Diciembre de 2025

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
