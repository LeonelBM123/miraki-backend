from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import BitacoraAcceso, Rol
from .utils import get_client_ip, get_user_agent

Usuario = get_user_model()


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id_rol', 'nombre_rol', 'descripcion']


class UsuarioSerializer(serializers.ModelSerializer):
    nombre_rol = serializers.CharField(source='id_rol.nombre_rol', read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'public_id', 'correo', 'id_rol', 'nombre_rol', 'is_active', 'is_staff',
            'last_login',
            'fecha_ultimo_cambio_password', 'requiere_cambio_password',
            'fecha_creacion', 'fecha_modificacion',
        ]
        read_only_fields = ['public_id', 'last_login', 'fecha_creacion', 'fecha_modificacion']
        # id_usuario, intentos_fallidos, bloqueado_hasta are internal —
        # never exposed via API per django-security skill.


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

    max_failed_attempts = 5
    lockout_minutes = 15
    failure_message = 'Credenciales inválidas.'

    def _get_usuario(self, correo):
        if not correo:
            return None
        return Usuario.objects.filter(correo__iexact=correo).first()

    def _log_access(self, request, correo_intento, tipo_evento, usuario=None):
        BitacoraAcceso.objects.create(
            id_usuario=usuario,
            correo_intento=correo_intento,
            tipo_evento=tipo_evento,
            direccion_ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    def _mark_failure(self, usuario, request, correo_intento):
        if usuario is not None:
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= self.max_failed_attempts:
                usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=self.lockout_minutes)
            usuario.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])
        self._log_access(request, correo_intento, 'login_fallido', usuario=usuario)
        raise AuthenticationFailed(self.failure_message)

    def _mark_success(self, usuario, request, correo_intento):
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])
        self._log_access(request, correo_intento, 'login_exitoso', usuario=usuario)

    def validate(self, attrs):
        request = self.context.get('request')
        correo_intento = attrs.get(self.username_field, '')
        usuario = self._get_usuario(correo_intento)

        if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > timezone.now():
            self._log_access(request, correo_intento, 'login_fallido', usuario=usuario)
            raise AuthenticationFailed(self.failure_message)

        try:
            data = super().validate(attrs)
        except Exception:
            self._mark_failure(usuario, request, correo_intento)

        self._mark_success(self.user, request, correo_intento)
        return data
