from django.contrib.auth import get_user_model
from django.db import models

from apps.children.models import Nino
from apps.common.models import AuditMixin

Usuario = get_user_model()


class CodigoPareo(AuditMixin):
    id_codigo_pareo = models.AutoField(primary_key=True, db_column='id_codigo_pareo')
    codigo = models.CharField(max_length=6, unique=True, db_column='codigo')
    id_nino = models.ForeignKey(Nino, on_delete=models.CASCADE, db_column='id_nino', related_name='codigos_pareo')
    id_tutor = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_tutor', related_name='codigos_pareo')
    creado_en = models.DateTimeField(auto_now_add=True, db_column='creado_en')
    expira_en = models.DateTimeField(db_column='expira_en')
    usado = models.BooleanField(default=False, db_column='usado')

    class Meta:
        db_table = 'codigo_pareo'
        indexes = [
            models.Index(fields=['codigo'], name='ix_codigo_pareo_codigo'),
            models.Index(fields=['id_nino', 'usado'], name='ix_codigo_pareo_nino_usado'),
        ]
