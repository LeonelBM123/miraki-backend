# Endpoints — `apps/accounts`

Modelos: `Rol`, `Usuario` (`AUTH_USER_MODEL`), `BitacoraAcceso`.

Todos los endpoints requieren `Authorization: Bearer <access_token>` salvo
donde se indique **Público**. Ver [README.md](README.md#cómo-probar-la-api)
para cómo probar con JWT en Swagger.

## Autenticación — prefijo `/api/v1/auth/`

| Método | Ruta | Auth | Body | Respuesta |
|---|---|---|---|---|
| POST | `/api/v1/auth/register/` | Público | `{correo, password}` | `201` Usuario creado (sin password) |
| POST | `/api/v1/auth/login/` | Público | `{correo, password}` | `200 {refresh, access}` — registra `BitacoraAcceso` (`login_exitoso`/`login_fallido`) |
| POST | `/api/v1/auth/refresh/` | Público | `{refresh}` | `200 {access, refresh}` — rota el refresh (`ROTATE_REFRESH_TOKENS=True`) |
| POST | `/api/v1/auth/change-password/` | JWT | `{password_actual, password_nuevo}` | `200 {detail}` |
| POST | `/api/v1/auth/logout/` | JWT | `{refresh}` | `205` — invalida (blacklist) el refresh token y registra `BitacoraAcceso` (`logout`) |

Notas:
- `register` en esta etapa solo crea el `Usuario` (rol `Tutor` por defecto);
  no crea todavía un `Tutor` porque esa app no existe aún (ver
  [README.md](README.md)).
- `password` nunca se expone en las respuestas de ningún endpoint.

## CRUD — prefijo `/api/v1/accounts/`

Router estándar de DRF (`DefaultRouter`): cada recurso expone
`GET`/`POST` en la ruta de lista y `GET`/`PUT`/`PATCH`/`DELETE` en
`.../{id}/`. Todos requieren JWT y están paginados (20 por página).

| Recurso | Ruta base | Tipo | Notas |
|---|---|---|---|
| Roles | `/api/v1/accounts/roles/` | CRUD completo | `id_rol`, `nombre_rol`, `descripcion` |
| Usuarios | `/api/v1/accounts/usuarios/` | CRUD completo | No expone `password`; `id_usuario`/`last_login`/`fecha_creacion`/`fecha_modificacion` son de solo lectura |
| Bitácora de accesos | `/api/v1/accounts/bitacora-accesos/` | Solo lectura | `list`/`retrieve` únicamente — ni la API ni el Django Admin permiten crear/editar/borrar registros |

## Documentación / esquema

| Ruta | Descripción |
|---|---|
| `/api/v1/schema/` | Esquema OpenAPI (JSON/YAML, drf-spectacular) |
| `/api/v1/docs/` | Swagger UI |
| `/admin/` | Django Admin |
