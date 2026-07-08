from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Tutor
from apps.accounts.utils import get_client_ip
from apps.audit.models import Bitacora
from apps.audit.services import record_action, serialize_instance

from .models import Nino


def get_tutor_for_user(user):
    try:
        return user.tutor
    except (AttributeError, Tutor.DoesNotExist) as exc:
        raise PermissionDenied('El usuario autenticado no tiene perfil Tutor.') from exc


@transaction.atomic
def create_nino(*, user, data, request=None):
    tutor = get_tutor_for_user(user)
    nino = Nino.objects.create(
        id_tutor=tutor,
        nombre=data['nombre'],
        fecha_nacimiento=data.get('fecha_nacimiento'),
        foto_url=data.get('foto_url', ''),
        activo=True,
        creado_por=user,
        modificado_por=user,
    )
    record_action(
        table='nino',
        record_id=nino.pk,
        operation=Bitacora.Operacion.INSERT,
        actor=user,
        ip=get_client_ip(request),
        after=serialize_instance(nino),
    )
    return nino


@transaction.atomic
def update_nino(*, nino, user, data, request=None):
    locked = Nino.objects.select_for_update().get(pk=nino.pk)
    before = serialize_instance(locked)
    for field in ['nombre', 'fecha_nacimiento', 'foto_url']:
        if field in data:
            setattr(locked, field, data[field])
    locked.modificado_por = user
    locked.save(update_fields=['nombre', 'fecha_nacimiento', 'foto_url', 'modificado_por', 'fecha_modificacion'])
    record_action(
        table='nino',
        record_id=locked.pk,
        operation=Bitacora.Operacion.UPDATE,
        actor=user,
        ip=get_client_ip(request),
        before=before,
        after=serialize_instance(locked),
    )
    return locked


@transaction.atomic
def assign_nino_center(*, nino, centro, user, request=None):
    locked = Nino.objects.select_for_update().get(pk=nino.pk)
    old_centro_id = locked.centro_id
    new_centro_id = centro.pk

    if old_centro_id == new_centro_id:
        return locked

    locked.centro = centro
    locked.modificado_por = user
    locked.save(update_fields=['centro', 'modificado_por', 'fecha_modificacion'])
    record_action(
        table='nino',
        record_id=locked.pk,
        operation=Bitacora.Operacion.UPDATE,
        actor=user,
        ip=get_client_ip(request),
        before={'centro': old_centro_id},
        after={'centro': new_centro_id},
    )
    return locked


@transaction.atomic
def remove_nino_center(*, nino, user, request=None):
    locked = Nino.objects.select_for_update().get(pk=nino.pk)
    old_centro_id = locked.centro_id

    if old_centro_id is None:
        return locked

    locked.centro = None
    locked.modificado_por = user
    locked.save(update_fields=['centro', 'modificado_por', 'fecha_modificacion'])
    record_action(
        table='nino',
        record_id=locked.pk,
        operation=Bitacora.Operacion.UPDATE,
        actor=user,
        ip=get_client_ip(request),
        before={'centro': old_centro_id},
        after={'centro': None},
    )
    return locked


@transaction.atomic
def set_nino_active(*, nino, user, active, request=None):
    locked = Nino.objects.select_for_update().get(pk=nino.pk)
    before = serialize_instance(locked)
    locked.activo = active
    locked.modificado_por = user
    locked.save(update_fields=['activo', 'modificado_por', 'fecha_modificacion'])
    record_action(
        table='nino',
        record_id=locked.pk,
        operation=Bitacora.Operacion.UPDATE,
        actor=user,
        ip=get_client_ip(request),
        before=before,
        after=serialize_instance(locked),
    )
    return locked
