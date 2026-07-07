from rest_framework.routers import DefaultRouter

from .views import AdminCentroViewSet, CentroEducativoViewSet

router = DefaultRouter()
router.register('centros', CentroEducativoViewSet, basename='centro-educativo')
router.register('admin-centros', AdminCentroViewSet, basename='admin-centro')

urlpatterns = router.urls
