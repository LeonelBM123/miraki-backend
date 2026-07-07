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


class HorarioZona(AuditMixin):
    id_horario = models.AutoField(primary_key=True, db_column='id_horario')
    id_zona = models.ForeignKey(
        ZonaSegura,
        on_delete=models.CASCADE,
        db_column='id_zona',
        related_name='horarios',
    )
    dia_semana = models.SmallIntegerField(db_column='dia_semana')  # 1=Lunes ... 7=Domingo
    hora_inicio = models.TimeField(db_column='hora_inicio')
    hora_fin = models.TimeField(db_column='hora_fin')
    activo = models.BooleanField(default=True, db_column='activo')

    class Meta:
        db_table = 'horario_zona'
        indexes = [
            models.Index(fields=['id_zona', 'dia_semana'], name='ix_horario_zona'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(dia_semana__gte=1, dia_semana__lte=7),
                name='ck_horario_dia',
            ),
            models.CheckConstraint(
                condition=models.Q(hora_inicio__lt=models.F('hora_fin')),
                name='ck_horario_horas',
            ),
        ]

    def __str__(self):
        return f"{self.id_zona.nombre} - Día {self.dia_semana} ({self.hora_inicio}-{self.hora_fin})"


class NinoZonaSegura(AuditMixin):
    id = models.AutoField(primary_key=True, db_column='id')
    id_nino = models.ForeignKey(
        'children.Nino',
        on_delete=models.CASCADE,
        db_column='id_nino',
        related_name='zonas_asociadas',
    )
    id_zona = models.ForeignKey(
        ZonaSegura,
        on_delete=models.CASCADE,
        db_column='id_zona',
        related_name='ninos_asociados',
    )
    activa = models.BooleanField(default=True, db_column='activa')

    class Meta:
        db_table = 'nino_zona_segura'
        constraints = [
            models.UniqueConstraint(
                fields=['id_nino', 'id_zona'],
                name='uq_nino_zona_segura',
            )
        ]

    def __str__(self):
        return f"Niño #{self.id_nino_id} <-> Zona #{self.id_zona_id} (Activa: {self.activa})"
