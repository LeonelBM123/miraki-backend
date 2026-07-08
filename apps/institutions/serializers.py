from rest_framework import serializers

from .models import AdminCentro, CentroEducativo


class CentroEducativoResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroEducativo
        fields = ['id_centro', 'nombre', 'direccion', 'activo']
        read_only_fields = fields


class CentroEducativoSelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroEducativo
        fields = ['id_centro', 'nombre', 'direccion']
        read_only_fields = fields


class MyCentroEducativoSerializer(serializers.ModelSerializer):
    """Ver/editar el centro propio del AdminCentro (CU-07). Sólo nombre y dirección."""

    class Meta:
        model = CentroEducativo
        fields = ['id_centro', 'nombre', 'direccion', 'activo']
        read_only_fields = ['id_centro', 'activo']

    def validate_nombre(self, value):
        if not value.strip():
            raise serializers.ValidationError('El nombre no puede estar vacío.')
        return value.strip()


class AdminCentroResponseSerializer(serializers.ModelSerializer):
    centro = CentroEducativoResponseSerializer(source='id_centro', read_only=True)

    class Meta:
        model = AdminCentro
        fields = ['id_admin_centro', 'nombre', 'telefono', 'activo', 'centro']
        read_only_fields = fields
