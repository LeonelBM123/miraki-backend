from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import Tutor
from apps.accounts.utils import get_client_ip
from apps.audit.models import Bitacora
from apps.audit.services import record_action, serialize_instance
from apps.children.models import Nino

from .models import Dispositivo


def get_tutor_for_user(user):
    try:
        return user.tutor
    except (AttributeError, Tutor.DoesNotExist) as exc:
        raise PermissionDenied('El usuario autenticado no tiene perfil Tutor.') from exc


def get_device_status(device):
    estado = (device.estado or '').strip().lower()
    if not device.activo:
        estado_general = 'Inactivo'
    elif estado in {'activo', 'vinculado'}:
        estado_general = 'Vinculado'
    elif estado:
        estado_general = estado.capitalize()
    else:
        estado_general = 'Desconocido'

    return {
        'estado_general': estado_general,
        'nino': {
            'id_nino': device.id_nino_id,
            'nombre': device.id_nino.nombre,
        },
        'vinculado': device.id_nino_id is not None,
    }


@transaction.atomic
def link_device(imei, id_nino, user, request):
    get_tutor_for_user(user)
    child = (
        Nino.objects.select_for_update()
        .select_related('id_tutor', 'id_tutor__id_usuario')
        .filter(pk=id_nino, id_tutor__id_usuario=user)
        .first()
    )
    if child is None:
        raise ValidationError('El niño no existe o no pertenece al tutor autenticado.')

    if hasattr(child, 'dispositivo'):
        raise ValidationError('Este niño ya tiene un dispositivo vinculado.')

    if Dispositivo.objects.filter(imei=imei).exists():
        raise ValidationError('Este IMEI ya está vinculado a otro dispositivo.')

    try:
        device = Dispositivo.objects.create(
            imei=imei,
            id_nino=child,
            estado='vinculado',
            activo=True,
            creado_por=user,
            modificado_por=user,
        )
    except IntegrityError as exc:
        raise ValidationError('No pudimos vincular el dispositivo. Revisá los datos e intentá nuevamente.') from exc

    record_action(
        table='dispositivo',
        record_id=device.pk,
        operation=Bitacora.Operacion.INSERT,
        actor=user,
        ip=get_client_ip(request),
        after=serialize_instance(device),
    )
    return device
