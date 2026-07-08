from django.db import migrations

CREATE_VIEW = """
CREATE OR REPLACE VIEW vw_ultima_posicion_nino AS
SELECT DISTINCT ON (n.id_nino)
    n.id_nino,
    n.nombre,
    p.latitud,
    p.longitud,
    p.velocidad,
    p.fecha_posicion,
    p.fecha_recepcion,
    p.bateria
FROM nino n
    JOIN dispositivo d ON d.id_nino = n.id_nino
    JOIN posicion p ON p.id_dispositivo = d.id_dispositivo
ORDER BY n.id_nino, p.fecha_posicion DESC, p.id_posicion DESC;
"""

DROP_VIEW = "DROP VIEW IF EXISTS vw_ultima_posicion_nino;"


class Migration(migrations.Migration):
    """
    Crea (o reemplaza) la vista de última posición por niño.

    En producción la vista se creó vía el script SQL inicial; aquí la
    formalizamos en una migración para que la base de datos de test también la
    tenga. `CREATE OR REPLACE` la hace idempotente y agrega la columna `bateria`
    al final (permitido por Postgres al reemplazar una vista existente).
    """

    dependencies = [
        ('alerts', '0003_posicion_bateria'),
        ('children', '0003_nino_foto_public_id'),
        ('dispositivos', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_VIEW, reverse_sql=DROP_VIEW),
    ]
