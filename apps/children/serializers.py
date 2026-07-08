from django.utils import timezone
from rest_framework import serializers

from apps.institutions.models import CentroEducativo

from .models import Nino


class NinoCentroReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroEducativo
        fields = ['id_centro', 'nombre']
        read_only_fields = fields


class NinoCreateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nino
        fields = ['nombre', 'fecha_nacimiento', 'foto_url']

    def validate_fecha_nacimiento(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError('La fecha de nacimiento no puede ser futura.')
        return value


class NinoUpdateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nino
        fields = ['nombre', 'fecha_nacimiento', 'foto_url']
        extra_kwargs = {
            'nombre': {'required': False},
            'fecha_nacimiento': {'required': False},
            'foto_url': {'required': False},
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
