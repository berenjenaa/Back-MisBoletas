# FAQs - Preguntas Frecuentes

## Endpoints

| Método | URL          | Auth  |
| ------ | ------------ | ----- |
| GET    | `/faqs`      | ❌ No |
| GET    | `/faqs/{id}` | ❌ No |
| POST   | `/faqs`      | ✅ Sí |
| PUT    | `/faqs/{id}` | ✅ Sí |
| DELETE | `/faqs/{id}` | ✅ Sí |

## Ejemplos

### Obtener todas

```bash
GET /api/v1/faqs
```

### Crear (admin)

```bash
POST /api/v1/faqs
Authorization: Bearer TOKEN
{
  "pregunta": "¿Cómo subo documentos?",
  "respuesta": "Usa el botón de cámara...",
  "categoria": "documentos",
  "orden": 1
}
```

---

**Documentación completa:** [FAQS_FULL.md](FAQS_FULL.md)
