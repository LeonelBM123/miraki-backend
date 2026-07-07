from django.conf import settings
from django.db import models

from apps.common.models import AuditMixin


class CentroEducativo(AuditMixin):
    id_centro = models.AutoField(primary_key=True, db_column='id_centro')
    nombre = models.CharField(max_length=150, db_column='nombre')
    direccion = models.TextField(db_column='direccion')
    activo = models.BooleanField(default=True, db_column='activo')

    class Meta:
        db_table = 'centro_educativo'

    def __str__(self):
        return self.nombre


class AdminCentro(AuditMixin):
    id_admin_centro = models.AutoField(primary_key=True, db_column='id_admin_centro')
    id_usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_usuario',
        related_name='admin_centro',
    )
    id_centro = models.OneToOneField(
        CentroEducativo,
        on_delete=models.PROTECT,
        db_column='id_centro',
        related_name='admin_centro',
    )
    nombre = models.CharField(max_length=150, db_column='nombre')
    telefono = models.CharField(max_length=20, db_column='telefono')
    activo = models.BooleanField(default=True, db_column='activo')

    class Meta:
        db_table = 'admin_centro'

    def __str__(self):
        return self.nombre
