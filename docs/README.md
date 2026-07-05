# Miraki backend

## Cómo correr el proyecto

Guía completa (Docker, venv local, o venv reusando tus propias credenciales
de Postgres) en [SETUP.md](SETUP.md). Resumen rápido con Docker:

```bash
cd miraki-backend
cp .env.example .env
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

- API: http://localhost:8000/api/v1/
- Swagger: http://localhost:8000/api/v1/docs/
- Admin: http://localhost:8000/admin/

Resumen rápido con venv local — **requiere que antes hayas creado la BD +
extensión postgis y configurado `.env`** (rutas de GDAL/GEOS incluidas); ver
Opción B/C en [SETUP.md](SETUP.md) para esos dos pasos previos:

```bash
cd miraki-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Cómo probar la API

Con el servidor corriendo, abre `http://localhost:8000/api/v1/docs/`
(Swagger). Para probar endpoints protegidos con JWT:

1. `POST /api/v1/auth/register/` (o `login/` si ya tienes usuario) → "Try it
   out" → Execute. Copia el valor de `"access"` de la respuesta.
2. Botón **"Authorize"** (candado, arriba a la derecha) → pega **solo el
   token** en `jwtAuth` (Swagger agrega el prefijo `Bearer` solo) → Authorize.
3. Ya puedes probar endpoints protegidos (ej. `GET /api/v1/accounts/usuarios/`).

El `access` token expira en 60 minutos (`SIMPLE_JWT.ACCESS_TOKEN_LIFETIME`);
después de eso repite el login o usa `POST /api/v1/auth/refresh/` y vuelve a
pegar el nuevo token en "Authorize".

## Endpoints por app

- [`accounts.md`](accounts.md) — Rol, Usuario, BitacoraAcceso, autenticación JWT.

(Cada app nueva agrega su propio `docs/<app>.md` con esta misma estructura.)

## Documentación de datos

`docs/modelo_datos_postgresql.sql` es el script SQL **fuente de verdad** para
PostgreSQL/PostGIS (equivalente funcional del modelo v5, ver CLAUDE.md
secciones 3 y 5). Los modelos Django de este backend deben coincidir con ese
script. `docs/modelo_datos_sig_monitoreo_v2.sql` es una versión anterior (v2,
T-SQL/SQL Server) que se conserva solo como referencia histórica — ya
superada por el script real (por ejemplo, la v2 no separaba `HorarioZona` de
`ZonaSegura` ni incluía las tablas de `suscripciones`, que sí están en el
script v5/PostgreSQL). Todavía no existe `diagrama_clases_v5.puml`.

Esta primera etapa del backend solo implementa las tablas `rol`, `usuario` y
`bitacora_acceso` del script (apps `apps/common` y `apps/accounts`, con los
endpoints de autenticación JWT). El resto de tablas (`centro_educativo`,
`admin_centro`, `tutor`, `nino`, `zona_segura`, `horario_zona`,
`nino_zona_segura`, `dispositivo`, `posicion`, `alerta`, `plan`,
`suscripcion`, `pago`, `bitacora`) quedan para una siguiente etapa.

## Desviaciones documentadas de los modelos Django respecto al script SQL

- `Usuario` es el `AUTH_USER_MODEL` real de Django (extiende `AbstractBaseUser`
  + `PermissionsMixin`) en vez de un modelo aparte con JWT manual, para que
  `createsuperuser` y el Django Admin funcionen de forma nativa.
- No existe columna `password_salt` en el modelo Django (el script SQL sí la
  define, nullable): el hash de contraseñas de Django (PBKDF2) ya embebe el
  salt dentro del propio `password_hash`, así que esa columna quedaría sin uso
  real.
- Los roles sembrados por la migración de datos (`0002_seed_roles.py`) usan
  exactamente los mismos valores de `nombre_rol` que el `INSERT` del script
  SQL: `'Tutor'`, `'AdminCentro'`, `'SuperAdmin'` (no snake_case).
- Cuando se implemente `apps/zonas` (tabla `nino_zona_segura`), se usará una
  PK autoincremental (`id`) + `UniqueConstraint(id_nino, id_zona)` en vez de
  la PK compuesta real `(id_nino, id_zona)` del script, porque Django REST
  Framework no soporta bien rutas de detalle con PK compuesta.
- `POST /api/v1/auth/register/` en esta etapa solo crea un `Usuario` (no crea
  todavía un `Tutor`, ya que `apps/tutores` aún no existe).
