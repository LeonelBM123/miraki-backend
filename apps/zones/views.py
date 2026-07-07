from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsTutor

from .models import ZonaSegura
from .serializers import (
    HorarioZonaSerializer,
    ZonaSeguraReadSerializer,
    ZonaSeguraUpdateSerializer,
    ZonaSeguraWriteSerializer,
)
from .services import (
    create_zona,
    desactivar_nino_zona,
    set_zona_active,
    sync_horarios_zona,
    update_zona,
    vincular_nino_zona,
)


class ZonaSeguraViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ZonaSegura.objects.none()
    permission_classes = [IsTutor]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ZonaSegura.objects.none()
        queryset = ZonaSegura.objects.filter(
            id_tutor_propietario__id_usuario=self.request.user
        )
        if self.action == 'list' and self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(activo=True)
        return queryset.order_by('nombre')

    def get_serializer_class(self):
        if self.action == 'create':
            return ZonaSeguraWriteSerializer
        if self.action in ['partial_update', 'update']:
            return ZonaSeguraUpdateSerializer
        return ZonaSeguraReadSerializer

    @extend_schema(
        request=ZonaSeguraWriteSerializer,
        responses={201: ZonaSeguraReadSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        zona = create_zona(user=request.user, data=serializer.validated_data, request=request)
        return Response(ZonaSeguraReadSerializer(zona).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=ZonaSeguraUpdateSerializer,
        responses={200: ZonaSeguraReadSerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        zona = self.get_object()
        serializer = self.get_serializer(zona, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        zona = update_zona(zona=zona, user=request.user, data=serializer.validated_data, request=request)
        return Response(ZonaSeguraReadSerializer(zona).data)

    @extend_schema(responses={200: ZonaSeguraReadSerializer})
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        zona = self.get_object()
        zona = set_zona_active(zona=zona, user=request.user, active=False, request=request)
        return Response(ZonaSeguraReadSerializer(zona).data)

    @extend_schema(responses={200: ZonaSeguraReadSerializer})
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        zona = self.get_object()
        zona = set_zona_active(zona=zona, user=request.user, active=True, request=request)
        return Response(ZonaSeguraReadSerializer(zona).data)

    @extend_schema(
        request=HorarioZonaSerializer(many=True),
        responses={200: ZonaSeguraReadSerializer},
    )
    @action(detail=True, methods=['put'])
    def horarios(self, request, pk=None):
        zona = self.get_object()
        if not isinstance(request.data, list):
            return Response(
                {'detail': 'Se espera una lista de horarios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = HorarioZonaSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        sync_horarios_zona(
            zona=zona,
            user=request.user,
            horarios_data=serializer.validated_data,
            request=request,
        )
        return Response(ZonaSeguraReadSerializer(zona).data)

    @extend_schema(responses={200: ZonaSeguraReadSerializer})
    @action(detail=True, methods=['post'])
    def vincular_nino(self, request, pk=None):
        zona = self.get_object()
        id_nino = request.data.get('id_nino')
        if not id_nino:
            return Response(
                {'detail': 'El campo id_nino es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        vincular_nino_zona(
            zona=zona,
            id_nino=id_nino,
            user=request.user,
            request=request,
        )
        return Response(ZonaSeguraReadSerializer(zona).data)

    @extend_schema(responses={200: ZonaSeguraReadSerializer})
    @action(detail=True, methods=['post'])
    def desactivar_nino(self, request, pk=None):
        zona = self.get_object()
        id_nino = request.data.get('id_nino')
        if not id_nino:
            return Response(
                {'detail': 'El campo id_nino es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        desactivar_nino_zona(
            zona=zona,
            id_nino=id_nino,
            user=request.user,
            request=request,
        )
        return Response(ZonaSeguraReadSerializer(zona).data)
