from rest_framework import serializers

from apps.dispositivos.models import Dispositivo

from .models import Alerta, DispositivoToken


class AlertaReadSerializer(serializers.ModelSerializer):
    nombre_nino = serializers.CharField(source='id_nino.nombre', read_only=True)
    nombre_zona = serializers.CharField(source='id_zona.nombre', read_only=True, allow_null=True)
    latitud = serializers.DecimalField(
        source='id_posicion.latitud',
        max_digits=9,
        decimal_places=6,
        read_only=True,
        allow_null=True,
    )
    longitud = serializers.DecimalField(
        source='id_posicion.longitud',
        max_digits=9,
        decimal_places=6,
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Alerta
        fields = [
            'id_alerta',
            'id_nino',
            'nombre_nino',
            'id_zona',
            'nombre_zona',
            'id_posicion',
            'latitud',
            'longitud',
            'tipo',
            'fecha_alerta',
            'atendida',
            'fecha_atencion',
            'atendida_por',
        ]
        read_only_fields = fields


class AlertaMarkAttendedSerializer(serializers.Serializer):
    pass


class DispositivoTokenSerializer(serializers.ModelSerializer):
    id_dispositivo = serializers.PrimaryKeyRelatedField(
        queryset=Dispositivo.objects.all(),
        required=False,
        allow_null=True,
    )
    plataforma = serializers.CharField()

    class Meta:
        model = DispositivoToken
        fields = ['id', 'id_usuario', 'id_dispositivo', 'token', 'plataforma']
        read_only_fields = ['id', 'id_usuario']

    def validate_plataforma(self, value):
        plataforma = value.strip().lower()
        allowed = {choice for choice, _ in DispositivoToken.Plataforma.choices}
        if plataforma not in allowed:
            raise serializers.ValidationError('La plataforma debe ser android, ios o web.')
        return plataforma
