# Contratos API PB-01 a PB-05

Prefijo base: `/api/v1/`

## Auth

### POST `/auth/register/`

Registra una cuenta publica de tipo `tutor` o `admin_centro`. No inicia sesion y no devuelve tokens.

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

```json
{
  "correo": "tutor@email.com",
  "password": "StrongPass123!"
}
```

Respuesta `200`:

```json
{
  "refresh": "...",
  "access": "...",
  "usuario": {
    "id_usuario": 1,
    "correo": "tutor@email.com",
    "rol": "Tutor"
  }
}
```

Registra `login_exitoso` o `login_fallido` en `BitacoraAcceso`. Al quinto fallo bloquea la cuenta durante 15 minutos.

### POST `/auth/logout/`

Requiere `Authorization: Bearer <access>`.

```json
{
  "refresh": "..."
}
```

Respuesta `200`:

```json
{
  "detail": "Sesion cerrada correctamente."
}
```

## Ninos

Todos los endpoints requieren usuario autenticado con rol `Tutor`.

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
