from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import BitacoraAcceso
from apps.accounts.utils import get_client_ip, get_user_agent

Usuario = get_user_model()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _log_access(*, usuario=None, correo_intento='', tipo_evento, request=None):
    return BitacoraAcceso.objects.create(
        id_usuario=usuario,
        correo_intento=correo_intento,
        tipo_evento=tipo_evento,
        direccion_ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


def _blocked_error():
    return AuthenticationFailed(
        detail='La cuenta está temporalmente bloqueada. Intenta nuevamente en 15 minutos.',
        code='cuenta_bloqueada',
    )


@transaction.atomic
def login_with_lockout(*, correo, password, request=None):
    correo_intento = correo or ''
    usuario = (
        Usuario.objects.select_for_update()
        .select_related('id_rol')
        .filter(correo__iexact=correo_intento)
        .first()
    )

    if usuario is None:
        _log_access(correo_intento=correo_intento, tipo_evento='login_fallido', request=request)
        return {'error': 'invalid_credentials'}

    now = timezone.now()
    if usuario.bloqueado_hasta and usuario.bloqueado_hasta > now:
        _log_access(
            usuario=usuario,
            correo_intento=correo_intento,
            tipo_evento='login_fallido',
            request=request,
        )
        return {'error': 'blocked'}

    if not usuario.is_active or not usuario.check_password(password):
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= MAX_FAILED_ATTEMPTS:
            usuario.bloqueado_hasta = now + timedelta(minutes=LOCKOUT_MINUTES)
        usuario.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])
        _log_access(
            usuario=usuario,
            correo_intento=correo_intento,
            tipo_evento='login_fallido',
            request=request,
        )
        if usuario.bloqueado_hasta and usuario.bloqueado_hasta > now:
            return {'error': 'blocked'}
        return {'error': 'invalid_credentials'}

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.last_login = now
    usuario.save(update_fields=['intentos_fallidos', 'bloqueado_hasta', 'last_login'])
    _log_access(
        usuario=usuario,
        correo_intento=correo_intento,
        tipo_evento='login_exitoso',
        request=request,
    )

    refresh = RefreshToken.for_user(usuario)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'usuario': {
            'id_usuario': usuario.id_usuario,
            'correo': usuario.correo,
            'rol': usuario.id_rol.nombre_rol,
        },
    }


def authenticate_login(*, correo, password, request=None):
    result = login_with_lockout(correo=correo, password=password, request=request)
    if result.get('error') == 'blocked':
        raise _blocked_error()
    if result.get('error') == 'invalid_credentials':
        raise AuthenticationFailed('No se encontró una cuenta activa con las credenciales proporcionadas.')
    return result


@transaction.atomic
def record_logout(*, usuario, request=None):
    _log_access(
        usuario=usuario,
        correo_intento=usuario.correo,
        tipo_evento='logout',
        request=request,
    )
