from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from apps.common.models import AuditMixin


class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True, db_column='id_rol')
    nombre_rol = models.CharField(max_length=50, unique=True, db_column='nombre_rol')
    descripcion = models.CharField(max_length=200, null=True, blank=True, db_column='descripcion')

    class Meta:
        db_table = 'rol'

    def __str__(self):
        return self.nombre_rol


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, correo, password, **extra_fields):
        if not correo:
            raise ValueError('El correo es obligatorio.')
        correo = self.normalize_email(correo)
        usuario = self.model(correo=correo, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, correo, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        if 'id_rol' not in extra_fields:
            rol_tutor, _ = Rol.objects.get_or_create(
                nombre_rol='Tutor',
                defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'},
            )
            extra_fields['id_rol'] = rol_tutor
        return self._create_user(correo, password, **extra_fields)

    def create_superuser(self, correo, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')
        if 'id_rol' not in extra_fields:
            rol_super_admin, _ = Rol.objects.get_or_create(
                nombre_rol='SuperAdmin',
                defaults={'descripcion': 'Administrador general del sistema'},
            )
            extra_fields['id_rol'] = rol_super_admin
        return self._create_user(correo, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin, AuditMixin):
    """
    AUTH_USER_MODEL del proyecto. No existe columna ``password_salt``: el
    hash de contraseñas de Django (PBKDF2) ya embebe el salt en ``password``.
    """

    id_usuario = models.AutoField(primary_key=True, db_column='id_usuario')
    correo = models.EmailField(max_length=150, unique=True, db_column='correo')
    password = models.CharField(max_length=256, db_column='password_hash')
    id_rol = models.ForeignKey(
        Rol, on_delete=models.PROTECT, db_column='id_rol', related_name='usuarios',
    )
    is_active = models.BooleanField(default=True, db_column='activo')
    is_staff = models.BooleanField(default=False, db_column='is_staff')
    last_login = models.DateTimeField(null=True, blank=True, db_column='ultimo_login')
    intentos_fallidos = models.PositiveIntegerField(default=0, db_column='intentos_fallidos')
    bloqueado_hasta = models.DateTimeField(null=True, blank=True, db_column='bloqueado_hasta')
    fecha_ultimo_cambio_password = models.DateTimeField(
        null=True, blank=True, db_column='fecha_ultimo_cambio_password',
    )
    requiere_cambio_password = models.BooleanField(default=False, db_column='requiere_cambio_password')

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'usuario'

    def __str__(self):
        return self.correo


class Tutor(AuditMixin):
    id_tutor = models.AutoField(primary_key=True, db_column='id_tutor')
    id_usuario = models.OneToOneField(
        Usuario,
        on_delete=models.PROTECT,
        db_column='id_usuario',
        related_name='tutor',
    )
    nombre = models.CharField(max_length=150, db_column='nombre')
    telefono = models.CharField(max_length=20, db_column='telefono')
    activo = models.BooleanField(default=True, db_column='activo')

    class Meta:
        db_table = 'tutor'

    def __str__(self):
        return self.nombre


class BitacoraAcceso(models.Model):
    TIPO_EVENTO_CHOICES = [
        ('login_exitoso', 'Login exitoso'),
        ('login_fallido', 'Login fallido'),
        ('logout', 'Logout'),
    ]

    id_bitacora_acceso = models.AutoField(primary_key=True, db_column='id_bitacora_acceso')
    id_usuario = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='id_usuario',
        related_name='accesos',
    )
    correo_intento = models.CharField(max_length=150, db_column='correo_intento')
    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES, db_column='tipo_evento')
    direccion_ip = models.GenericIPAddressField(null=True, blank=True, db_column='direccion_ip')
    user_agent = models.CharField(max_length=300, null=True, blank=True, db_column='user_agent')
    fecha_evento = models.DateTimeField(auto_now_add=True, db_column='fecha_evento')

    class Meta:
        db_table = 'bitacora_acceso'

    def __str__(self):
        return f'{self.correo_intento} - {self.tipo_evento}'
