import logging

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Tutor
from apps.accounts.utils import get_client_ip
from apps.audit.models import Bitacora
from apps.audit.services import record_action, serialize_instance
from apps.common.services.cloudinary import delete_image, upload_image

from .models import Nino

logger = logging.getLogger(__name__)
NINO_PHOTO_FOLDER = 'miraki/ninos'


def get_tutor_for_user(user):
    try:
        return user.tutor
    except (AttributeError, Tutor.DoesNotExist) as exc:
        raise PermissionDenied('El usuario autenticado no tiene perfil Tutor.') from exc


def _serialize_nino_for_audit(nino):
    data = serialize_instance(nino)
    if data:
        data.pop('foto_public_id', None)
    return data


def _delete_uploaded_photo(public_id):
    if not public_id:
        return
    if not delete_image(public_id):
        logger.warning('No se pudo completar limpieza de foto en Cloudinary.')


def create_nino(*, user, data, request=None):
    tutor = get_tutor_for_user(user)
    foto = data.pop('foto', None)
    uploaded_photo = None

    if foto is not None:
        uploaded_photo = upload_image(foto, folder=NINO_PHOTO_FOLDER)

    try:
        with transaction.atomic():
            nino = Nino.objects.create(
                id_tutor=tutor,
                nombre=data['nombre'],
                fecha_nacimiento=data.get('fecha_nacimiento'),
                foto_url=uploaded_photo['secure_url'] if uploaded_photo else None,
                foto_public_id=uploaded_photo['public_id'] if uploaded_photo else None,
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
                after=_serialize_nino_for_audit(nino),
            )
            return nino
    except Exception:
        if uploaded_photo:
            _delete_uploaded_photo(uploaded_photo['public_id'])
        raise


def update_nino(*, nino, user, data, request=None):
    foto = data.pop('foto', None)
    uploaded_photo = None
    old_public_id = None

    if foto is not None:
        uploaded_photo = upload_image(foto, folder=NINO_PHOTO_FOLDER)

    try:
        with transaction.atomic():
            locked = Nino.objects.select_for_update().get(pk=nino.pk)
            before = _serialize_nino_for_audit(locked)
            old_public_id = locked.foto_public_id
            update_fields = ['modificado_por', 'fecha_modificacion']

            for field in ['nombre', 'fecha_nacimiento']:
                if field in data:
                    setattr(locked, field, data[field])
                    update_fields.append(field)

            if uploaded_photo:
                locked.foto_url = uploaded_photo['secure_url']
                locked.foto_public_id = uploaded_photo['public_id']
                update_fields.extend(['foto_url', 'foto_public_id'])

            locked.modificado_por = user
            locked.save(update_fields=update_fields)
            record_action(
                table='nino',
                record_id=locked.pk,
                operation=Bitacora.Operacion.UPDATE,
                actor=user,
                ip=get_client_ip(request),
                before=before,
                after=_serialize_nino_for_audit(locked),
            )
    except Exception:
        if uploaded_photo:
            _delete_uploaded_photo(uploaded_photo['public_id'])
        raise

    if uploaded_photo and old_public_id:
        _delete_uploaded_photo(old_public_id)

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
    before = _serialize_nino_for_audit(locked)
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
        after=_serialize_nino_for_audit(locked),
    )
    return locked


def remove_nino_photo(*, nino, user, request=None):
    with transaction.atomic():
        locked = Nino.objects.select_for_update().get(pk=nino.pk)
        old_public_id = locked.foto_public_id

        if not locked.foto_url and not old_public_id:
            return locked

        before = {'foto_url': locked.foto_url}
        locked.foto_url = None
        locked.foto_public_id = None
        locked.modificado_por = user
        locked.save(update_fields=['foto_url', 'foto_public_id', 'modificado_por', 'fecha_modificacion'])
        record_action(
            table='nino',
            record_id=locked.pk,
            operation=Bitacora.Operacion.UPDATE,
            actor=user,
            ip=get_client_ip(request),
            before=before,
            after={'foto_url': None},
        )

    _delete_uploaded_photo(old_public_id)
    return locked
