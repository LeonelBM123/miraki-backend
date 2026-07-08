import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import AccessToken

from apps.children.models import Nino

from .models import CodigoPareo

CODIGO_LENGTH = 6
CODIGO_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
PAIRING_TOKEN_LIFETIME = timedelta(days=7)


def generar_codigo() -> str:
    return ''.join(secrets.choice(CODIGO_ALPHABET) for _ in range(CODIGO_LENGTH))


def generar_token_pareo(nino: Nino) -> str:
    token = AccessToken()
    token['nino_id'] = nino.id_nino
    token['tutor_id'] = nino.id_tutor.id_usuario_id
    token['scope'] = 'kid_device'
    token.set_exp(lifetime=PAIRING_TOKEN_LIFETIME)
    return str(token)


@transaction.atomic
def vincular_dispositivo(codigo: str) -> dict:
    now = timezone.now()
    try:
        codigo_pareo = (
            CodigoPareo.objects.select_for_update()
            .select_related('id_nino', 'id_nino__id_tutor')
            .get(codigo=codigo, usado=False, expira_en__gt=now)
        )
    except CodigoPareo.DoesNotExist as exc:
        raise ValidationError({'codigo': 'Código inválido, usado o expirado.'}) from exc

    codigo_pareo.usado = True
    codigo_pareo.save(update_fields=['usado'])

    nino = codigo_pareo.id_nino
    return {
        'token': generar_token_pareo(nino),
        'id_nino': nino.id_nino,
        'nombre': nino.nombre,
        'tutor_nombre': nino.id_tutor.nombre,
    }
