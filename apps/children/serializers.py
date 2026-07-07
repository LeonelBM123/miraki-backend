from django.utils import timezone
from rest_framework import serializers

from .models import Nino


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
    class Meta:
        model = Nino
        fields = [
            'id_nino', 'nombre', 'fecha_nacimiento', 'foto_url',
            'activo', 'fecha_creacion', 'fecha_modificacion',
        ]
        read_only_fields = fields
