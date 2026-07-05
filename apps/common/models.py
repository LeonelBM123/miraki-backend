from django.conf import settings
from django.db import models


class AuditMixin(models.Model):
    """Columnas de auditoría comunes a la mayoría de tablas del modelo de datos."""

    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    fecha_modificacion = models.DateTimeField(auto_now=True, db_column='fecha_modificacion')
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        db_column='creado_por',
    )
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        db_column='modificado_por',
    )

    class Meta:
        abstract = True
