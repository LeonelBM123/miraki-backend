import json
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict

from .models import Bitacora

SENSITIVE_KEYS = {'password', 'password_hash', 'access', 'refresh', 'token'}


def _clean_mapping(value):
    if value is None:
        return None
    cleaned = {}
    for key, item in value.items():
        if key in SENSITIVE_KEYS:
            continue
        cleaned[key] = item
    return json.loads(json.dumps(cleaned, cls=DjangoJSONEncoder))


def serialize_instance(instance):
    if instance is None:
        return None
    data = model_to_dict(instance)
    for field in instance._meta.fields:
        value = getattr(instance, field.name)
        if field.is_relation and value is not None:
            data[field.name] = getattr(value, value._meta.pk.name)
        elif isinstance(value, Decimal):
            data[field.name] = str(value)
        else:
            data[field.name] = value
    return _clean_mapping(data)


def record_action(*, table, record_id, operation, actor=None, ip=None, before=None, after=None):
    return Bitacora.objects.create(
        tabla_afectada=table,
        id_registro=str(record_id),
        operacion=operation,
        datos_anteriores=_clean_mapping(before),
        datos_nuevos=_clean_mapping(after),
        id_usuario=actor if getattr(actor, 'is_authenticated', False) else None,
        direccion_ip=ip,
    )
