from rest_framework.routers import DefaultRouter

from .views import NinoViewSet

router = DefaultRouter()
router.register('ninos', NinoViewSet, basename='nino')

urlpatterns = router.urls
