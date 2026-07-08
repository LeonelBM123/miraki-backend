from django.db import models

from apps.accounts.models import Tutor
from apps.common.models import AuditMixin
from apps.institutions.models import CentroEducativo


class Nino(AuditMixin):
    id_nino = models.AutoField(primary_key=True, db_column='id_nino')
    nombre = models.CharField(max_length=150, db_column='nombre')
    fecha_nacimiento = models.DateField(null=True, blank=True, db_column='fecha_nacimiento')
    foto_url = models.CharField(max_length=300, null=True, blank=True, db_column='foto_url')
    foto_public_id = models.CharField(max_length=255, null=True, blank=True, db_column='foto_public_id')
    id_tutor = models.ForeignKey(
        Tutor,
        on_delete=models.PROTECT,
        db_column='id_tutor',
        related_name='ninos',
    )
    centro = models.ForeignKey(
        CentroEducativo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_centro',
        related_name='ninos',
    )
    activo = models.BooleanField(default=True, db_column='activo')

    class Meta:
        db_table = 'nino'
        indexes = [
            models.Index(fields=['id_tutor'], name='ix_nino_tutor'),
            models.Index(fields=['centro'], name='ix_nino_centro'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
