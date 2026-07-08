from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import (
    AlertaViewSet,
    DispositivoTokenViewSet,
    HistorialPosicionesView,
    ReportarPosicionView,
    SOSView,
    UltimaPosicionView,
)

router = DefaultRouter()
router.register('alertas', AlertaViewSet, basename='alerta')
router.register('dispositivo-tokens', DispositivoTokenViewSet, basename='dispositivo-token')

urlpatterns = [
    path('alertas/sos/', SOSView.as_view(), name='alerta-sos'),
    path('posiciones/ultima/', UltimaPosicionView.as_view(), name='ultima-posicion'),
    path('posiciones/reportar/', ReportarPosicionView.as_view(), name='reportar-posicion'),
    path('posiciones/historial/', HistorialPosicionesView.as_view(), name='historial-posiciones'),
] + router.urls
