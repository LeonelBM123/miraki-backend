from rest_framework import serializers

from apps.children.models import Nino


class CrearCodigoSerializer(serializers.Serializer):
    id_nino = serializers.IntegerField()

    def validate_id_nino(self, value):
        request = self.context.get('request')
        if request is None or not getattr(request.user, 'is_authenticated', False):
            raise serializers.ValidationError('Autenticación requerida.')

        try:
            nino = Nino.objects.select_related('id_tutor__id_usuario').get(pk=value)
        except Nino.DoesNotExist as exc:
            raise serializers.ValidationError('El niño no existe.') from exc

        if nino.id_tutor.id_usuario_id != request.user.id_usuario:
            raise serializers.ValidationError('El niño no pertenece al tutor autenticado.')

        self._nino = nino
        return value

    def validate(self, attrs):
        attrs['nino'] = getattr(self, '_nino', None)
        return attrs


class VincularDispositivoSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=6)


class EstadoNinoSerializer(serializers.Serializer):
    id_nino = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    tutor_nombre = serializers.CharField(read_only=True)
    activo = serializers.BooleanField(read_only=True)
    ultima_posicion = serializers.JSONField(read_only=True, required=False, allow_null=True)
    zona_actual = serializers.JSONField(read_only=True, required=False, allow_null=True)
    alertas_recientes = serializers.IntegerField(read_only=True, required=False)
