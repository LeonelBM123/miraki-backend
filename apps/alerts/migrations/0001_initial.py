# Generated manually — GDAL/PostGIS not available in development environment
# Run `python manage.py makemigrations alerts --check` to verify after DB setup

from django.contrib.gis.db.models import fields as gis_fields
from django.contrib.postgres.indexes import GistIndex
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dispositivos', '0001_initial'),
        ('zones', '0001_initial'),
        ('children', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Posicion',
            fields=[
                ('id_posicion', models.AutoField(db_column='id_posicion', primary_key=True, serialize=False)),
                ('latitud', models.DecimalField(db_column='latitud', decimal_places=6, max_digits=9)),
                ('longitud', models.DecimalField(db_column='longitud', decimal_places=6, max_digits=9)),
                ('ubicacion', gis_fields.PointField(blank=True, db_column='ubicacion', geography=True, null=True, srid=4326)),
                ('velocidad', models.DecimalField(blank=True, db_column='velocidad', decimal_places=2, max_digits=6, null=True)),
                ('fecha_posicion', models.DateTimeField(db_column='fecha_posicion')),
                ('fecha_recepcion', models.DateTimeField(auto_now_add=True, db_column='fecha_recepcion')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_modificacion', models.DateTimeField(auto_now=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounts.usuario')),
                ('modificado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounts.usuario')),
                ('id_dispositivo', models.ForeignKey(db_column='id_dispositivo', on_delete=django.db.models.deletion.CASCADE, related_name='posiciones', to='dispositivos.dispositivo')),
            ],
            options={
                'db_table': 'posicion',
            },
        ),
        migrations.CreateModel(
            name='Alerta',
            fields=[
                ('id_alerta', models.AutoField(db_column='id_alerta', primary_key=True, serialize=False)),
                ('tipo', models.CharField(choices=[('salida_zona', 'Salida de zona'), ('bateria_baja', 'Batería baja'), ('sos', 'SOS')], db_column='tipo', max_length=30)),
                ('fecha_alerta', models.DateTimeField(auto_now_add=True, db_column='fecha_alerta')),
                ('atendida', models.BooleanField(db_column='atendida', default=False)),
                ('fecha_atencion', models.DateTimeField(blank=True, db_column='fecha_atencion', null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_modificacion', models.DateTimeField(auto_now=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounts.usuario')),
                ('modificado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounts.usuario')),
                ('atendida_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alertas_atendidas', to='accounts.usuario')),
                ('id_nino', models.ForeignKey(db_column='id_nino', on_delete=django.db.models.deletion.CASCADE, related_name='alertas', to='children.nino')),
                ('id_posicion', models.ForeignKey(blank=True, db_column='id_posicion', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alertas', to='alerts.posicion')),
                ('id_zona', models.ForeignKey(blank=True, db_column='id_zona', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alertas', to='zones.zonasegura')),
            ],
            options={
                'db_table': 'alerta',
            },
        ),
        migrations.CreateModel(
            name='DispositivoToken',
            fields=[
                ('id', models.AutoField(db_column='id', primary_key=True, serialize=False)),
                ('token', models.CharField(db_column='token', max_length=512, unique=True)),
                ('plataforma', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS'), ('web', 'Web')], db_column='plataforma', max_length=20)),
                ('activo', models.BooleanField(db_column='activo', default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_modificacion', models.DateTimeField(auto_now=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounts.usuario')),
                ('id_dispositivo', models.ForeignKey(blank=True, db_column='id_dispositivo', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tokens_push', to='dispositivos.dispositivo')),
                ('id_usuario', models.ForeignKey(db_column='id_usuario', on_delete=django.db.models.deletion.CASCADE, related_name='dispositivo_tokens', to='accounts.usuario')),
                ('modificado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounts.usuario')),
            ],
            options={
                'db_table': 'dispositivo_token',
            },
        ),
        migrations.AddIndex(
            model_name='alerta',
            index=models.Index(fields=['id_nino', '-fecha_alerta'], name='ix_alerta_nino_fecha'),
        ),
        migrations.AddIndex(
            model_name='alerta',
            index=models.Index(fields=['id_zona'], name='ix_alerta_zona'),
        ),
        migrations.AddIndex(
            model_name='alerta',
            index=models.Index(fields=['atendida', '-fecha_alerta'], name='ix_alerta_atendida_fecha'),
        ),
        migrations.AddIndex(
            model_name='posicion',
            index=models.Index(fields=['id_dispositivo', '-fecha_posicion'], name='ix_posicion_dispositivo_fecha'),
        ),
        migrations.AddIndex(
            model_name='posicion',
            index=GistIndex(fields=['ubicacion'], name='six_posicion_ubicacion'),
        ),
        migrations.AddIndex(
            model_name='dispositivotoken',
            index=models.Index(fields=['id_usuario', 'activo'], name='ix_disp_token_usr_activo'),
        ),
    ]
