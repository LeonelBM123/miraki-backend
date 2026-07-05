-- =====================================================================
-- PROYECTO: Sistema SIG de Monitoreo Infantil
-- MOTOR: PostgreSQL 15+ con extension PostGIS
-- Equivalente funcional del modelo v5 (originalmente en T-SQL/SQL Server,
-- usado como entregable/diagrama academico). Este es el script real
-- para el desarrollo con Django.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- util para funciones de hash si se necesitan a nivel de BD

-- =====================================================================
-- 1. CATALOGO DE ROLES
-- =====================================================================
CREATE TABLE rol (
    id_rol          SERIAL PRIMARY KEY,
    nombre_rol      VARCHAR(50) NOT NULL UNIQUE,
    descripcion     VARCHAR(200)
);

INSERT INTO rol (nombre_rol, descripcion) VALUES
    ('Tutor', 'Padre o tutor que monitorea a uno o mas ninos'),
    ('AdminCentro', 'Administrador de un centro educativo'),
    ('SuperAdmin', 'Administrador general del sistema');

-- =====================================================================
-- 2. USUARIO (autenticacion)
-- =====================================================================
CREATE TABLE usuario (
    id_usuario                      SERIAL PRIMARY KEY,
    correo                          VARCHAR(150) NOT NULL UNIQUE,
    password_hash                   VARCHAR(256) NOT NULL,
    password_salt                   VARCHAR(128),
    id_rol                          INTEGER NOT NULL REFERENCES rol(id_rol),
    activo                          BOOLEAN NOT NULL DEFAULT TRUE,
    ultimo_login                    TIMESTAMPTZ,
    intentos_fallidos               INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta                 TIMESTAMPTZ,

    fecha_ultimo_cambio_password    TIMESTAMPTZ,
    requiere_cambio_password        BOOLEAN NOT NULL DEFAULT FALSE,

    fecha_creacion                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion              TIMESTAMPTZ,
    creado_por                      INTEGER REFERENCES usuario(id_usuario),
    modificado_por                  INTEGER REFERENCES usuario(id_usuario)
);

CREATE INDEX ix_usuario_rol ON usuario(id_rol);

-- =====================================================================
-- 3. CENTRO EDUCATIVO (catalogo institucional, sin poligono propio)
-- =====================================================================
CREATE TABLE centro_educativo (
    id_centro           SERIAL PRIMARY KEY,
    nombre              VARCHAR(150) NOT NULL,
    direccion           VARCHAR(250),

    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion  TIMESTAMPTZ,
    creado_por          INTEGER REFERENCES usuario(id_usuario),
    modificado_por      INTEGER REFERENCES usuario(id_usuario)
);

-- =====================================================================
-- 4. ADMIN CENTRO
-- =====================================================================
CREATE TABLE admin_centro (
    id_admin_centro     SERIAL PRIMARY KEY,
    id_usuario          INTEGER NOT NULL UNIQUE REFERENCES usuario(id_usuario),
    id_centro           INTEGER NOT NULL REFERENCES centro_educativo(id_centro),
    nombre              VARCHAR(150) NOT NULL,
    telefono            VARCHAR(20),

    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion  TIMESTAMPTZ,
    creado_por          INTEGER REFERENCES usuario(id_usuario),
    modificado_por      INTEGER REFERENCES usuario(id_usuario)
);

-- =====================================================================
-- 5. TUTOR
-- =====================================================================
CREATE TABLE tutor (
    id_tutor            SERIAL PRIMARY KEY,
    id_usuario          INTEGER NOT NULL UNIQUE REFERENCES usuario(id_usuario),
    nombre              VARCHAR(150) NOT NULL,
    telefono            VARCHAR(20),

    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion  TIMESTAMPTZ,
    creado_por          INTEGER REFERENCES usuario(id_usuario),
    modificado_por      INTEGER REFERENCES usuario(id_usuario)
);

-- =====================================================================
-- 6. NINO
-- =====================================================================
CREATE TABLE nino (
    id_nino             SERIAL PRIMARY KEY,
    nombre              VARCHAR(150) NOT NULL,
    fecha_nacimiento    DATE,
    foto_url            VARCHAR(300),
    id_tutor            INTEGER NOT NULL REFERENCES tutor(id_tutor),

    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion  TIMESTAMPTZ,
    creado_por          INTEGER REFERENCES usuario(id_usuario),
    modificado_por      INTEGER REFERENCES usuario(id_usuario)
);

CREATE INDEX ix_nino_tutor ON nino(id_tutor);

-- =====================================================================
-- 7. ZONA SEGURA (institucional o personalizada)
--    poligono: PostGIS geography, SRID 4326 (lat/long estandar GPS)
-- =====================================================================
CREATE TABLE zona_segura (
    id_zona                 SERIAL PRIMARY KEY,
    nombre                  VARCHAR(150) NOT NULL,
    poligono                geography(POLYGON, 4326) NOT NULL,
    tipo                    VARCHAR(20) NOT NULL,

    id_centro               INTEGER REFERENCES centro_educativo(id_centro),
    id_tutor_propietario    INTEGER REFERENCES tutor(id_tutor),

    activo                  BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion          TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion      TIMESTAMPTZ,
    creado_por              INTEGER REFERENCES usuario(id_usuario),
    modificado_por          INTEGER REFERENCES usuario(id_usuario),

    CONSTRAINT ck_zona_tipo CHECK (tipo IN ('institucional','personalizada')),
    CONSTRAINT ck_zona_propietario CHECK (
        (tipo = 'institucional' AND id_centro IS NOT NULL AND id_tutor_propietario IS NULL)
        OR
        (tipo = 'personalizada' AND id_tutor_propietario IS NOT NULL AND id_centro IS NULL)
    )
);

-- Indice espacial GiST (equivalente PostGIS del "spatial index" de SQL Server)
CREATE INDEX six_zona_poligono ON zona_segura USING GIST (poligono);
CREATE INDEX ix_zona_centro ON zona_segura(id_centro);
CREATE INDEX ix_zona_tutor_propietario ON zona_segura(id_tutor_propietario);

-- =====================================================================
-- 7.1 HORARIO ZONA (multiples ventanas horarias por dia de la semana)
-- =====================================================================
CREATE TABLE horario_zona (
    id_horario          SERIAL PRIMARY KEY,
    id_zona             INTEGER NOT NULL REFERENCES zona_segura(id_zona),
    dia_semana          SMALLINT NOT NULL,     -- 1=Lunes ... 7=Domingo (ISO-8601)
    hora_inicio         TIME NOT NULL,
    hora_fin            TIME NOT NULL,

    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion  TIMESTAMPTZ,
    creado_por          INTEGER REFERENCES usuario(id_usuario),
    modificado_por      INTEGER REFERENCES usuario(id_usuario),

    CONSTRAINT ck_horario_dia CHECK (dia_semana BETWEEN 1 AND 7),
    CONSTRAINT ck_horario_horas CHECK (hora_inicio < hora_fin)
);

CREATE INDEX ix_horario_zona ON horario_zona(id_zona, dia_semana);

-- =====================================================================
-- 8. NINO_ZONA_SEGURA (N a N)
-- =====================================================================
CREATE TABLE nino_zona_segura (
    id_nino             INTEGER NOT NULL REFERENCES nino(id_nino),
    id_zona             INTEGER NOT NULL REFERENCES zona_segura(id_zona),
    activa              BOOLEAN NOT NULL DEFAULT TRUE,

    fecha_asociacion    TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion  TIMESTAMPTZ,
    creado_por          INTEGER REFERENCES usuario(id_usuario),
    modificado_por      INTEGER REFERENCES usuario(id_usuario),

    PRIMARY KEY (id_nino, id_zona)
);

-- =====================================================================
-- 9. DISPOSITIVO
-- =====================================================================
CREATE TABLE dispositivo (
    id_dispositivo      SERIAL PRIMARY KEY,
    imei                VARCHAR(20) NOT NULL UNIQUE,
    sim_numero          VARCHAR(20),
    modelo              VARCHAR(100),
    estado              VARCHAR(20) NOT NULL DEFAULT 'inactivo',
    id_nino             INTEGER NOT NULL UNIQUE REFERENCES nino(id_nino),

    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion  TIMESTAMPTZ,
    creado_por          INTEGER REFERENCES usuario(id_usuario),
    modificado_por      INTEGER REFERENCES usuario(id_usuario),

    CONSTRAINT ck_dispositivo_estado CHECK (estado IN ('activo','inactivo','sin_senal'))
);

-- =====================================================================
-- 10. POSICION (alto volumen; latitud/longitud + columna geography generada)
-- =====================================================================
CREATE TABLE posicion (
    id_posicion         BIGSERIAL PRIMARY KEY,
    id_dispositivo      INTEGER NOT NULL REFERENCES dispositivo(id_dispositivo),
    latitud             NUMERIC(9,6) NOT NULL,
    longitud            NUMERIC(9,6) NOT NULL,
    ubicacion           geography(POINT, 4326)
                        GENERATED ALWAYS AS (
                            ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)::geography
                        ) STORED,
    velocidad           NUMERIC(6,2),
    fecha_posicion      TIMESTAMPTZ NOT NULL,
    fecha_recepcion     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_posicion_dispositivo_fecha ON posicion(id_dispositivo, fecha_posicion DESC);
CREATE INDEX six_posicion_ubicacion ON posicion USING GIST (ubicacion);

-- =====================================================================
-- 11. ALERTA
-- =====================================================================
CREATE TABLE alerta (
    id_alerta           SERIAL PRIMARY KEY,
    id_nino             INTEGER NOT NULL REFERENCES nino(id_nino),
    id_zona             INTEGER REFERENCES zona_segura(id_zona),
    id_posicion         BIGINT NOT NULL REFERENCES posicion(id_posicion),
    tipo                VARCHAR(30) NOT NULL,
    fecha_alerta        TIMESTAMPTZ NOT NULL DEFAULT now(),
    atendida            BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_atencion      TIMESTAMPTZ,
    atendida_por        INTEGER REFERENCES usuario(id_usuario),

    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_alerta_tipo CHECK (tipo IN ('salida_zona','bateria_baja','sos'))
);

CREATE INDEX ix_alerta_nino ON alerta(id_nino, fecha_alerta DESC);
CREATE INDEX ix_alerta_zona ON alerta(id_zona);

-- =====================================================================
-- 12. PLAN
-- =====================================================================
CREATE TABLE plan (
    id_plan             SERIAL PRIMARY KEY,
    nombre              VARCHAR(100) NOT NULL,
    descripcion         VARCHAR(300),
    precio              NUMERIC(10,2) NOT NULL,
    moneda              VARCHAR(5) NOT NULL DEFAULT 'BOB',
    periodicidad        VARCHAR(20) NOT NULL,
    segmento            VARCHAR(10) NOT NULL,
    limite_ninos        INTEGER,
    limite_zonas        INTEGER,

    activo              BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion      TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion  TIMESTAMPTZ,
    creado_por          INTEGER REFERENCES usuario(id_usuario),
    modificado_por      INTEGER REFERENCES usuario(id_usuario),

    CONSTRAINT ck_plan_periodicidad CHECK (periodicidad IN ('mensual','anual')),
    CONSTRAINT ck_plan_segmento CHECK (segmento IN ('B2C','B2B'))
);

INSERT INTO plan (nombre, descripcion, precio, periodicidad, segmento, limite_ninos, limite_zonas) VALUES
    ('Plan Familiar Mensual', 'Suscripcion individual para tutores, hasta 3 ninos', 25.00, 'mensual', 'B2C', 3, 10),
    ('Plan Familiar Anual', 'Version anual del plan familiar con descuento', 250.00, 'anual', 'B2C', 3, 10),
    ('Plan Institucional Anual', 'Licencia para centros educativos, ninos ilimitados', 3500.00, 'anual', 'B2B', NULL, NULL);

-- =====================================================================
-- 13. SUSCRIPCION
-- =====================================================================
CREATE TABLE suscripcion (
    id_suscripcion          SERIAL PRIMARY KEY,
    id_plan                 INTEGER NOT NULL REFERENCES plan(id_plan),
    id_tutor                INTEGER REFERENCES tutor(id_tutor),
    id_centro               INTEGER REFERENCES centro_educativo(id_centro),

    fecha_inicio            DATE NOT NULL,
    fecha_fin               DATE,
    estado                  VARCHAR(20) NOT NULL DEFAULT 'pendiente_pago',
    renovacion_automatica   BOOLEAN NOT NULL DEFAULT TRUE,

    fecha_creacion          TIMESTAMPTZ NOT NULL DEFAULT now(),
    fecha_modificacion      TIMESTAMPTZ,
    creado_por              INTEGER REFERENCES usuario(id_usuario),
    modificado_por          INTEGER REFERENCES usuario(id_usuario),

    CONSTRAINT ck_suscripcion_estado CHECK (estado IN ('activa','cancelada','vencida','pendiente_pago')),
    CONSTRAINT ck_suscripcion_titular CHECK (
        (id_tutor IS NOT NULL AND id_centro IS NULL)
        OR
        (id_tutor IS NULL AND id_centro IS NOT NULL)
    )
);

CREATE INDEX ix_suscripcion_tutor ON suscripcion(id_tutor);
CREATE INDEX ix_suscripcion_centro ON suscripcion(id_centro);
CREATE INDEX ix_suscripcion_estado ON suscripcion(estado);

-- =====================================================================
-- 14. PAGO
-- =====================================================================
CREATE TABLE pago (
    id_pago                 SERIAL PRIMARY KEY,
    id_suscripcion          INTEGER NOT NULL REFERENCES suscripcion(id_suscripcion),
    monto                   NUMERIC(10,2) NOT NULL,
    moneda                  VARCHAR(5) NOT NULL DEFAULT 'BOB',
    fecha_pago              TIMESTAMPTZ NOT NULL DEFAULT now(),
    metodo_pago             VARCHAR(30) NOT NULL,
    estado_pago             VARCHAR(20) NOT NULL,
    referencia_externa      VARCHAR(100),

    fecha_creacion          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_pago_metodo CHECK (metodo_pago IN ('tarjeta','qr','transferencia')),
    CONSTRAINT ck_pago_estado CHECK (estado_pago IN ('exitoso','fallido','pendiente'))
);

CREATE INDEX ix_pago_suscripcion ON pago(id_suscripcion, fecha_pago DESC);

-- =====================================================================
-- 15. BITACORA (auditoria de cambios de datos)
-- =====================================================================
CREATE TABLE bitacora (
    id_bitacora         BIGSERIAL PRIMARY KEY,
    tabla_afectada      VARCHAR(100) NOT NULL,
    id_registro         VARCHAR(50) NOT NULL,
    operacion           VARCHAR(10) NOT NULL,
    datos_anteriores    JSONB,
    datos_nuevos        JSONB,
    id_usuario          INTEGER REFERENCES usuario(id_usuario),
    fecha_evento        TIMESTAMPTZ NOT NULL DEFAULT now(),
    direccion_ip        VARCHAR(45),

    CONSTRAINT ck_bitacora_operacion CHECK (operacion IN ('INSERT','UPDATE','DELETE'))
);

CREATE INDEX ix_bitacora_tabla_fecha ON bitacora(tabla_afectada, fecha_evento DESC);

-- =====================================================================
-- 15.1 BITACORA DE ACCESO (auditoria de login/logout)
-- =====================================================================
CREATE TABLE bitacora_acceso (
    id_bitacora_acceso  BIGSERIAL PRIMARY KEY,
    id_usuario          INTEGER REFERENCES usuario(id_usuario),
    correo_intento      VARCHAR(150) NOT NULL,
    tipo_evento         VARCHAR(20) NOT NULL,
    direccion_ip        VARCHAR(45),
    user_agent          VARCHAR(300),
    fecha_evento        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_bitacora_acceso_tipo CHECK (tipo_evento IN ('login_exitoso','login_fallido','logout'))
);

CREATE INDEX ix_bitacora_acceso_usuario_fecha ON bitacora_acceso(id_usuario, fecha_evento DESC);
CREATE INDEX ix_bitacora_acceso_correo ON bitacora_acceso(correo_intento);

-- =====================================================================
-- 16. FUNCION + TRIGGERS DE AUDITORIA GENERICOS
--     A diferencia de SQL Server, en PostgreSQL conviene UNA sola funcion
--     generica en PL/pgSQL reutilizada por varias tablas, en vez de
--     repetir el mismo bloque INSERT/UPDATE/DELETE en cada trigger.
-- =====================================================================
CREATE OR REPLACE FUNCTION fn_auditoria_generica()
RETURNS TRIGGER AS $$
DECLARE
    v_id_registro TEXT;
BEGIN
    IF (TG_OP = 'INSERT') THEN
        v_id_registro := (to_jsonb(NEW) ->> TG_ARGV[0]);
        INSERT INTO bitacora (tabla_afectada, id_registro, operacion, datos_nuevos)
        VALUES (TG_TABLE_NAME, v_id_registro, 'INSERT', to_jsonb(NEW));
        RETURN NEW;

    ELSIF (TG_OP = 'UPDATE') THEN
        v_id_registro := (to_jsonb(NEW) ->> TG_ARGV[0]);
        INSERT INTO bitacora (tabla_afectada, id_registro, operacion, datos_anteriores, datos_nuevos)
        VALUES (TG_TABLE_NAME, v_id_registro, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;

    ELSIF (TG_OP = 'DELETE') THEN
        v_id_registro := (to_jsonb(OLD) ->> TG_ARGV[0]);
        INSERT INTO bitacora (tabla_afectada, id_registro, operacion, datos_anteriores)
        VALUES (TG_TABLE_NAME, v_id_registro, 'DELETE', to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Nota: para ZonaSegura, to_jsonb(NEW) incluiria la columna 'poligono' (tipo geography),
-- que SI serializa en PostgreSQL (a diferencia de SQL Server), pero como texto WKB extenso.
-- Si se prefiere no auditar el poligono completo cada vez, usar una funcion especifica
-- que excluya esa columna (ver fn_auditoria_zona_segura mas abajo).

CREATE TRIGGER trg_alerta_auditoria
AFTER INSERT OR UPDATE OR DELETE ON alerta
FOR EACH ROW EXECUTE FUNCTION fn_auditoria_generica('id_alerta');

CREATE TRIGGER trg_dispositivo_auditoria
AFTER INSERT OR UPDATE OR DELETE ON dispositivo
FOR EACH ROW EXECUTE FUNCTION fn_auditoria_generica('id_dispositivo');

CREATE TRIGGER trg_suscripcion_auditoria
AFTER INSERT OR UPDATE OR DELETE ON suscripcion
FOR EACH ROW EXECUTE FUNCTION fn_auditoria_generica('id_suscripcion');

CREATE TRIGGER trg_pago_auditoria
AFTER INSERT OR UPDATE OR DELETE ON pago
FOR EACH ROW EXECUTE FUNCTION fn_auditoria_generica('id_pago');

-- Trigger especifico para ZonaSegura, excluyendo el poligono del JSON auditado
CREATE OR REPLACE FUNCTION fn_auditoria_zona_segura()
RETURNS TRIGGER AS $$
DECLARE
    v_datos_new JSONB;
    v_datos_old JSONB;
BEGIN
    IF (TG_OP = 'INSERT') THEN
        v_datos_new := to_jsonb(NEW) - 'poligono';
        INSERT INTO bitacora (tabla_afectada, id_registro, operacion, datos_nuevos)
        VALUES ('zona_segura', NEW.id_zona::TEXT, 'INSERT', v_datos_new);
        RETURN NEW;

    ELSIF (TG_OP = 'UPDATE') THEN
        v_datos_old := to_jsonb(OLD) - 'poligono';
        v_datos_new := to_jsonb(NEW) - 'poligono';
        INSERT INTO bitacora (tabla_afectada, id_registro, operacion, datos_anteriores, datos_nuevos)
        VALUES ('zona_segura', NEW.id_zona::TEXT, 'UPDATE', v_datos_old, v_datos_new);
        RETURN NEW;

    ELSIF (TG_OP = 'DELETE') THEN
        v_datos_old := to_jsonb(OLD) - 'poligono';
        INSERT INTO bitacora (tabla_afectada, id_registro, operacion, datos_anteriores)
        VALUES ('zona_segura', OLD.id_zona::TEXT, 'DELETE', v_datos_old);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_zona_segura_auditoria
AFTER INSERT OR UPDATE OR DELETE ON zona_segura
FOR EACH ROW EXECUTE FUNCTION fn_auditoria_zona_segura();

-- =====================================================================
-- 17. VISTAS DE APOYO
-- =====================================================================

CREATE VIEW vw_ultima_posicion_nino AS
SELECT DISTINCT ON (n.id_nino)
    n.id_nino,
    n.nombre AS nombre_nino,
    p.latitud,
    p.longitud,
    p.fecha_posicion
FROM nino n
INNER JOIN dispositivo di ON di.id_nino = n.id_nino
INNER JOIN posicion p ON p.id_dispositivo = di.id_dispositivo
ORDER BY n.id_nino, p.fecha_posicion DESC;

CREATE VIEW vw_zonas_activas_por_nino AS
SELECT
    n.id_nino, n.nombre AS nombre_nino,
    z.id_zona, z.nombre AS nombre_zona, z.tipo,
    nz.activa AS asociacion_activa
FROM nino n
INNER JOIN nino_zona_segura nz ON nz.id_nino = n.id_nino
INNER JOIN zona_segura z ON z.id_zona = nz.id_zona
WHERE z.activo = TRUE AND nz.activa = TRUE;

CREATE VIEW vw_horario_zonas AS
SELECT
    z.id_zona,
    z.nombre AS nombre_zona,
    h.dia_semana,
    CASE h.dia_semana
        WHEN 1 THEN 'Lunes' WHEN 2 THEN 'Martes' WHEN 3 THEN 'Miercoles'
        WHEN 4 THEN 'Jueves' WHEN 5 THEN 'Viernes' WHEN 6 THEN 'Sabado'
        WHEN 7 THEN 'Domingo'
    END AS nombre_dia,
    h.hora_inicio,
    h.hora_fin
FROM zona_segura z
INNER JOIN horario_zona h ON h.id_zona = z.id_zona
WHERE h.activo = TRUE;

CREATE VIEW vw_suscripciones_vigentes AS
SELECT
    s.id_suscripcion,
    p.nombre AS nombre_plan,
    p.segmento,
    s.id_tutor,
    t.nombre AS nombre_tutor,
    s.id_centro,
    c.nombre AS nombre_centro,
    s.estado,
    s.fecha_inicio,
    s.fecha_fin
FROM suscripcion s
INNER JOIN plan p ON p.id_plan = s.id_plan
LEFT JOIN tutor t ON t.id_tutor = s.id_tutor
LEFT JOIN centro_educativo c ON c.id_centro = s.id_centro
WHERE s.estado = 'activa';

-- =====================================================================
-- Ejemplo de consulta point-in-polygon (equivalente al STContains de SQL Server)
-- =====================================================================
-- SELECT z.id_zona, z.nombre,
--        ST_Contains(
--            z.poligono::geometry,
--            ST_SetSRID(ST_MakePoint(%(longitud)s, %(latitud)s), 4326)
--        ) AS dentro_de_zona
-- FROM vw_zonas_activas_por_nino v
-- INNER JOIN zona_segura z ON z.id_zona = v.id_zona
-- WHERE v.id_nino = %(id_nino)s;
--
-- Nota: ST_Contains trabaja con geometry, no geography directamente en todas
-- las versiones; por eso se castea con ::geometry. Alternativa mas simple
-- y recomendada con geography nativo: usar ST_Covers o ST_Intersects segun
-- el caso, que si soportan geography sin cast:
--
-- SELECT ST_Covers(z.poligono, ST_SetSRID(ST_MakePoint(%(longitud)s, %(latitud)s), 4326)::geography)
-- FROM zona_segura z WHERE z.id_zona = %(id_zona)s;

-- =====================================================================
-- FIN DEL SCRIPT (PostgreSQL/PostGIS - equivalente al modelo v5)
-- =====================================================================
