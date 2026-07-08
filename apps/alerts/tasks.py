from celery import shared_task
from django.conf import settings
from django.contrib.gis.geos import Point
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from apps.children.models import Nino
from apps.zones.models import NinoZonaSegura, ZonaSegura

from .models import Alerta, DispositivoToken, Posicion
from .services import send_push_notification as dispatch_push_notification

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def evaluar_zonas(self):
    """
    Celery beat task: evaluate each child's latest position against their linked zones.
    Creates an alert if the child is outside ALL active linked zones.
    """
    latest_position = Posicion.objects.filter(
        id_dispositivo__id_nino_id=OuterRef('pk'),
    ).order_by('-fecha_posicion', '-id_posicion')

    children = (
        Nino.objects.filter(
            activo=True,
            dispositivo__posiciones__isnull=False,
            zonas_asociadas__activa=True,
            zonas_asociadas__id_zona__activo=True,
        )
        .annotate(
            latest_pos_id=Subquery(latest_position.values('id_posicion')[:1]),
            latest_latitud=Subquery(latest_position.values('latitud')[:1]),
            latest_longitud=Subquery(latest_position.values('longitud')[:1]),
        )
        .values('id_nino', 'latest_pos_id', 'latest_latitud', 'latest_longitud')
        .distinct()
    )

    alerts_created = 0
    ten_minutes_ago = timezone.now() - timezone.timedelta(minutes=10)
    dispatch_push = not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)

    for child in children:
        zonas = list(
            NinoZonaSegura.objects.filter(
                id_nino_id=child['id_nino'],
                activa=True,
                id_zona__activo=True,
            ).select_related('id_zona')
        )
        if not zonas:
            continue

        punto = Point(float(child['latest_longitud']), float(child['latest_latitud']), srid=4326)

        for nz in zonas:
            zona = nz.id_zona

            # Skip if point is inside this zone
            if ZonaSegura.objects.filter(pk=zona.pk, poligono__covers=punto).exists():
                continue

            # Dedup: child + zone + tipo in last 10 min
            if Alerta.objects.filter(
                id_nino_id=child['id_nino'],
                id_zona_id=zona.pk,
                tipo=Alerta.TipoAlerta.SALIDA_ZONA,
                fecha_alerta__gte=ten_minutes_ago,
            ).exists():
                continue

            alerta = Alerta.objects.create(
                id_nino_id=child['id_nino'],
                id_zona_id=zona.pk,
                id_posicion_id=child['latest_pos_id'],
                tipo=Alerta.TipoAlerta.SALIDA_ZONA,
            )
            alerts_created += 1

            if dispatch_push:
                tokens = DispositivoToken.objects.filter(
                    id_usuario__tutor__ninos__id_nino=child['id_nino'],
                    activo=True,
                ).distinct()
                if tokens.exists():
                    send_push_notification.delay(alerta.id_alerta)

    return f'{alerts_created} alerts created'


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_push_notification(self, alerta_id):
    """Send FCM push for an alert. Called by evaluar_zonas or manually."""
    try:
        alerta = Alerta.objects.select_related('id_nino', 'id_zona').get(pk=alerta_id)
    except Alerta.DoesNotExist:
        return 'alert not found'

    tokens = DispositivoToken.objects.filter(
        id_usuario__tutor__ninos__id_nino=alerta.id_nino_id,
        activo=True,
    ).distinct()

    success, failure = dispatch_push_notification(alerta=alerta, tokens=tokens)
    return f'{success} sent, {failure} failed'
