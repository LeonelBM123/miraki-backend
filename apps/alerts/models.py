from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.db import models

from apps.accounts.models import Usuario
from apps.children.models import Nino
from apps.common.models import AuditMixin
from apps.dispositivos.models import Dispositivo
from apps.zones.models import ZonaSegura


class Posicion(AuditMixin):
    id_posicion = models.AutoField(primary_key=True, db_column='id_posicion')
    id_dispositivo = models.ForeignKey(
        Dispositivo,
        on_delete=models.CASCADE,
        db_column='id_dispositivo',
        related_name='posiciones',
    )
    latitud = models.DecimalField(max_digits=9, decimal_places=6, db_column='latitud')
    longitud = models.DecimalField(max_digits=9, decimal_places=6, db_column='longitud')
    ubicacion = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True,
        blank=True,
        db_column='ubicacion',
    )
    velocidad = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        db_column='velocidad',
    )
    bateria = models.SmallIntegerField(
        null=True,
        blank=True,
        db_column='bateria',
        help_text='Nivel de batería del dispositivo (0-100) al reportar la posición.',
    )
    fecha_posicion = models.DateTimeField(db_column='fecha_posicion')
    fecha_recepcion = models.DateTimeField(auto_now_add=True, db_column='fecha_recepcion')

    class Meta:
        db_table = 'posicion'
        indexes = [
            models.Index(fields=['id_dispositivo', '-fecha_posicion'], name='ix_posicion_dispositivo_fecha'),
            GistIndex(fields=['ubicacion'], name='six_posicion_ubicacion'),
        ]

    def __str__(self):
        return f'Posicion {self.id_posicion} - {self.fecha_posicion}'


class Alerta(AuditMixin):
    class TipoAlerta(models.TextChoices):
        SALIDA_ZONA = 'salida_zona', 'Salida de zona'
        BATERIA_BAJA = 'bateria_baja', 'Batería baja'
        SOS = 'sos', 'SOS'

    id_alerta = models.AutoField(primary_key=True, db_column='id_alerta')
    id_nino = models.ForeignKey(Nino, on_delete=models.CASCADE, db_column='id_nino', related_name='alertas')
    id_zona = models.ForeignKey(
        ZonaSegura,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='id_zona',
        related_name='alertas',
    )
    id_posicion = models.ForeignKey(
        'Posicion',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='id_posicion',
        related_name='alertas',
    )
    tipo = models.CharField(max_length=30, choices=TipoAlerta.choices, db_column='tipo')
    fecha_alerta = models.DateTimeField(auto_now_add=True, db_column='fecha_alerta')
    atendida = models.BooleanField(default=False, db_column='atendida')
    fecha_atencion = models.DateTimeField(null=True, blank=True, db_column='fecha_atencion')
    atendida_por = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='atendida_por',
        related_name='alertas_atendidas',
    )

    class Meta:
        db_table = 'alerta'
        indexes = [
            models.Index(fields=['id_nino', '-fecha_alerta'], name='ix_alerta_nino_fecha'),
            models.Index(fields=['id_zona'], name='ix_alerta_zona'),
            models.Index(fields=['atendida', '-fecha_alerta'], name='ix_alerta_atendida_fecha'),
        ]

    def __str__(self):
        return f'Alerta {self.id_alerta} - {self.get_tipo_display()} - {self.fecha_alerta}'


class DispositivoToken(AuditMixin):
    class Plataforma(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'
        WEB = 'web', 'Web'

    id = models.AutoField(primary_key=True, db_column='id')
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='id_usuario',
        related_name='dispositivo_tokens',
    )
    id_dispositivo = models.ForeignKey(
        Dispositivo,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='id_dispositivo',
        related_name='tokens_push',
    )
    token = models.CharField(max_length=512, unique=True, db_column='token')
    plataforma = models.CharField(max_length=20, choices=Plataforma.choices, db_column='plataforma')
    activo = models.BooleanField(default=True, db_column='activo')

    class Meta:
        db_table = 'dispositivo_token'
        indexes = [
            models.Index(fields=['id_usuario', 'activo'], name='ix_disp_token_usr_activo'),
        ]

    def __str__(self):
        return f'{self.id_usuario_id} - {self.plataforma}'
