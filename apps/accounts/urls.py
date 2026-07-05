from rest_framework.routers import DefaultRouter

from .views import BitacoraAccesoViewSet, RolViewSet, UsuarioViewSet

router = DefaultRouter()
router.register('roles', RolViewSet, basename='rol')
router.register('usuarios', UsuarioViewSet, basename='usuario')
router.register('bitacora-accesos', BitacoraAccesoViewSet, basename='bitacora-acceso')

urlpatterns = router.urls
