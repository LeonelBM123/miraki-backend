from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Tutor
from apps.accounts.utils import get_client_ip
from apps.audit.models import Bitacora
from apps.audit.services import record_action, serialize_instance

from .models import ZonaSegura, HorarioZona, NinoZonaSegura


def get_owner_for_user(user):
    role_name = getattr(getattr(user, 'id_rol', None), 'nombre_rol', None)
    if role_name == 'AdminCentro':
        try:
            return None, user.admin_centro.id_centro
        except (AttributeError, Exception) as exc:
            raise PermissionDenied('El usuario autenticado no tiene perfil AdminCentro o no está asignado a un centro.') from exc
    try:
        return user.tutor, None
    except (AttributeError, Tutor.DoesNotExist) as exc:
        raise PermissionDenied('El usuario autenticado no tiene perfil Tutor ni AdminCentro.') from exc


def get_tutor_for_user(user):
    try:
        return user.tutor
    except (AttributeError, Tutor.DoesNotExist) as exc:
        raise PermissionDenied('El usuario autenticado no tiene perfil Tutor.') from exc


@transaction.atomic
def create_zona(*, user, data, request=None):
    tutor, centro = get_owner_for_user(user)
    zona = ZonaSegura.objects.create(
        nombre=data['nombre'],
        poligono=data['poligono'],
        activo=True,
        id_tutor_propietario=tutor,
        id_centro=centro,
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


@transaction.atomic
def sync_horarios_zona(*, zona, user, horarios_data, request=None):
    for old_h in HorarioZona.objects.filter(id_zona=zona):
        before = serialize_instance(old_h)
        old_pk = old_h.pk
        old_h.delete()
        record_action(
            table='horario_zona',
            record_id=old_pk,
            operation=Bitacora.Operacion.DELETE,
            actor=user,
            ip=get_client_ip(request),
            before=before,
        )

    nuevos_horarios = []
    for item in horarios_data:
        h = HorarioZona.objects.create(
            id_zona=zona,
            dia_semana=item['dia_semana'],
            hora_inicio=item['hora_inicio'],
            hora_fin=item['hora_fin'],
            activo=item.get('activo', True),
            creado_por=user,
            modificado_por=user,
        )
        record_action(
            table='horario_zona',
            record_id=h.pk,
            operation=Bitacora.Operacion.INSERT,
            actor=user,
            ip=get_client_ip(request),
            after=serialize_instance(h),
        )
        nuevos_horarios.append(h)
    return nuevos_horarios


def get_nino_for_user(user, id_nino):
    from apps.children.models import Nino
    role_name = getattr(getattr(user, 'id_rol', None), 'nombre_rol', None)
    if role_name == 'AdminCentro':
        try:
            admin_centro = user.admin_centro
            return Nino.objects.get(pk=id_nino, centro=admin_centro.id_centro)
        except (AttributeError, Nino.DoesNotExist) as exc:
            raise PermissionDenied('El niño especificado no existe o no pertenece a tu centro educativo.') from exc
    tutor = get_tutor_for_user(user)
    try:
        return Nino.objects.get(pk=id_nino, id_tutor=tutor)
    except Nino.DoesNotExist as exc:
        raise PermissionDenied('El niño especificado no existe o no pertenece a tu cuenta.') from exc


@transaction.atomic
def vincular_nino_zona(*, zona, id_nino, user, request=None):
    nino = get_nino_for_user(user, id_nino)

    asoc, created = NinoZonaSegura.objects.get_or_create(
        id_nino=nino,
        id_zona=zona,
        defaults={
            'activa': True,
            'creado_por': user,
            'modificado_por': user,
        }
    )
    if not created and not asoc.activa:
        before = serialize_instance(asoc)
        asoc.activa = True
        asoc.modificado_por = user
        asoc.save(update_fields=['activa', 'modificado_por', 'fecha_modificacion'])
        record_action(
            table='nino_zona_segura',
            record_id=asoc.pk,
            operation=Bitacora.Operacion.UPDATE,
            actor=user,
            ip=get_client_ip(request),
            before=before,
            after=serialize_instance(asoc),
        )
    elif created:
        record_action(
            table='nino_zona_segura',
            record_id=asoc.pk,
            operation=Bitacora.Operacion.INSERT,
            actor=user,
            ip=get_client_ip(request),
            after=serialize_instance(asoc),
        )
    return asoc


@transaction.atomic
def desactivar_nino_zona(*, zona, id_nino, user, request=None):
    nino = get_nino_for_user(user, id_nino)

    try:
        asoc = NinoZonaSegura.objects.get(id_nino=nino, id_zona=zona)
    except NinoZonaSegura.DoesNotExist as exc:
        raise PermissionDenied('El niño no está vinculado a esta zona.') from exc

    if asoc.activa:
        before = serialize_instance(asoc)
        asoc.activa = False
        asoc.modificado_por = user
        asoc.save(update_fields=['activa', 'modificado_por', 'fecha_modificacion'])
        record_action(
            table='nino_zona_segura',
            record_id=asoc.pk,
            operation=Bitacora.Operacion.UPDATE,
            actor=user,
            ip=get_client_ip(request),
            before=before,
            after=serialize_instance(asoc),
        )
    return asoc
