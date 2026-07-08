from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.institutions.models import CentroEducativo

from .models import Nino

ALLOWED_PHOTO_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_PHOTO_SIZE = 5 * 1024 * 1024


@extend_schema_field(OpenApiTypes.BINARY)
class NinoPhotoField(serializers.ImageField):
    def to_internal_value(self, data):
        if getattr(data, 'size', 0) == 0:
            raise serializers.ValidationError('La foto no puede estar vacia.')
        if data.size > MAX_PHOTO_SIZE:
            raise serializers.ValidationError('La foto no puede superar 5 MB.')
        content_type = getattr(data, 'content_type', None)
        if content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
            raise serializers.ValidationError('La foto debe ser JPEG, PNG o WEBP.')
        return super().to_internal_value(data)


class NinoCentroReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroEducativo
        fields = ['id_centro', 'nombre']
        read_only_fields = fields


class NinoCreateRequestSerializer(serializers.ModelSerializer):
    foto = NinoPhotoField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Nino
        fields = ['nombre', 'fecha_nacimiento', 'foto']

    def validate_fecha_nacimiento(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError('La fecha de nacimiento no puede ser futura.')
        return value


class NinoUpdateRequestSerializer(serializers.ModelSerializer):
    foto = NinoPhotoField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Nino
        fields = ['nombre', 'fecha_nacimiento', 'foto']
        extra_kwargs = {
            'nombre': {'required': False},
            'fecha_nacimiento': {'required': False},
        }

    def validate_fecha_nacimiento(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError('La fecha de nacimiento no puede ser futura.')
        return value


class NinoReadSerializer(serializers.ModelSerializer):
    centro = NinoCentroReadSerializer(read_only=True)

    class Meta:
        model = Nino
        fields = [
            'id_nino', 'nombre', 'fecha_nacimiento', 'foto_url',
            'activo', 'centro', 'fecha_creacion', 'fecha_modificacion',
        ]
        read_only_fields = fields


class AssignCenterSerializer(serializers.Serializer):
    centro_id = serializers.IntegerField(required=True)

    def validate_centro_id(self, value):
        try:
            return CentroEducativo.objects.get(pk=value)
        except CentroEducativo.DoesNotExist as exc:
            raise serializers.ValidationError('El centro educativo especificado no existe.') from exc
