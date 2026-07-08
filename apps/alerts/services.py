import logging
import sys
from types import ModuleType, SimpleNamespace

from django.db import transaction
from django.utils import timezone

from apps.accounts.utils import get_client_ip

from .models import Alerta

logger = logging.getLogger(__name__)

try:
    import firebase_admin  # type: ignore
    from firebase_admin import messaging  # type: ignore
except ImportError:  # pragma: no cover - exercised in environments without firebase-admin
    firebase_admin = ModuleType('firebase_admin')
    messaging = ModuleType('firebase_admin.messaging')

    class FirebaseError(Exception):
        pass

    def _message_factory(*, notification, data, token=None, topic=None):
        return SimpleNamespace(notification=notification, data=data, token=token, topic=topic)

    def _notification_factory(*, title, body):
        return SimpleNamespace(title=title, body=body)

    def _send_each(messages, dry_run=False, app=None):
        raise FirebaseError('firebase_admin not installed')

    messaging.Message = _message_factory
    messaging.Notification = _notification_factory
    messaging.send_each = _send_each
    firebase_admin.messaging = messaging
    firebase_admin.FirebaseError = FirebaseError
    sys.modules.setdefault('firebase_admin', firebase_admin)
    sys.modules.setdefault('firebase_admin.messaging', messaging)
    exceptions_module = ModuleType('firebase_admin.exceptions')
    exceptions_module.FirebaseError = FirebaseError
    firebase_admin.exceptions = exceptions_module
    sys.modules.setdefault('firebase_admin.exceptions', exceptions_module)


@transaction.atomic
def atender_alerta(*, alerta, user, request=None):
    alerta = Alerta.objects.select_for_update().get(pk=alerta.pk)
    alerta.atendida = True
    alerta.fecha_atencion = timezone.now()
    alerta.atendida_por = user
    alerta.modificado_por = user
    alerta.save(update_fields=['atendida', 'fecha_atencion', 'atendida_por', 'modificado_por'])

    try:
        from apps.audit.models import Bitacora
        from apps.audit.services import record_action, serialize_instance

        record_action(
            table='alerta',
            record_id=alerta.pk,
            operation=Bitacora.Operacion.UPDATE,
            actor=user,
            ip=get_client_ip(request),
            after=serialize_instance(alerta),
        )
    except ImportError:
        pass

    return alerta


def send_push_notification(*, alerta, tokens):
    """Send FCM push notification for an alert to a list of device tokens."""
    token_list = list(tokens)
    if not token_list:
        return 0, 0

    messages = []
    body = f'{alerta.id_nino.nombre} salió de {alerta.id_zona.nombre if alerta.id_zona else "una zona segura"}'
    for token_obj in token_list:
        messages.append(
            messaging.Message(
                notification=messaging.Notification(
                    title='🚨 Alerta de zona',
                    body=body,
                ),
                data={
                    'alerta_id': str(alerta.id_alerta),
                    'id_nino': str(alerta.id_nino_id),
                    'tipo': alerta.tipo,
                    'type': 'alerta',
                },
                token=token_obj.token,
            )
        )

    try:
        response = messaging.send_each(messages)
    except Exception:
        logger.exception('FCM send failed for alerta %s', alerta.id_alerta)
        return 0, len(token_list)

    return getattr(response, 'success_count', len(token_list)), getattr(response, 'failure_count', 0)
