# Endpoints - `apps/accounts`

Modelos principales: `Rol`, `Usuario`, `Tutor`, `BitacoraAcceso`.

La autenticacion principal para el frontend usa cookies HttpOnly:

- `miraki_access`: access JWT.
- `miraki_refresh`: refresh JWT.

El frontend debe usar `credentials: "include"` y enviar `X-CSRFToken` en metodos mutables cuando exista cookie `csrftoken`. Se mantiene fallback `Authorization: Bearer <access>` para Swagger, desarrollo y clientes tecnicos.

## Autenticacion - prefijo `/api/v1/auth/`

| Metodo | Ruta | Auth | Body | Respuesta |
|---|---|---|---|---|
| GET | `/api/v1/auth/csrf/` | Publico | - | `200 {detail}` y cookie `csrftoken` |
| POST | `/api/v1/auth/register/` | Publico | Registro Tutor/AdminCentro | `201` usuario + perfil, sin tokens |
| POST | `/api/v1/auth/login/` | Publico | `{correo, password}` | `200 {usuario}` y cookies JWT HttpOnly |
| GET | `/api/v1/auth/me/` | Cookie/Bearer | - | `200 {id_usuario, correo, rol}` |
| POST | `/api/v1/auth/refresh/` | Refresh cookie | - | `200 {detail}` y nueva access cookie |
| POST | `/api/v1/auth/change-password/` | Cookie/Bearer | `{password_actual, password_nuevo}` | `200 {detail}` |
| POST | `/api/v1/auth/logout/` | Cookie/Bearer | body opcional | `200 {detail}`; blacklist refresh y limpia cookies |

Notas:
- `login` registra `login_exitoso`/`login_fallido` en `BitacoraAcceso`.
- `logout` registra `logout` en `BitacoraAcceso`.
- `refresh` y `/me/` no generan eventos de acceso.
- `register` no inicia sesion automaticamente.
- Los JWT no se devuelven en JSON en el contrato principal del frontend.

## CRUD administrativo - prefijo `/api/v1/accounts/`

Router estandar de DRF (`DefaultRouter`). Estos endpoints estan restringidos a `SuperAdmin`.

| Recurso | Ruta base | Tipo | Notas |
|---|---|---|---|
| Roles | `/api/v1/accounts/roles/` | CRUD completo | `id_rol`, `nombre_rol`, `descripcion` |
| Usuarios | `/api/v1/accounts/usuarios/` | CRUD completo | No expone `password` |
| Bitacora de accesos | `/api/v1/accounts/bitacora-accesos/` | Solo lectura | Eventos de login/logout |

## Documentacion / esquema

| Ruta | Descripcion |
|---|---|
| `/api/v1/schema/` | Esquema OpenAPI |
| `/api/v1/docs/` | Swagger UI |
| `/admin/` | Django Admin |
