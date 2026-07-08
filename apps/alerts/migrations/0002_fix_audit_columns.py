from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('alerts', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE posicion RENAME COLUMN creado_por_id TO creado_por;',
            reverse_sql='ALTER TABLE posicion RENAME COLUMN creado_por TO creado_por_id;',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE posicion RENAME COLUMN modificado_por_id TO modificado_por;',
            reverse_sql='ALTER TABLE posicion RENAME COLUMN modificado_por TO modificado_por_id;',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE alerta RENAME COLUMN creado_por_id TO creado_por;',
            reverse_sql='ALTER TABLE alerta RENAME COLUMN creado_por TO creado_por_id;',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE alerta RENAME COLUMN modificado_por_id TO modificado_por;',
            reverse_sql='ALTER TABLE alerta RENAME COLUMN modificado_por TO modificado_por_id;',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE alerta RENAME COLUMN atendida_por_id TO atendida_por;',
            reverse_sql='ALTER TABLE alerta RENAME COLUMN atendida_por TO atendida_por_id;',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE dispositivo_token RENAME COLUMN creado_por_id TO creado_por;',
            reverse_sql='ALTER TABLE dispositivo_token RENAME COLUMN creado_por TO creado_por_id;',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE dispositivo_token RENAME COLUMN modificado_por_id TO modificado_por;',
            reverse_sql='ALTER TABLE dispositivo_token RENAME COLUMN modificado_por TO modificado_por_id;',
        ),
    ]
