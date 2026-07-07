from django.contrib import admin

from .models import AdminCentro, CentroEducativo


@admin.register(CentroEducativo)
class CentroEducativoAdmin(admin.ModelAdmin):
    list_display = ['id_centro', 'nombre', 'direccion', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'direccion']


@admin.register(AdminCentro)
class AdminCentroAdmin(admin.ModelAdmin):
    list_display = ['id_admin_centro', 'nombre', 'telefono', 'id_usuario', 'id_centro', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'telefono', 'id_usuario__correo', 'id_centro__nombre']
