from django.contrib.gis.db import models as gis_models
from django.db import models

from apps.accounts.models import Tutor
from apps.common.models import AuditMixin
from apps.institutions.models import CentroEducativo


class ZonaSegura(AuditMixin):
    id_zona = models.AutoField(primary_key=True, db_column='id_zona')
    nombre = models.CharField(max_length=150, db_column='nombre')
    # PolygonField de GeoDjango almacena el polígono en PostGIS con índice GIST
    # geography=True permite cálculos de distancia en metros sobre la esfera
    poligono = gis_models.PolygonField(geography=True, srid=4326, db_column='poligono')
    activo = models.BooleanField(default=True, db_column='activo')

    # Una zona es personalizada (tutor) o institucional (centro), nunca ambas ni ninguna.
    # La validación de esta regla vive en el service, no en la base de datos.
    id_tutor_propietario = models.ForeignKey(
        Tutor,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column='id_tutor_propietario',
        related_name='zonas',
    )
    id_centro = models.ForeignKey(
        CentroEducativo,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column='id_centro',
        related_name='zonas',
    )

    class Meta:
        db_table = 'zona_segura'
        indexes = [
            models.Index(fields=['id_tutor_propietario'], name='ix_zona_tutor'),
            models.Index(fields=['id_centro'], name='ix_zona_centro'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(id_tutor_propietario__isnull=False, id_centro__isnull=True)
                    | models.Q(id_tutor_propietario__isnull=True, id_centro__isnull=False)
                ),
                name='ck_zona_propietario_exclusivo',
            )
        ]

    def __str__(self):
        return self.nombre
