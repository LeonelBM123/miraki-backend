# Generated manually because GDAL is unavailable in the local environment.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0003_tutor'),
        ('children', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dispositivo',
            fields=[
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')),
                ('fecha_modificacion', models.DateTimeField(auto_now=True, db_column='fecha_modificacion')),
                ('id_dispositivo', models.AutoField(db_column='id_dispositivo', primary_key=True, serialize=False)),
                ('imei', models.CharField(db_column='imei', max_length=20, unique=True)),
                ('sim_numero', models.CharField(blank=True, db_column='sim_numero', max_length=20, null=True)),
                ('modelo', models.CharField(blank=True, db_column='modelo', max_length=100, null=True)),
                ('estado', models.CharField(db_column='estado', default='inactivo', max_length=20)),
                ('activo', models.BooleanField(db_column='activo', default=True)),
                ('creado_por', models.ForeignKey(blank=True, db_column='creado_por', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('id_nino', models.OneToOneField(db_column='id_nino', on_delete=django.db.models.deletion.PROTECT, related_name='dispositivo', to='children.nino')),
                ('modificado_por', models.ForeignKey(blank=True, db_column='modificado_por', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'dispositivo',
            },
        ),
    ]
