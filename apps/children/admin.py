from django.contrib import admin

from .models import Nino


@admin.register(Nino)
class NinoAdmin(admin.ModelAdmin):
    list_display = ['id_nino', 'nombre', 'id_tutor', 'activo', 'fecha_nacimiento']
    list_filter = ['activo']
    search_fields = ['nombre', 'id_tutor__nombre', 'id_tutor__id_usuario__correo']
