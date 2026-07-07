# Contratos API PB-01 a PB-05

Prefijo base: `/api/v1/`

El frontend debe usar `credentials: "include"` en todas las llamadas. Los JWT se transportan en cookies HttpOnly:

- access: `miraki_access`
- refresh: `miraki_refresh`

Redux debe guardar solo usuario/estado, no tokens. Para requests mutables con cookies, enviar `X-CSRFToken` usando la cookie `csrftoken`.

## Auth

### GET `/auth/csrf/`

Inicializa la cookie CSRF para que React pueda leer `csrftoken`.

Respuesta `200`:

```json
{
  "detail": "CSRF cookie initialized."
}
```

### POST `/auth/register/`

Registra una cuenta publica de tipo `tutor` o `admin_centro`. No inicia sesion, no establece cookies JWT y no devuelve tokens.

Tutor:

```json
{
  "correo": "tutor@email.com",
  "password": "StrongPass123!",
  "confirmar_password": "StrongPass123!",
  "tipo_cuenta": "tutor",
  "nombre": "Nombre Tutor",
  "telefono": "70000000"
}
```

AdminCentro:

```json
{
  "correo": "admin@centro.com",
  "password": "StrongPass123!",
  "confirmar_password": "StrongPass123!",
  "tipo_cuenta": "admin_centro",
  "nombre": "Nombre Administrador",
  "telefono": "70000000",
  "centro": {
    "nombre": "Nombre del Centro",
    "direccion": "Direccion escrita"
  }
}
```

Respuesta `201`:

```json
{
  "usuario": {
    "id_usuario": 1,
    "correo": "tutor@email.com",
    "rol": "Tutor"
  },
  "tipo_cuenta": "tutor",
  "perfil": {
    "id_tutor": 1,
    "nombre": "Nombre Tutor",
    "telefono": "70000000",
    "activo": true
  }
}
```

### POST `/auth/login/`

Request:

```json
{
  "correo": "tutor@email.com",
  "password": "StrongPass123!"
}
```

Respuesta `200`:

```json
{
  "usuario": {
    "id_usuario": 1,
    "correo": "tutor@email.com",
    "rol": "Tutor"
  }
}
```

El backend establece `miraki_access` y `miraki_refresh` como cookies HttpOnly. La respuesta no expone JWT. Registra `login_exitoso` o `login_fallido` en `BitacoraAcceso`; al quinto fallo bloquea la cuenta durante 15 minutos.

### GET `/auth/me/`

Requiere cookie `miraki_access` valida.

Respuesta `200`:

```json
{
  "id_usuario": 1,
  "correo": "tutor@email.com",
  "rol": "Tutor"
}
```

Sin access cookie valida responde `401`.

### POST `/auth/refresh/`

Lee `miraki_refresh` desde cookie HttpOnly. No requiere refresh en body para el frontend normal.

Respuesta `200`:

```json
{
  "detail": "Token renovado correctamente."
}
```

El backend reemplaza la cookie `miraki_access`. Como `ROTATE_REFRESH_TOKENS=True`, tambien reemplaza `miraki_refresh` cuando SimpleJWT emite refresh nuevo.

### POST `/auth/logout/`

Requiere cookie `miraki_access` valida. Lee `miraki_refresh` desde cookie, intenta blacklistearlo, limpia ambas cookies y registra logout.

Respuesta `200`:

```json
{
  "detail": "Sesion cerrada correctamente."
}
```

## Ninos

Todos los endpoints requieren usuario autenticado con rol `Tutor`. La autenticacion normal viene de cookie `miraki_access`.

### GET `/children/ninos/`

Lista los ninos activos del Tutor autenticado. Para incluir inactivos:

`GET /api/v1/children/ninos/?include_inactive=true`

### POST `/children/ninos/`

```json
{
  "nombre": "Mateo",
  "fecha_nacimiento": "2018-05-20",
  "foto_url": ""
}
```

Respuesta `201`:

```json
{
  "id_nino": 1,
  "nombre": "Mateo",
  "fecha_nacimiento": "2018-05-20",
  "foto_url": "",
  "activo": true,
  "fecha_creacion": "...",
  "fecha_modificacion": "..."
}
```

### GET `/children/ninos/{id}/`

Devuelve solo ninos propios. Un nino ajeno responde `404`.

### PATCH `/children/ninos/{id}/`

Permite editar `nombre`, `fecha_nacimiento` y `foto_url`. No permite cambiar `id_tutor` ni `activo`.

### POST `/children/ninos/{id}/deactivate/`

Baja logica: `activo=false`.

### POST `/children/ninos/{id}/reactivate/`

Reactivacion: `activo=true`.

## Auditoria

- `BitacoraAcceso`: solo login/logout.
- `Bitacora`: registro de cuenta, perfiles, centros y cambios de ninos.
- `/api/v1/accounts/bitacora-accesos/`: solo `SuperAdmin`.
- `/api/v1/audit/bitacora/`: solo `SuperAdmin`.

## RTK Query

Configuracion base esperada:

```ts
fetchBaseQuery({
  baseUrl: import.meta.env.VITE_API_URL,
  credentials: "include",
  prepareHeaders: (headers) => {
    const csrf = readCookie("csrftoken")
    if (csrf) headers.set("X-CSRFToken", csrf)
    return headers
  },
})
```

Bootstrap recomendado:

1. `GET /auth/csrf/`
2. `GET /auth/me/`
3. si `/me/` responde `401`, llamar `POST /auth/refresh/`
4. si refresh responde `200`, reintentar `/auth/me/`
5. si vuelve a fallar, estado `unauthenticated`
