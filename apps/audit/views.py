from rest_framework import viewsets

from apps.accounts.permissions import IsSuperAdmin

from .models import Bitacora
from .serializers import BitacoraSerializer


class BitacoraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bitacora.objects.select_related('id_usuario').all().order_by('-fecha_evento')
    serializer_class = BitacoraSerializer
    permission_classes = [IsSuperAdmin]
