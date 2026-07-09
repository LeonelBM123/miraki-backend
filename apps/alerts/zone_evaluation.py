import logging

from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.children.models import Nino
from apps.zones.models import NinoZonaSegura, ZonaSegura
from apps.zones.services import zona_vigente

from .models import Alerta, DispositivoToken, NinoZonaEstado, Posicion
from .services import send_push_notification as dispatch_fcm

logger = logging.getLogger(__name__)

SALIDA_DEDUP_MINUTES = 10
ENTRADA_DEDUP_MINUTES = 10


def evaluar_zona_nino(*, nino: Nino, posicion: Posicion):
    """
    Evalúa si el niño está dentro o fuera de cada una de sus zonas activas.
    Compara con el estado anterior para detectar transiciones:
      - dentro → fuera: crea alerta SALIDA_ZONA + push al tutor.
      - fuera → dentro: envía push al tutor (sin crear alerta persistente).
    Dedup evita notificaciones repetidas en ventanas cortas.
    """
    ahora = timezone.localtime()
    punto = Point(float(posicion.longitud), float(posicion.latitud), srid=4326)

    zonas_activas = list(
        NinoZonaSegura.objects.filter(
            id_nino=nino,
            activa=True,
            id_zona__activo=True,
        )
        .select_related('id_zona')
        .prefetch_related('id_zona__horarios')
    )

    if not zonas_activas:
        return {'evaluated': 0, 'exits': 0, 'entries': 0}

    exits = 0
    entries = 0

    for nz in zonas_activas:
        zona = nz.id_zona

        # Skip if the zone schedule says it's not active right now
        if not zona_vigente(zona, ahora):
            continue

        dentro_ahora = ZonaSegura.objects.filter(pk=zona.pk, poligono__covers=punto).exists()

        estado, _created = NinoZonaEstado.objects.get_or_create(
            id_nino=nino,
            id_zona=zona,
            defaults={'dentro': dentro_ahora},
        )

        if estado.dentro == dentro_ahora:
            # No change — skip
            continue

        if estado.dentro and not dentro_ahora:
            # Transition: inside → outside
            exits += _handle_exit(nino=nino, zona=zona, posicion=posicion)
        else:
            # Transition: outside → inside
            entries += _handle_entry(nino=nino, zona=zona, posicion=posicion)

        # Update state
        estado.dentro = dentro_ahora
        estado.save(update_fields=['dentro', 'fecha_actualizacion'])

    return {'evaluated': len(zonas_activas), 'exits': exits, 'entries': entries}


def _handle_exit(*, nino, zona, posicion):
    """Child left the zone: create alert + send push."""
    desde = timezone.now() - timezone.timedelta(minutes=SALIDA_DEDUP_MINUTES)
    if Alerta.objects.filter(
        id_nino=nino,
        id_zona=zona,
        tipo=Alerta.TipoAlerta.SALIDA_ZONA,
        fecha_alerta__gte=desde,
    ).exists():
        return 0  # dedup

    alerta = Alerta.objects.create(
        id_nino=nino,
        id_zona=zona,
        id_posicion=posicion,
        tipo=Alerta.TipoAlerta.SALIDA_ZONA,
    )
    _dispatch_push_for_alerta(alerta)
    return 1


def _handle_entry(*, nino, zona, posicion):
    """Child entered the zone: send push only (no persistent alert)."""
    desde = timezone.now() - timezone.timedelta(minutes=ENTRADA_DEDUP_MINUTES)
    if Alerta.objects.filter(
        id_nino=nino,
        id_zona=zona,
        tipo=Alerta.TipoAlerta.SALIDA_ZONA,
        fecha_alerta__gte=desde,
    ).exists():
        return 0  # was just outside recently — entry notification expected but dedup if too fast

    # Send an entry push without creating an alert
    _send_entry_push(nino=nino, zona=zona)
    return 1


def _dispatch_push_for_alerta(alerta):
    """Send FCM push for an alert. Runs inline since Celery worker is not available."""
    _send_push_inline(alerta)


def _send_push_inline(alerta):
    """Send FCM push synchronously (fallback when Celery is not running)."""
    try:
        tokens = DispositivoToken.objects.filter(
            id_usuario__tutor__ninos__id_nino=alerta.id_nino_id,
            activo=True,
        ).distinct()
        if tokens.exists():
            sent, failed = dispatch_fcm(alerta=alerta, tokens=tokens)
            logger.info('Push sent inline for alerta %s: %d ok, %d failed', alerta.id_alerta, sent, failed)
        else:
            logger.info('No active FCM tokens for nino %s, alerta %s', alerta.id_nino_id, alerta.id_alerta)
    except Exception:
        logger.exception('Inline push failed for alerta %s', alerta.id_alerta)


def _send_entry_push(*, nino, zona):
    """Send an 'entered safe zone' push notification to the tutor."""
    tokens = DispositivoToken.objects.filter(
        id_usuario__tutor__ninos__id_nino=nino.id_nino,
        activo=True,
    ).distinct()

    if not tokens.exists():
        logger.info('No FCM tokens for nino %s entry push', nino.id_nino)
        return

    from firebase_admin import messaging

    messages = []
    for token_obj in tokens:
        messages.append(
            messaging.Message(
                notification=messaging.Notification(
                    title='✅ Zona segura',
                    body=f'{nino.nombre} entró a {zona.nombre}.',
                ),
                data={
                    'id_nino': str(nino.id_nino),
                    'id_zona': str(zona.pk),
                    'tipo': 'entrada_zona',
                    'type': 'zone_entry',
                },
                token=token_obj.token,
            )
        )

    try:
        response = messaging.send_each(messages)
        success = getattr(response, 'success_count', len(messages))
        failure = getattr(response, 'failure_count', 0)
        logger.info('Entry push for nino %s zona %s: %d ok, %d failed', nino.id_nino, zona.pk, success, failure)
    except Exception:
        logger.exception('Entry push failed for nino %s zona %s', nino.id_nino, zona.pk)
