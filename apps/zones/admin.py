from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import ZonaSegura


@admin.register(ZonaSegura)
class ZonaSeguraAdmin(GISModelAdmin):
    list_display = ['id_zona', 'nombre', 'activo', 'id_tutor_propietario', 'id_centro']
    list_filter = ['activo']
    search_fields = ['nombre']
