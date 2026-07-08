# Miraki — URLs del sistema

> AWS: `44.195.68.214:8000` | Local: `localhost:8000`

---

## 🌐 Backend API REST

Base: `http://44.195.68.214:8000/api/v1/`

### Autenticación (`/api/v1/auth/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/auth/login/` | Iniciar sesión (JWT + cookies) |
| `POST` | `/auth/register/` | Registrarse |
| `POST` | `/auth/refresh/` | Refrescar token (cookie o body) |
| `POST` | `/auth/logout/` | Cerrar sesión |
| `GET`  | `/auth/me/` | Datos del usuario autenticado |
| `GET`  | `/auth/csrf/` | Obtener cookie CSRF |
| `POST` | `/auth/change-password/` | Cambiar contraseña |

### Cuentas (`/api/v1/accounts/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET`  | `/accounts/roles/` | Listar roles |
| `CRUD` | `/accounts/usuarios/` | Gestionar usuarios (admin) |
| `GET`  | `/accounts/me/` | Perfil del usuario actual |
| `GET`  | `/accounts/bitacora-accesos/` | Historial de accesos |

### Niños (`/api/v1/children/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET`  | `/children/ninos/` | Listar niños del tutor |
| `POST` | `/children/ninos/` | Crear niño |
| `GET`  | `/children/ninos/{id}/` | Detalle de niño |
| `PATCH`| `/children/ninos/{id}/` | Editar niño |
| `POST` | `/children/ninos/{id}/deactivate/` | Dar de baja |
| `POST` | `/children/ninos/{id}/reactivate/` | Reactivar |
| `POST` | `/children/ninos/{id}/photo/` | Subir foto |
| `POST` | `/children/ninos/{id}/assign-center/` | Asignar a centro |
| `POST` | `/children/ninos/{id}/remove-center/` | Quitar de centro |

### Zonas Seguras (`/api/v1/zones/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET`  | `/zones/zonas/` | Listar zonas |
| `POST` | `/zones/zonas/` | Crear zona |
| `GET`  | `/zones/zonas/{id}/` | Detalle de zona |
| `PATCH`| `/zones/zonas/{id}/` | Editar zona |
| `POST` | `/zones/zonas/{id}/deactivate/` | Desactivar zona |
| `POST` | `/zones/zonas/{id}/reactivate/` | Reactivar zona |
| `PUT`  | `/zones/zonas/{id}/horarios/` | Sincronizar horarios |
| `POST` | `/zones/zonas/{id}/vincular_nino/` | Vincular niño |
| `POST` | `/zones/zonas/{id}/desactivar_nino/` | Desvincular niño |

### Tracking / Posiciones (`/api/v1/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/posiciones/reportar/` | Kid reporta su ubicación |
| `GET`  | `/posiciones/ultima/` | Última posición de cada niño (tutor) |
| `GET`  | `/posiciones/historial/` | Historial de posiciones |

### Alertas (`/api/v1/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET`  | `/alertas/` | Listar alertas |
| `GET`  | `/alertas/{id}/` | Detalle de alerta |
| `PATCH`| `/alertas/{id}/mark-attended/` | Marcar atendida |
| `POST` | `/alertas/sos/` | Activar SOS (desde kid) |

### Dispositivos / Tokens Push (`/api/v1/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `CRUD` | `/dispositivos/` | Gestionar dispositivos GPS |
| `CRUD` | `/dispositivo-tokens/` | Registrar token FCM para push |

### Pareo / Vinculación Kid (`/api/v1/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/pareo/crear/` | Generar código de vinculación (tutor) |
| `GET`  | `/pareo/estado/{nino_id}/` | Estado del niño (kid) |
| `POST` | `/pareo/vincular/` | Vincular dispositivo kid |

### Instituciones / Centros (`/api/v1/institutions/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET`  | `/institutions/children/` | Niños del centro (admin centro) |
| `GET`  | `/institutions/my-center/` | Datos de mi centro |
| `GET`  | `/institutions/map/` | Mapa con niños del centro |

### Auditoría (`/api/v1/audit/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET`  | `/audit/bitacora/` | Bitácora general (admin) |

### Documentación

| Endpoint | Descripción |
|----------|-------------|
| `/api/v1/schema/` | OpenAPI 3.0 — schema JSON |
| `/api/v1/docs/` | Swagger UI — interfaz interactiva |
| `/admin/` | Django Admin |

---

## 🔌 WebSocket

| Endpoint | Auth | Descripción |
|----------|------|-------------|
| `ws://44.195.68.214:8000/ws/tracking/` | Token JWT (tutor) o X-Kid-Token (kid) | Monitoreo en tiempo real |

**Grupos de canal:**
- `tracking-{tutor_id}` — Posiciones en vivo para el tutor
- `tracking-{nino_id}` — Posiciones para el dispositivo kid

**Payload de posición (recibido):**
```json
{
  "type": "position",
  "child_id": 123,
  "nombre": "Pedro",
  "latitud": -17.7833,
  "longitud": -63.1821,
  "velocidad": 1.5,
  "bateria": 85,
  "fecha_posicion": "2026-07-08T15:30:00Z"
}
```

---

## 🖥️ Frontend Web — SIG-FRONT

Base: `http://44.195.68.214:5173` (Vite dev) o `http://localhost:5173`

| Ruta | Rol | Descripción |
|------|-----|-------------|
| `/` | — | Redirección según auth |
| `/login` | público | Iniciar sesión |
| `/register` | público | Registro |
| `/dashboard` | Tutor, Admin | Panel principal |
| `/children` | Tutor | Gestión de niños |
| `/center-children` | Admin Centro | Niños del centro |
| `/center` | Admin Centro | Gestión del centro |
| `/center-map` | Admin Centro | Mapa del centro |
| `/zones` | Tutor, Admin | Lista de zonas seguras |
| `/zones/create` | Tutor, Admin | Crear zona (dibujo en mapa) |
| `/zones/{id}` | Tutor, Admin | Detalle de zona |
| `/zones/{id}/edit` | Tutor, Admin | Editar zona |
| `/alerts` | Tutor | Lista de alertas |
| `/route-history` | Tutor | Historial de rutas |
| `/audit` | Super Admin | Bitácora general |
| `/access-audit` | Super Admin | Bitácora de accesos |
| `/forbidden` | — | Acceso denegado |

---

## 📱 Mobile — miraki_mobile y miraki_kid

Base API: `http://44.195.68.214:8000/api/v1/` (LAN: `http://192.168.0.13:8000/api/v1/`)

### miraki_mobile (App Tutor)

| Pantalla | Ruta GoRouter |
|----------|--------------|
| Home | `/home` |
| Niños | `/children` |
| Detalle niño | `/children/:id` |
| Crear/Editar niño | `/children/new`, `/children/:id/edit` |
| Mapa | `/map` |
| Zonas | `/zones` |
| Crear zona | `/zones/new` |
| Detalle zona | `/zones/:id` |
| Editar zona | `/zones/:id/edit` |
| Horarios zona | `/zones/:id/horarios` |
| Vincular niños | `/zones/:id/children` |
| Alertas | `/alerts` |
| Perfil | `/profile` |
| Login | `/login` |
| Registro | `/register` |

### miraki_kid (App Niño)

| Ruta | Descripción |
|------|-------------|
| `/` | Redirección |
| `/pairing` | Pantalla de vinculación |
| `/home` | Home con estado y ubicación |
| `/settings` | Ajustes y desconexión |

**Endpoints usados por miraki_kid:**
- `POST /api/v1/pareo/vincular/` — Enviar código de vinculación
- `GET /api/v1/pareo/estado/{nino_id}/` — Estado del niño
- `POST /api/v1/posiciones/reportar/` — Reportar posición GPS

---

## 🔑 Autenticación

| Tipo | Header / Cookie | Consumidor |
|------|----------------|------------|
| JWT (access) | `Authorization: Bearer <token>` o cookie `miraki_access` | Web, Mobile |
| JWT (refresh) | `Authorization: Bearer <token>` o cookie `miraki_refresh` | Web, Mobile |
| Pairing Token | `X-Kid-Token: <token>` | miraki_kid |
| WebSocket | `?token=<jwt>` (query string) | Web, Mobile |
