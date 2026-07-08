from django.contrib import admin

from .models import Alerta, DispositivoToken, Posicion


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('id_alerta', 'id_nino', 'tipo', 'atendida', 'fecha_alerta')
    list_filter = ('tipo', 'atendida')
    search_fields = ('id_nino__nombre',)


@admin.register(DispositivoToken)
class DispositivoTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'id_usuario', 'id_dispositivo', 'plataforma', 'activo')
    list_filter = ('plataforma', 'activo')
    search_fields = ('token', 'id_usuario__correo')


@admin.register(Posicion)
class PosicionAdmin(admin.ModelAdmin):
    list_display = ('id_posicion', 'id_dispositivo', 'fecha_posicion', 'fecha_recepcion')
    search_fields = ('id_dispositivo__imei',)
