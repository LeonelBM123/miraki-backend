from rest_framework import serializers

from apps.children.models import Nino

from .models import Dispositivo


class DispositivoReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispositivo
        fields = [
            'id_dispositivo',
            'imei',
            'sim_numero',
            'modelo',
            'estado',
            'id_nino',
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
            'creado_por',
            'modificado_por',
        ]
        read_only_fields = fields


class LinkDeviceSerializer(serializers.Serializer):
    imei = serializers.CharField(required=True, max_length=20)
    id_nino = serializers.IntegerField(required=True)

    def validate_imei(self, value):
        normalized = value.strip()
        if not normalized.isdigit() or len(normalized) != 15:
            raise serializers.ValidationError('El IMEI debe contener exactamente 15 dígitos numéricos.')
        return normalized

    def validate_id_nino(self, value):
        if value <= 0:
            raise serializers.ValidationError('El identificador del niño debe ser válido.')
        if not Nino.objects.filter(pk=value).exists():
            raise serializers.ValidationError('El niño no existe.')
        return value
