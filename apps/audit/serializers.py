from rest_framework import serializers

from .models import Bitacora


class BitacoraSerializer(serializers.ModelSerializer):
    usuario_correo = serializers.EmailField(source='id_usuario.correo', read_only=True)

    class Meta:
        model = Bitacora
        fields = [
            'id_bitacora', 'tabla_afectada', 'id_registro', 'operacion',
            'datos_anteriores', 'datos_nuevos', 'id_usuario', 'usuario_correo',
            'fecha_evento', 'direccion_ip',
        ]
        read_only_fields = fields
