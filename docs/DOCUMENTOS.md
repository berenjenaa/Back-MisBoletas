# Documentos - Subida y OCR

## Endpoints

| Método | URL                                | Descripción       |
| ------ | ---------------------------------- | ----------------- |
| POST   | `/documentos/upload/{producto_id}` | Subir archivo     |
| GET    | `/documentos`                      | Listar documentos |
| GET    | `/documentos/{id}`                 | Obtener uno       |
| GET    | `/documentos/{id}/signed-url`      | Descargar         |
| DELETE | `/documentos/{id}`                 | Eliminar          |

## Ejemplo: Subir con OCR

```bash
POST /api/v1/documentos/upload/producto_123
Content-Type: multipart/form-data

file: boleta.pdf
```

Respuesta incluye:

- `documento_id`
- `ocr_status`: "pendiente" → "completado"
- `metadata_ocr`: Datos extraídos

## OCR Automático

Los documentos se procesan automáticamente:

1. Upload → Storage en GCS
2. OCR inicia en background
3. Datos se guardan en `metadata_ocr`
4. Accede vía `GET /documentos/{id}`

---

**Documentación completa:** [DOCUMENTOS_FULL.md](DOCUMENTOS_FULL.md)
