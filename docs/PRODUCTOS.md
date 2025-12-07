# Productos - CRUD

## Endpoints

| Método | URL                         | Descripción           |
| ------ | --------------------------- | --------------------- |
| GET    | `/productos`                | Listar todos          |
| GET    | `/productos?categoria={id}` | Filtrar por categoría |
| GET    | `/productos/{id}`           | Obtener uno           |
| POST   | `/productos`                | Crear                 |
| PUT    | `/productos/{id}`           | Actualizar            |
| DELETE | `/productos/{id}`           | Eliminar              |

## Ejemplos

### Listar

```bash
GET /api/v1/productos
Authorization: Bearer TOKEN
```

### Crear

```bash
POST /api/v1/productos
{
  "nombre": "iPhone 15",
  "marca": "Apple",
  "modelo": "Pro Max",
  "precio": 1299.99,
  "fecha_compra": "2025-10-15",
  "duracion_garantia_meses": 24,
  "tienda": "Apple Store"
}
```

### Filtrar por categoría

```bash
GET /api/v1/productos?categoria=cat_123
```

### Actualizar

```bash
PUT /api/v1/productos/prod_123
{ "nombre": "iPhone 15 Updated", "precio": 999.99 }
```

### Eliminar

```bash
DELETE /api/v1/productos/prod_123
```

---

**Ver Swagger en `/docs`**

Notas:

- Solo el dueno puede modificar o eliminar sus productos
- Todos los timestamps en formato ISO 8601
