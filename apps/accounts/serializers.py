from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.institutions.serializers import AdminCentroResponseSerializer

from .models import BitacoraAcceso, Rol, Tutor
from .services.auth import authenticate_login

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


class UsuarioAuthResponseSerializer(serializers.ModelSerializer):
    rol = serializers.CharField(source='id_rol.nombre_rol', read_only=True)

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'correo', 'rol']
        read_only_fields = fields


class LoginResponseSerializer(serializers.Serializer):
    usuario = UsuarioAuthResponseSerializer(read_only=True)


class TutorResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tutor
        fields = ['id_tutor', 'nombre', 'telefono', 'activo']
        read_only_fields = fields


class BitacoraAccesoSerializer(serializers.ModelSerializer):
    class Meta:
        model = BitacoraAcceso
        fields = '__all__'
        read_only_fields = [f.name for f in BitacoraAcceso._meta.fields]


class CentroRegistroSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    direccion = serializers.CharField()


class RegisterAccountRequestSerializer(serializers.Serializer):
    TIPO_TUTOR = 'tutor'
    TIPO_ADMIN_CENTRO = 'admin_centro'
    TIPO_CUENTA_CHOICES = [
        (TIPO_TUTOR, 'Tutor'),
        (TIPO_ADMIN_CENTRO, 'AdminCentro'),
    ]

    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirmar_password = serializers.CharField(write_only=True)
    tipo_cuenta = serializers.ChoiceField(choices=TIPO_CUENTA_CHOICES)
    nombre = serializers.CharField(max_length=150)
    telefono = serializers.CharField(max_length=20)
    centro = CentroRegistroSerializer(required=False)

    def validate_correo(self, value):
        if Usuario.objects.filter(correo__iexact=value).exists():
            raise serializers.ValidationError('Ya existe un usuario con este correo.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirmar_password']:
            raise serializers.ValidationError({'confirmar_password': 'Las contraseñas no coinciden.'})
        if attrs['tipo_cuenta'] == self.TIPO_ADMIN_CENTRO and not attrs.get('centro'):
            raise serializers.ValidationError({'centro': 'Los datos del centro son obligatorios.'})
        return attrs


class RegisterResponseSerializer(serializers.Serializer):
    usuario = UsuarioAuthResponseSerializer(read_only=True)
    tipo_cuenta = serializers.CharField(read_only=True)
    perfil = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DictField)
    def get_perfil(self, obj):
        perfil = obj['perfil']
        if obj['tipo_cuenta'] == RegisterAccountRequestSerializer.TIPO_TUTOR:
            return TutorResponseSerializer(perfil).data
        return AdminCentroResponseSerializer(perfil).data


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
    """TokenObtainPairSerializer compatible con SimpleJWT y bloqueo de cuenta."""

    def validate(self, attrs):
        request = self.context.get('request')
        return authenticate_login(
            correo=attrs.get(self.username_field, ''),
            password=attrs.get('password', ''),
            request=request,
        )


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False)


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


RegisterSerializer = RegisterAccountRequestSerializer
