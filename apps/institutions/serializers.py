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


class AdminCentroResponseSerializer(serializers.ModelSerializer):
    centro = CentroEducativoResponseSerializer(source='id_centro', read_only=True)

    class Meta:
        model = AdminCentro
        fields = ['id_admin_centro', 'nombre', 'telefono', 'activo', 'centro']
        read_only_fields = fields
