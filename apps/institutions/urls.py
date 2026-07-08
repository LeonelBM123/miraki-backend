from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminCentroChildrenListView,
    AdminCentroViewSet,
    CentroEducativoSelectionListView,
    CentroEducativoViewSet,
)

router = DefaultRouter()
router.register('centros', CentroEducativoViewSet, basename='centro-educativo')
router.register('admin-centros', AdminCentroViewSet, basename='admin-centro')

urlpatterns = [
    path('centers/', CentroEducativoSelectionListView.as_view(), name='centro-educativo-selection-list'),
    path('children/', AdminCentroChildrenListView.as_view(), name='admin-centro-children'),
]
urlpatterns += router.urls
