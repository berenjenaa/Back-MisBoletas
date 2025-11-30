# Modulo Productos

Gestionar productos (electrodomesticos, celulares, muebles, etc).

## Listar Productos

GET /productos

Obtener todos los productos del usuario autenticado.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

`json
[
  {
    "id_producto": "550e8400-e29b-41d4-a716-446655440000",
    "id_usuario": "123e4567-e89b-12d3-a456-426614174000",
    "nombre": "iPhone 15 Pro",
    "fecha_compra": "2025-10-15",
    "duracion_garantia_meses": 24,
    "marca": "Apple",
    "modelo": "iPhone 15 Pro Max",
    "tienda": "Apple Store",
    "notas": "Comprado en promocion",
    "precio": 1299.99,
    "fecha_creacion": "2025-11-20T14:30:00"
  }
]
`

## Obtener Producto

GET /productos/{id_producto}

Obtener un producto especifico.

Headers:

Authorization: Bearer {access_token}

Respuesta (200): Mismo formato que arriba.

Errores:

- 404: Producto no encontrado

## Crear Producto

POST /productos

Crear un nuevo producto.

Headers:

Authorization: Bearer {access_token}

Solicitud:

`json
{
  "nombre": "iPhone 15 Pro",
  "fecha_compra": "2025-10-15",
  "duracion_garantia_meses": 24,
  "marca": "Apple",
  "modelo": "iPhone 15 Pro Max",
  "tienda": "Apple Store",
  "notas": "Comprado en promocion",
  "precio": 1299.99
}
`

Solo nombre es requerido. Otros campos son opcionales.

Respuesta (201):

`json
{
  "id_producto": "550e8400-e29b-41d4-a716-446655440000",
  "id_usuario": "123e4567-e89b-12d3-a456-426614174000",
  "nombre": "iPhone 15 Pro",
  "fecha_compra": "2025-10-15",
  "duracion_garantia_meses": 24,
  "marca": "Apple",
  "modelo": "iPhone 15 Pro Max",
  "tienda": "Apple Store",
  "notas": "Comprado en promocion",
  "precio": 1299.99,
  "fecha_creacion": "2025-11-20T14:30:00"
}
`

Validaciones:

- nombre: 1-255 caracteres (requerido)
- duracion_garantia_meses: 0-120
- precio: mayor a 0
- fecha_compra: formato YYYY-MM-DD

Errores:

- 400: Nombre vacio o muy largo

## Actualizar Producto

PUT /productos/{id_producto}

Actualizar informacion del producto.

Headers:

Authorization: Bearer {access_token}

Solicitud:

`json
{
  "nombre": "iPhone 15 Pro",
  "precio": 1199.99,
  "notas": "Notas actualizadas"
}
`

Todos los campos son opcionales.

Respuesta (200): Producto actualizado.

## Eliminar Producto

DELETE /productos/{id_producto}

Eliminar un producto.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

`json
{
  "message": "Producto eliminado correctamente"
}
`

Notas:

- Solo el dueno puede modificar o eliminar sus productos
- Todos los timestamps en formato ISO 8601
