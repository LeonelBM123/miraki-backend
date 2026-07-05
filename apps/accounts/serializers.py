from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import BitacoraAcceso, Rol
from .utils import get_client_ip, get_user_agent

Usuario = get_user_model()


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id_rol', 'nombre_rol', 'descripcion']


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            'id_usuario', 'correo', 'id_rol', 'is_active', 'is_staff',
            'last_login', 'intentos_fallidos', 'bloqueado_hasta',
            'fecha_ultimo_cambio_password', 'requiere_cambio_password',
            'fecha_creacion', 'fecha_modificacion',
        ]
        read_only_fields = ['id_usuario', 'last_login', 'fecha_creacion', 'fecha_modificacion']


class BitacoraAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BitacoraAcceso
        fields = '__all__'
        read_only_fields = [f.name for f in BitacoraAcceso._meta.fields]


class RegisterSerializer(serializers.Serializer):
    """
    Registro de un Usuario nuevo (rol 'Tutor' por defecto).

    # TODO: cuando exista apps.tutores, crear aquí también el Tutor asociado
    # (nombre/telefono) en la misma transacción, tal como pide el prompt original.
    """

    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_correo(self, value):
        if Usuario.objects.filter(correo__iexact=value).exists():
            raise serializers.ValidationError('Ya existe un usuario con este correo.')
        return value

    def create(self, validated_data):
        return Usuario.objects.create_user(
            correo=validated_data['correo'],
            password=validated_data['password'],
        )


class ChangePasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_password_actual(self, value):
        usuario = self.context['request'].user
        if not usuario.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value

    def save(self, **kwargs):
        usuario = self.context['request'].user
        usuario.set_password(self.validated_data['password_nuevo'])
        usuario.requiere_cambio_password = False
        usuario.fecha_ultimo_cambio_password = timezone.now()
        usuario.save(update_fields=['password', 'requiere_cambio_password', 'fecha_ultimo_cambio_password'])
        return usuario


class BitacoraTokenObtainPairSerializer(TokenObtainPairSerializer):
    """TokenObtainPairSerializer que registra cada intento en BitacoraAcceso."""

    def validate(self, attrs):
        request = self.context.get('request')
        correo_intento = attrs.get(self.username_field, '')
        try:
            data = super().validate(attrs)
        except Exception:
            BitacoraAcceso.objects.create(
                correo_intento=correo_intento,
                tipo_evento='login_fallido',
                direccion_ip=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            raise

        BitacoraAcceso.objects.create(
            id_usuario=self.user,
            correo_intento=correo_intento,
            tipo_evento='login_exitoso',
            direccion_ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return data
