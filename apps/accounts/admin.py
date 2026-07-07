from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import BitacoraAcceso, Rol, Tutor, Usuario


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ['id_rol', 'nombre_rol', 'descripcion']
    search_fields = ['nombre_rol']


@admin.register(Usuario)
class UsuarioAdmin(DjangoUserAdmin):
    ordering = ['correo']
    list_display = ['correo', 'id_rol', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'id_rol']
    search_fields = ['correo']
    fieldsets = (
        (None, {'fields': ('correo', 'password')}),
        ('Datos de negocio', {'fields': ('id_rol', 'requiere_cambio_password')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('correo', 'id_rol', 'password1', 'password2'),
        }),
    )
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(BitacoraAcceso)
class BitacoraAccesoAdmin(admin.ModelAdmin):
    list_display = ['id_bitacora_acceso', 'correo_intento', 'tipo_evento', 'fecha_evento']
    list_filter = ['tipo_evento']
    search_fields = ['correo_intento']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ['id_tutor', 'nombre', 'telefono', 'id_usuario', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'telefono', 'id_usuario__correo']
