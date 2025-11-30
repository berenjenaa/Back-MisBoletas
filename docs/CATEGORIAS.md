# Modulo Categorias

Organizar productos en categorias personalizadas.

## Listar Categorias

GET /categorias

Obtener todas las categorias del usuario autenticado.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

`json
[
  {
    "id_categoria": "770e8400-e29b-41d4-a716-446655440000",
    "id_usuario": "123e4567-e89b-12d3-a456-426614174000",
    "nombre": "Electronica",
    "color": "#FF6B6B"
  },
  {
    "id_categoria": "880e8400-e29b-41d4-a716-446655440000",
    "id_usuario": "123e4567-e89b-12d3-a456-426614174000",
    "nombre": "Muebles",
    "color": "#4ECDC4"
  }
]
`

## Obtener Categoria

GET /categorias/{id_categoria}

Obtener una categoria especifica.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

`json
{
  "id_categoria": "770e8400-e29b-41d4-a716-446655440000",
  "id_usuario": "123e4567-e89b-12d3-a456-426614174000",
  "nombre": "Electronica",
  "color": "#FF6B6B"
}
`

Errores:

- 404: Categoria no encontrada

## Crear Categoria

POST /categorias

Crear una nueva categoria.

Headers:

Authorization: Bearer {access_token}

Solicitud:

`json
{
  "nombre": "Electronica",
  "color": "#FF6B6B"
}
`

Respuesta (201):

`json
{
  "id_categoria": "770e8400-e29b-41d4-a716-446655440000",
  "id_usuario": "123e4567-e89b-12d3-a456-426614174000",
  "nombre": "Electronica",
  "color": "#FF6B6B"
}
`

Validaciones:

- nombre: 1-255 caracteres (requerido)
- color: Formato HEX valido (#RRGGBB)

Errores:

- 400: Nombre invalido o color invalido

## Actualizar Categoria

PUT /categorias/{id_categoria}

Actualizar informacion de la categoria.

Headers:

Authorization: Bearer {access_token}

Solicitud:

`json
{
  "nombre": "Electronica y Gadgets",
  "color": "#FF8800"
}
`

Todos los campos son opcionales.

Respuesta (200):

`json
{
  "id_categoria": "770e8400-e29b-41d4-a716-446655440000",
  "id_usuario": "123e4567-e89b-12d3-a456-426614174000",
  "nombre": "Electronica y Gadgets",
  "color": "#FF8800"
}
`

## Eliminar Categoria

DELETE /categorias/{id_categoria}

Eliminar una categoria.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

`json
{
  "message": "Categoria eliminada correctamente"
}
`

## Ejemplos de Colores

Algunos colores sugeridos para categorias:

- #FF6B6B (Rojo)
- #4ECDC4 (Turquesa)
- #45B7D1 (Azul)
- #96CEB4 (Verde)
- #FFEAA7 (Amarillo)
- #DDA15E (Marron)

## Categorias Sugeridas

- Electronica
- Muebles
- Ropa
- Electrodomesticos
- Equipamiento deportivo
- Herramientas
- Libros
- Otros

Notas:

- Solo el dueno puede modificar o eliminar
- El color debe ser en formato HEX valido
- Las categorias se usan para organizar productos en la UI
