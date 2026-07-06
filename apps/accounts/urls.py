from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import BitacoraAccesoViewSet, MeView, RolViewSet, UsuarioViewSet

router = DefaultRouter()
router.register('roles', RolViewSet, basename='rol')
router.register('usuarios', UsuarioViewSet, basename='usuario')
router.register('bitacora-accesos', BitacoraAccesoViewSet, basename='bitacora-acceso')

urlpatterns = router.urls
urlpatterns += [path('me/', MeView.as_view(), name='account-me')]
