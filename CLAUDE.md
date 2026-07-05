# CLAUDE.md

Este archivo da contexto a Claude Code (u otras sesiones de Claude) sobre el proyecto,
sus decisiones de arquitectura y sus convenciones, para que el desarrollo sea consistente
sin tener que re-explicar todo en cada sesión.

## 1. Resumen del proyecto

Sistema de Información Geográfica (SIG) para el monitoreo en tiempo real de niños en edad
preescolar. Detecta, mediante análisis espacial (point-in-polygon), si un niño salió de una
o más zonas seguras definidas (institucionales o personalizadas), y notifica al tutor.

Modelo de negocio híbrido: B2B (licencia institucional a centros educativos) + B2C
(suscripción individual de tutores).

## 2. Stack tecnológico

- **Backend**: Django + Django REST Framework
- **Base de datos**: SQL Server (ver nota crítica en sección 3)
- **Frontend web**: React + TanStack Query/Router
- **Mobile**: Flutter
- **Tracking GPS**: Traccar (servidor open source), dispositivo físico = reloj GPS (protocolo GT06/WATCH)
- **Notificaciones**: Firebase Cloud Messaging
- **Infraestructura**: Docker + Docker Compose

## 3. Motor de base de datos (DECISIÓN CONFIRMADA)

**Desarrollo real: PostgreSQL + PostGIS.**

El script en T-SQL (`docs/modelo_datos_sig_monitoreo_v5.sql`) se generó únicamente como
entregable/diagrama para la materia académica (SQL Server). El script real que se usa para
desarrollar el sistema con Django está en `docs/modelo_datos_postgresql.sql`.

Esto significa:

- Se usa `django.contrib.gis` (GeoDjango) de forma nativa y completa — soporte oficial de
  Django para PostGIS, sin necesidad de SQL crudo para las consultas espaciales.
- Los campos `GEOGRAPHY` del script SQL Server se mapean a `PointField`/`PolygonField` de
  GeoDjango (`django.contrib.gis.db.models`).
- Las consultas point-in-polygon se hacen con el ORM: `ZonaSegura.objects.filter(poligono__covers=punto)`
  en vez de SQL crudo.
- Los triggers de auditoría (`Bitacora`, `BitacoraAcceso`) están reescritos en PL/pgSQL en
  el script de PostgreSQL (la sintaxis de triggers de SQL Server no es compatible).

## 4. Estructura de apps de Django

Cada app es un módulo autocontenido (modelos, serializers, views, urls) enfocado en una
responsabilidad. División propuesta, alineada con las entidades del modelo de datos v5:

```
apps/
├── accounts/       -> Usuario, Rol, autenticación (JWT), BitacoraAcceso
├── centros/        -> CentroEducativo, AdminCentro
├── tutores/        -> Tutor, Nino
├── zonas/          -> ZonaSegura, HorarioZona, Nino_ZonaSegura
├── dispositivos/   -> Dispositivo, integración con API de Traccar
├── tracking/       -> Posicion, job/webhook de recepción de posiciones
├── alertas/        -> Alerta, lógica point-in-polygon, notificaciones push (FCM)
├── suscripciones/  -> Plan, Suscripcion, Pago
└── auditoria/      -> Lectura de Bitacora (los triggers viven en SQL, no en Django)
```

Reglas de negocio que la capa de aplicación (no solo la base de datos) debe respetar:

- Una `ZonaSegura` es institucional (con `id_centro`, sin `id_tutor_propietario`) o
  personalizada (con `id_tutor_propietario`, sin `id_centro`). Nunca ambas, nunca ninguna.
- Una `Suscripcion` pertenece a un `Tutor` (B2C) o a un `CentroEducativo` (B2B), nunca ambos.
- Antes de crear un `Nino` o una `ZonaSegura`, validar `Plan.limite_ninos` / `Plan.limite_zonas`
  contra la suscripción activa del tutor/centro.
- Si una `ZonaSegura` no tiene registros en `HorarioZona`, se interpreta como vigente 24/7.

## 5. Modelo de datos

- **Script real de desarrollo**: `docs/modelo_datos_postgresql.sql` (PostgreSQL + PostGIS).
- **Script de referencia académica** (SQL Server, no se usa para desarrollo): `docs/modelo_datos_sig_monitoreo_v5.sql`.

Ambos contienen las mismas tablas, índices espaciales, triggers de auditoría (`bitacora`,
`bitacora_acceso`) y vistas de apoyo (`vw_ultima_posicion_nino`, `vw_zonas_activas_por_nino`,
`vw_horario_zonas`, `vw_suscripciones_vigentes`), adaptados a la sintaxis de cada motor.

El diagrama de clases equivalente está en `docs/diagrama_clases_v5.puml` (PlantUML).

## 6. Convenciones de código

- Nombres de modelos/campos en el ORM de Django: usar **snake_case en inglés** para el código
  Python (convención estándar de Django), pero mantener los nombres de tabla/columna en
  español vía `db_table` / `db_column` para que coincidan con el script SQL ya entregado
  académicamente. Ejemplo:

  ```python
  class Nino(models.Model):
      nombre = models.CharField(max_length=150, db_column='nombre')
      fecha_nacimiento = models.DateField(null=True, db_column='fecha_nacimiento')

      class Meta:
          db_table = 'Nino'
  ```

- Formateo: `black` + `isort` (ver sección de plugins recomendados).
- Tests: `pytest-django`, un archivo de tests por app (`apps/<app>/tests.py` o carpeta `tests/`).
- Commits: mensajes cortos en español, en modo imperativo (ej. "Agrega endpoint de zonas").

## 7. Roles del equipo (referencia)

1. SIG / Datos Geoespaciales
2. Backend (Django)
3. Frontend Web (React + TanStack)
4. Mobile (Flutter)
5. Infraestructura, QA y Hardware

## 8. Comandos frecuentes (a completar cuando el repo exista)

```bash
# Entorno virtual
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Correr servidor de desarrollo
python manage.py runserver

# Tests
pytest

# Linting/formato
black .
isort .
flake8 .
```

## 10. Paquetes Python clave (requirements.txt)

```
Django>=5.0
djangorestframework
djangorestframework-simplejwt
psycopg2-binary          # driver de PostgreSQL
django-environ
django-cors-headers
django-filter
drf-spectacular
django-extensions
celery
django-celery-beat
redis
Pillow
```

`django.contrib.gis` viene incluido con Django (no es un paquete aparte), pero requiere
que el sistema operativo tenga instaladas las librerías GEOS, GDAL y PROJ para funcionar
(se instalan vía `apt install binutils libproj-dev gdal-bin` en Ubuntu/Debian, o
directamente incluidas si se usa la imagen Docker `postgis/postgis` para la base de datos).

## 11. Pendientes de decisión (revisar con el equipo)

- [ ] Confirmar si el pago del CentroEducativo (B2B) exime o no a los tutores de pagar su
      propia suscripción B2C individual.
- [ ] Definir quién vincula a un Nino con la zona institucional del colegio: ¿el Tutor al
      registrar al niño, o el AdminCentro al inscribirlo en su sistema?
