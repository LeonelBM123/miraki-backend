from django.db import models

from apps.children.models import Nino
from apps.common.models import AuditMixin


class Dispositivo(AuditMixin):
    id_dispositivo = models.AutoField(primary_key=True, db_column='id_dispositivo')
    imei = models.CharField(max_length=20, unique=True, db_column='imei')
    sim_numero = models.CharField(max_length=20, null=True, blank=True, db_column='sim_numero')
    modelo = models.CharField(max_length=100, null=True, blank=True, db_column='modelo')
    estado = models.CharField(max_length=20, default='inactivo', db_column='estado')
    id_nino = models.OneToOneField(Nino, on_delete=models.PROTECT, db_column='id_nino', related_name='dispositivo')
    activo = models.BooleanField(default=True, db_column='activo')

    class Meta:
        db_table = 'dispositivo'

    def __str__(self):
        return self.imei
