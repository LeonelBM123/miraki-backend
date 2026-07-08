from django.urls import path

from .views import CrearCodigoView, EstadoNinoView, VincularDispositivoView

urlpatterns = [
    path('pareo/crear/', CrearCodigoView.as_view(), name='pareo-crear'),
    path('pareo/estado/<int:nino_id>/', EstadoNinoView.as_view(), name='pareo-estado'),
    path('pareo/vincular/', VincularDispositivoView.as_view(), name='pareo-vincular'),
]
