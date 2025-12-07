# Categorías - Organizador de Productos

## Endpoints

| Método | URL                | Descripción       |
| ------ | ------------------ | ----------------- |
| GET    | `/categorias`      | Listar categorías |
| GET    | `/categorias/{id}` | Obtener una       |
| POST   | `/categorias`      | Crear             |
| PUT    | `/categorias/{id}` | Actualizar        |
| DELETE | `/categorias/{id}` | Eliminar          |

## Ejemplos

### Listar

```bash
GET /api/v1/categorias
Authorization: Bearer TOKEN
```

### Crear

```bash
POST /api/v1/categorias
{
  "nombre": "Electrónica",
  "color": "#FF6B6B"
}
```

### Ver productos de categoría

```bash
GET /api/v1/productos?categoria=cat_123
```

### Actualizar

```bash
PUT /api/v1/categorias/cat_123
{
  "nombre": "Electrónica Actualizada",
  "color": "#4ECDC4"
}
```

### Eliminar

```bash
DELETE /api/v1/categorias/cat_123
```

---

**Ver Swagger en `/docs`**
