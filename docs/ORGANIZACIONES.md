# Organizaciones - Espacios Compartidos

## Endpoints

| Método | URL                                     | Descripción     |
| ------ | --------------------------------------- | --------------- |
| GET    | `/organizations`                        | Listar mis orgs |
| POST   | `/organizations`                        | Crear org       |
| POST   | `/organizations/{id}/members`           | Invitar usuario |
| DELETE | `/organizations/{id}/members/{user_id}` | Remover usuario |

## Ejemplos

### Crear organización

```bash
POST /api/v1/organizations
{
  "nombre": "Mi Empresa",
  "descripcion": "Workspace compartido"
}
```

### Invitar miembro

```bash
POST /api/v1/organizations/org_123/members
{
  "email": "usuario@example.com",
  "rol": "editor"
}
```

**Roles:** owner, admin, editor, viewer

---

**Documentación completa:** [ORGANIZACIONES_FULL.md](ORGANIZACIONES_FULL.md)
