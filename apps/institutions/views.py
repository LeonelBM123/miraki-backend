from rest_framework import viewsets

from apps.accounts.permissions import IsSuperAdmin

from .models import AdminCentro, CentroEducativo
from .serializers import AdminCentroResponseSerializer, CentroEducativoResponseSerializer


class CentroEducativoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CentroEducativo.objects.all().order_by('nombre')
    serializer_class = CentroEducativoResponseSerializer
    permission_classes = [IsSuperAdmin]


class AdminCentroViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdminCentro.objects.select_related('id_usuario', 'id_centro').all().order_by('nombre')
    serializer_class = AdminCentroResponseSerializer
    permission_classes = [IsSuperAdmin]
