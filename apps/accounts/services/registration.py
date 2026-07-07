from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import Rol, Tutor
from apps.accounts.utils import get_client_ip
from apps.audit.models import Bitacora
from apps.audit.services import record_action, serialize_instance
from apps.institutions.models import AdminCentro, CentroEducativo

Usuario = get_user_model()


def _get_role(nombre_rol):
    return Rol.objects.get(nombre_rol=nombre_rol)


@transaction.atomic
def register_account(*, data, request):
    tipo_cuenta = data['tipo_cuenta']
    ip = get_client_ip(request)

    if tipo_cuenta == 'tutor':
        role = _get_role('Tutor')
        usuario = Usuario.objects.create_user(
            correo=data['correo'],
            password=data['password'],
            id_rol=role,
        )
        tutor = Tutor.objects.create(
            id_usuario=usuario,
            nombre=data['nombre'],
            telefono=data['telefono'],
            creado_por=usuario,
            modificado_por=usuario,
        )
        record_action(
            table='usuario',
            record_id=usuario.pk,
            operation=Bitacora.Operacion.INSERT,
            actor=usuario,
            ip=ip,
            after=serialize_instance(usuario),
        )
        record_action(
            table='tutor',
            record_id=tutor.pk,
            operation=Bitacora.Operacion.INSERT,
            actor=usuario,
            ip=ip,
            after=serialize_instance(tutor),
        )
        return {'usuario': usuario, 'perfil': tutor, 'tipo_cuenta': tipo_cuenta}

    role = _get_role('AdminCentro')
    centro_data = data['centro']
    usuario = Usuario.objects.create_user(
        correo=data['correo'],
        password=data['password'],
        id_rol=role,
    )
    centro = CentroEducativo.objects.create(
        nombre=centro_data['nombre'],
        direccion=centro_data['direccion'],
        creado_por=usuario,
        modificado_por=usuario,
    )
    admin_centro = AdminCentro.objects.create(
        id_usuario=usuario,
        id_centro=centro,
        nombre=data['nombre'],
        telefono=data['telefono'],
        creado_por=usuario,
        modificado_por=usuario,
    )
    for table, instance in (
        ('usuario', usuario),
        ('centro_educativo', centro),
        ('admin_centro', admin_centro),
    ):
        record_action(
            table=table,
            record_id=instance.pk,
            operation=Bitacora.Operacion.INSERT,
            actor=usuario,
            ip=ip,
            after=serialize_instance(instance),
        )
    return {'usuario': usuario, 'perfil': admin_centro, 'tipo_cuenta': tipo_cuenta}
