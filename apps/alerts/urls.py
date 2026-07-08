from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import AlertaViewSet, DispositivoTokenViewSet, UltimaPosicionView

router = DefaultRouter()
router.register('alertas', AlertaViewSet, basename='alerta')
router.register('dispositivo-tokens', DispositivoTokenViewSet, basename='dispositivo-token')

urlpatterns = router.urls + [path('posiciones/ultima/', UltimaPosicionView.as_view(), name='ultima-posicion')]
