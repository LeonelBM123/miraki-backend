from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Tutor
from apps.accounts.utils import get_client_ip
from apps.audit.models import Bitacora
from apps.audit.services import record_action, serialize_instance

from .models import ZonaSegura


def get_tutor_for_user(user):
    try:
        return user.tutor
    except (AttributeError, Tutor.DoesNotExist) as exc:
        raise PermissionDenied('El usuario autenticado no tiene perfil Tutor.') from exc


@transaction.atomic
def create_zona(*, user, data, request=None):
    tutor = get_tutor_for_user(user)
    zona = ZonaSegura.objects.create(
        nombre=data['nombre'],
        poligono=data['poligono'],
        activo=True,
        id_tutor_propietario=tutor,
        id_centro=None,
        creado_por=user,
        modificado_por=user,
    )
    record_action(
        table='zona_segura',
        record_id=zona.pk,
        operation=Bitacora.Operacion.INSERT,
        actor=user,
        ip=get_client_ip(request),
        after=serialize_instance(zona),
    )
    return zona


@transaction.atomic
def update_zona(*, zona, user, data, request=None):
    locked = ZonaSegura.objects.select_for_update().get(pk=zona.pk)
    before = serialize_instance(locked)

    for field in ['nombre', 'poligono']:
        if field in data:
            setattr(locked, field, data[field])

    locked.modificado_por = user
    locked.save(update_fields=['nombre', 'poligono', 'modificado_por', 'fecha_modificacion'])

    record_action(
        table='zona_segura',
        record_id=locked.pk,
        operation=Bitacora.Operacion.UPDATE,
        actor=user,
        ip=get_client_ip(request),
        before=before,
        after=serialize_instance(locked),
    )
    return locked


@transaction.atomic
def set_zona_active(*, zona, user, active, request=None):
    locked = ZonaSegura.objects.select_for_update().get(pk=zona.pk)
    before = serialize_instance(locked)

    locked.activo = active
    locked.modificado_por = user
    locked.save(update_fields=['activo', 'modificado_por', 'fecha_modificacion'])

    record_action(
        table='zona_segura',
        record_id=locked.pk,
        operation=Bitacora.Operacion.UPDATE,
        actor=user,
        ip=get_client_ip(request),
        before=before,
        after=serialize_instance(locked),
    )
    return locked
