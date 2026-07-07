from django.contrib import admin

from .models import Bitacora


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ['id_bitacora', 'tabla_afectada', 'id_registro', 'operacion', 'id_usuario', 'fecha_evento']
    list_filter = ['operacion', 'tabla_afectada']
    search_fields = ['tabla_afectada', 'id_registro', 'id_usuario__correo']
    readonly_fields = [
        'tabla_afectada', 'id_registro', 'operacion', 'datos_anteriores',
        'datos_nuevos', 'id_usuario', 'fecha_evento', 'direccion_ip',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
