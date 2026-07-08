from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import IsAdminCentro, IsSuperAdmin, IsTutorAdminCentroOrSuperAdmin
from apps.children.models import Nino
from apps.children.serializers import NinoReadSerializer

from .models import AdminCentro, CentroEducativo
from .serializers import (
    AdminCentroResponseSerializer,
    CentroEducativoResponseSerializer,
    CentroEducativoSelectionSerializer,
)


class CentroEducativoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CentroEducativo.objects.all().order_by('nombre')
    serializer_class = CentroEducativoResponseSerializer
    permission_classes = [IsSuperAdmin]


class AdminCentroViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdminCentro.objects.select_related('id_usuario', 'id_centro').all().order_by('nombre')
    serializer_class = AdminCentroResponseSerializer
    permission_classes = [IsSuperAdmin]


@extend_schema(
    description='Lista paginada de centros educativos activos disponibles para selección.',
    responses={200: CentroEducativoSelectionSerializer},
)
class CentroEducativoSelectionListView(generics.ListAPIView):
    serializer_class = CentroEducativoSelectionSerializer
    permission_classes = [IsTutorAdminCentroOrSuperAdmin]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CentroEducativo.objects.none()
        return CentroEducativo.objects.filter(activo=True).order_by('nombre')


class AdminCentroChildrenListView(generics.ListAPIView):
    serializer_class = NinoReadSerializer
    permission_classes = [IsAdminCentro]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Nino.objects.none()
        try:
            admin_centro = self.request.user.admin_centro
        except (AttributeError, AdminCentro.DoesNotExist) as exc:
            raise PermissionDenied('El usuario autenticado no tiene perfil AdminCentro.') from exc

        return Nino.objects.select_related('centro', 'id_tutor').filter(
            centro=admin_centro.id_centro,
            activo=True,
        ).order_by('nombre')
