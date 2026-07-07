from rest_framework.routers import DefaultRouter

from .views import ZonaSeguraViewSet

router = DefaultRouter()
router.register('zonas', ZonaSeguraViewSet, basename='zonas')

urlpatterns = router.urls
