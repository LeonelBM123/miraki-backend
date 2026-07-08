from rest_framework.routers import DefaultRouter

from .views import DispositivoViewSet

router = DefaultRouter()
router.register('dispositivos', DispositivoViewSet, basename='dispositivo')

urlpatterns = router.urls
