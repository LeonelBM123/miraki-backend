from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminCentroChildrenListView,
    AdminCentroViewSet,
    CentroEducativoSelectionListView,
    CentroEducativoViewSet,
    InstitutionMapView,
    MyCentroEducativoView,
)

router = DefaultRouter()
router.register('centros', CentroEducativoViewSet, basename='centro-educativo')
router.register('admin-centros', AdminCentroViewSet, basename='admin-centro')

urlpatterns = [
    path('centers/', CentroEducativoSelectionListView.as_view(), name='centro-educativo-selection-list'),
    path('children/', AdminCentroChildrenListView.as_view(), name='admin-centro-children'),
    path('my-center/', MyCentroEducativoView.as_view(), name='my-centro'),
    path('map/', InstitutionMapView.as_view(), name='institution-map'),
]
urlpatterns += router.urls
