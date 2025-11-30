# Modulo Documentos

Subir y gestionar documentos (boletas, garantias). El OCR procesa automaticamente.

## Informacion General

El OCR (Optical Character Recognition) se procesa automaticamente cuando subes un documento.
No necesitas un endpoint separado - el OCR es parte integral del flujo de subida de documentos.

## Subir Documento

POST /documentos/upload/{id_producto}

Subir un documento a un producto. OCR se procesa automaticamente.

Headers:

Authorization: Bearer {access_token}
Content-Type: multipart/form-data

Solicitud:

file: [documento.pdf o imagen.jpg]

Formatos soportados: PDF, JPG, PNG, JPEG
Tamaño maximo: 10MB

Respuesta (201):

``json
{
  "message": "Documento subido exitosamente",
  "documento": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "producto_id": "550e8400-e29b-41d4-a716-446655440000",
    "nombre_archivo": "boleta_iphone.pdf",
    "url_gcs": "https://storage.googleapis.com/...",
    "blob_name": "user_123e/product_550e/boleta_iphone.pdf",
    "content_type": "application/pdf",
    "size_bytes": 245000,
    "metadata_ocr": {
      "texto_completo": "BOLETA DE VENTA\nRUT Vendedor: 76.123.456-7...",
      "datos_estructurados": {
        "monto_total": "1299.99",
        "fecha": "2025-10-15",
        "vendedor": "Apple Store",
        "rut_vendedor": "76.123.456-7"
      },
      "confianza": 0.95,
      "total_entities": 12
    },
    "fecha_subida": "2025-11-30T14:30:00"
  },
  "ocr_processed": true
}
``

El OCR se ejecuta automaticamente. El campo ocr_processed indica si se proceso correctamente.

Errores:
- 404: Producto no encontrado
- 400: Archivo muy grande o formato invalido

## Listar Documentos

GET /documentos/by-product/{id_producto}

Obtener todos los documentos de un producto.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

``json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "producto_id": "550e8400-e29b-41d4-a716-446655440000",
    "nombre_archivo": "boleta_iphone.pdf",
    "url_gcs": "https://storage.googleapis.com/...",
    "content_type": "application/pdf",
    "size_bytes": 245000,
    "metadata_ocr": {
      "datos_estructurados": {
        "monto_total": "1299.99",
        "fecha": "2025-10-15"
      }
    },
    "fecha_subida": "2025-11-30T14:30:00"
  }
]
``

## Obtener Documento

GET /documentos/{id_documento}

Obtener un documento especifico con todos los datos OCR.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

``json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "producto_id": "550e8400-e29b-41d4-a716-446655440000",
  "nombre_archivo": "boleta_iphone.pdf",
  "url_gcs": "https://storage.googleapis.com/...",
  "blob_name": "user_123e/product_550e/boleta_iphone.pdf",
  "content_type": "application/pdf",
  "size_bytes": 245000,
  "metadata_ocr": {
    "texto_completo": "BOLETA DE VENTA\nFecha: 2025-10-15...",
    "datos_estructurados": {
      "monto_total": "1299.99",
      "monto_descuento": "0",
      "fecha": "2025-10-15",
      "vendedor": "Apple Store",
      "rut_vendedor": "76.123.456-7",
      "ciudad": "Santiago",
      "items_vendidos": 1,
      "folio": "123456"
    },
    "confianza": 0.95,
    "total_entities": 12
  },
  "fecha_subida": "2025-11-30T14:30:00"
}
``

Errores:
- 404: Documento no encontrado

## Descargar Documento

GET /documentos/{id_documento}/signed-url

Obtener URL firmada para descargar sin autenticacion.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

``json
{
  "documento_id": "660e8400-e29b-41d4-a716-446655440000",
  "signed_url": "https://storage.googleapis.com/...?X-Goog-Algorithm=...",
  "expires_in_seconds": 86400
}
``

La URL es valida por 24 horas y puede abrirse en navegador.

## Eliminar Documento

DELETE /documentos/{id_documento}

Eliminar un documento.

Headers:

Authorization: Bearer {access_token}

Respuesta (200):

``json
{
  "message": "Documento eliminado correctamente",
  "documento_id": "660e8400-e29b-41d4-a716-446655440000"
}
``

## Datos OCR Extraidos

El objeto metadata_ocr contiene:

``json
{
  "texto_completo": "Texto completo extraido",
  "datos_estructurados": {
    "monto_total": "Cantidad total",
    "monto_descuento": "Descuento si hay",
    "fecha": "Fecha de compra (YYYY-MM-DD)",
    "vendedor": "Nombre del negocio",
    "rut_vendedor": "RUT del vendedor",
    "ciudad": "Lugar de compra",
    "items_vendidos": "Cantidad de productos",
    "folio": "Numero de folio"
  },
  "confianza": 0.95,
  "total_entities": 12
}
``

Escala de confianza:
- 0.9+ = Muy confiado
- 0.7-0.9 = Buena confianza
- <0.7 = Baja confianza, verificar manualmente

## Notas

- OCR es automatico al subir documentos
- Solo el dueno del producto puede ver sus documentos
- Los documentos se guardan encriptados en Google Cloud Storage
- El OCR mejora con imagenes de mejor calidad y tamaño
