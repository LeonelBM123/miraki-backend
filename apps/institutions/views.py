from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminCentro, IsSuperAdmin, IsTutorAdminCentroOrSuperAdmin
from apps.children.models import Nino
from apps.children.serializers import NinoReadSerializer

from .models import AdminCentro, CentroEducativo
from .serializers import (
    AdminCentroResponseSerializer,
    CentroEducativoResponseSerializer,
    CentroEducativoSelectionSerializer,
    MyCentroEducativoSerializer,
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


class MyCentroEducativoView(generics.RetrieveUpdateAPIView):
    """CU-07: el AdminCentro consulta y edita los datos de su propio centro."""

    serializer_class = MyCentroEducativoSerializer
    permission_classes = [IsAdminCentro]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        try:
            admin_centro = self.request.user.admin_centro
        except (AttributeError, AdminCentro.DoesNotExist) as exc:
            raise PermissionDenied('El usuario autenticado no tiene perfil AdminCentro.') from exc
        return admin_centro.id_centro

    def perform_update(self, serializer):
        serializer.save(modificado_por=self.request.user)


class InstitutionMapView(APIView):
    """CU-36: mapa del centro con la última posición y estado dentro/fuera de zona
    de cada niño del centro, más los polígonos de las zonas institucionales."""

    permission_classes = [IsAdminCentro]

    def get(self, request):
        import json

        from django.contrib.gis.geos import Point

        from apps.alerts.models import Posicion
        from apps.zones.models import NinoZonaSegura, ZonaSegura

        try:
            centro = request.user.admin_centro.id_centro
        except (AttributeError, AdminCentro.DoesNotExist) as exc:
            raise PermissionDenied('El usuario autenticado no tiene perfil AdminCentro.') from exc

        children_payload = []
        for nino in Nino.objects.filter(centro=centro, activo=True).order_by('nombre'):
            posicion = (
                Posicion.objects.filter(id_dispositivo__id_nino=nino)
                .order_by('-fecha_posicion', '-id_posicion')
                .first()
            )
            dentro = None
            if posicion is not None:
                zona_ids = list(
                    NinoZonaSegura.objects.filter(
                        id_nino=nino,
                        activa=True,
                        id_zona__activo=True,
                    ).values_list('id_zona', flat=True)
                )
                if zona_ids:
                    punto = Point(float(posicion.longitud), float(posicion.latitud), srid=4326)
                    dentro = ZonaSegura.objects.filter(pk__in=zona_ids, poligono__covers=punto).exists()

            children_payload.append({
                'id_nino': nino.id_nino,
                'nombre': nino.nombre,
                'latitud': float(posicion.latitud) if posicion else None,
                'longitud': float(posicion.longitud) if posicion else None,
                'bateria': posicion.bateria if posicion else None,
                'fecha_posicion': posicion.fecha_posicion.isoformat() if posicion else None,
                'dentro_zona': dentro,
            })

        zonas_payload = []
        for zona in ZonaSegura.objects.filter(id_centro=centro, activo=True):
            if zona.poligono:
                zonas_payload.append({
                    'id_zona': zona.id_zona,
                    'nombre': zona.nombre,
                    'poligono': json.loads(zona.poligono.geojson),
                })

        return Response({'children': children_payload, 'zonas': zonas_payload})


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
