from django.conf import settings
from django.db import models


class Bitacora(models.Model):
    class Operacion(models.TextChoices):
        INSERT = 'INSERT', 'Insert'
        UPDATE = 'UPDATE', 'Update'
        DELETE = 'DELETE', 'Delete'

    id_bitacora = models.BigAutoField(primary_key=True, db_column='id_bitacora')
    tabla_afectada = models.CharField(max_length=100, db_column='tabla_afectada')
    id_registro = models.CharField(max_length=50, db_column='id_registro')
    operacion = models.CharField(max_length=10, choices=Operacion.choices, db_column='operacion')
    datos_anteriores = models.JSONField(null=True, blank=True, db_column='datos_anteriores')
    datos_nuevos = models.JSONField(null=True, blank=True, db_column='datos_nuevos')
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='id_usuario',
        related_name='bitacoras',
    )
    fecha_evento = models.DateTimeField(auto_now_add=True, db_column='fecha_evento')
    direccion_ip = models.GenericIPAddressField(null=True, blank=True, db_column='direccion_ip')

    class Meta:
        db_table = 'bitacora'
        indexes = [
            models.Index(fields=['tabla_afectada', '-fecha_evento'], name='ix_bitacora_tabla_fecha'),
        ]

    def __str__(self):
        return f'{self.tabla_afectada} {self.operacion} {self.id_registro}'
