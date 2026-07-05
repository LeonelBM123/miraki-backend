# Cómo correr el backend de Miraki

Hay dos formas de correrlo. **Docker es la recomendada para el equipo** porque
funciona igual en Windows/Mac/Linux y ya trae instalado todo lo que GeoDjango
necesita (GDAL/GEOS/PROJ). La opción con entorno virtual (venv) nativo es más
rápida para iterar en el día a día si ya tienes Postgres instalado, pero
requiere pasos extra específicos de tu sistema operativo.

## Opción A — Docker (recomendada, multiplataforma)

Requisitos: Docker Desktop instalado y corriendo.

```bash
cd miraki-backend
cp .env.example .env      # valores por defecto ya funcionan con docker-compose
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

- API: http://localhost:8000/api/v1/
- Swagger: http://localhost:8000/api/v1/docs/
- Admin: http://localhost:8000/admin/

No necesitas instalar Python, Postgres, PostGIS ni GDAL en tu máquina: todo
vive dentro de los contenedores (`db`, `web`, `redis`).

## Opción B — venv local (Windows, sin Docker)

Solo si ya tienes PostgreSQL instalado localmente y prefieres correr Django
nativo (más rápido para debug/autocompletado del IDE). GeoDjango necesita las
librerías GEOS/GDAL/PROJ; si instalaste PostgreSQL con el instalador de EDB y
elegiste incluir PostGIS (Stack Builder), esas DLLs ya vienen en la carpeta
`bin` de tu instalación de Postgres — no hace falta instalar OSGeo4W aparte.

1. **Crear la base de datos** (en pgAdmin o psql, contra tu Postgres local):
   ```sql
   CREATE ROLE miraki_user WITH LOGIN PASSWORD 'miraki_pass';
   CREATE DATABASE miraki_db OWNER miraki_user;
   -- conéctate a miraki_db (no a postgres) antes de correr esto:
   CREATE EXTENSION postgis;
   ```
2. **Crear el entorno virtual e instalar dependencias**:
   ```bash
   cd miraki-backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Configurar `.env`** (copia `.env.example` y ajusta):
   ```
   DATABASE_URL=postgis://miraki_user:miraki_pass@localhost:5432/miraki_db
   GDAL_LIBRARY_PATH=C:\Program Files\PostgreSQL\<TU_VERSION>\bin\libgdal-<NUMERO>.dll
   GEOS_LIBRARY_PATH=C:\Program Files\PostgreSQL\<TU_VERSION>\bin\libgeos_c.dll
   ```
   Estas dos últimas rutas **dependen de tu instalación** (versión de Postgres
   y número de la DLL de GDAL). Revisa qué archivos existen en tu carpeta
   `bin` con `dir "C:\Program Files\PostgreSQL\<TU_VERSION>\bin" | findstr /I "gdal geos"`
   y ajusta el nombre exacto. `REDIS_URL`/Redis no son necesarios todavía
   (Celery no está implementado aún).
4. **Migrar y crear superusuario**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

## Opción C — venv local, reusando un usuario Postgres que ya tengas

Si no quieres crear el rol `miraki_user` y prefieres usar un usuario/rol que
ya tengas en tu Postgres local (por ejemplo tu propio superusuario `postgres`,
u otro rol que ya uses para otros proyectos), puedes saltarte el `CREATE
ROLE` del paso 1 de la Opción B:

```sql
CREATE DATABASE miraki_db OWNER tu_usuario_existente;
-- conéctate a miraki_db (no a postgres) antes de correr esto:
CREATE EXTENSION postgis;
```

Y en `.env` pones tus propias credenciales:

```
DATABASE_URL=postgis://tu_usuario_existente:tu_password@localhost:5432/miraki_db
```

El resto de pasos (venv, `GDAL_LIBRARY_PATH`/`GEOS_LIBRARY_PATH`, migrate,
createsuperuser) son iguales a la Opción B.

**Trade-off a tener en cuenta**: si reusas un usuario que ya tiene acceso a
otras bases de datos tuyas (como el superusuario `postgres`), pierdes el
aislamiento de mínimo privilegio — un bug en Miraki podría, en teoría, tocar
tus otras bases de datos locales (de otros proyectos que tengas en el mismo
Postgres). Para desarrollo individual en tu propia máquina esto normalmente
es un riesgo aceptable; para un servidor compartido por el equipo, se
recomienda seguir usando un rol dedicado como en la Opción B.

### Nota sobre `.env`

`.env` nunca se sube al repositorio (está en `.gitignore`) porque las rutas de
GDAL/Postgres son específicas de cada máquina. Cada dev debe copiar
`.env.example` y ajustar sus propios valores. `.env.example` trae los valores
por defecto para Docker (Opción A); para la Opción B, cada quien pone su
propia ruta local.

## Troubleshooting

### `UnicodeDecodeError` al correr `migrate`/`makemigrations` (venv local, Windows)

Si ves algo como:

```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf3 in position 85: invalid continuation byte
```

No es el error real — es psycopg2 fallando al decodificar el mensaje de error
que manda Postgres, porque tu servidor tiene `lc_messages` en español (los
acentos vienen en Latin-1, no UTF-8). El error real casi siempre es más
simple: **usuario/contraseña incorrectos o la base de datos no existe**.
Para verlo directamente:

```bash
venv\Scripts\python.exe -c "import psycopg2; psycopg2.connect(host='localhost', port=5432, dbname='miraki_db', user='miraki_user', password='miraki_pass')"
```

y revisa el mensaje `FATAL: ...` en los bytes crudos del error. Ajusta las
credenciales en `.env` o vuelve a correr el `CREATE ROLE`/`CREATE DATABASE`
según corresponda.

### `ERROR: CREATE DATABASE no puede ser ejecutado dentro de un bloque de transacción` (pgAdmin)

pgAdmin manda varias líneas juntas como una sola transacción, y `CREATE
DATABASE` no puede ir dentro de una transacción. Ejecuta cada sentencia SQL
por separado (selecciona solo una línea a la vez antes de correr F5).

### "Failed to fetch" al probar en Swagger

Es el mensaje genérico de Swagger UI para cualquier fetch fallido — casi
siempre significa que el servidor (`runserver` o `docker compose up`) no está
corriendo en ese momento, no necesariamente un problema real de CORS.
Confirma que el server sigue arriba y vuelve a intentar.
