from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsTutor

from .models import Nino
from .serializers import (
    AssignCenterSerializer,
    NinoCreateRequestSerializer,
    NinoReadSerializer,
    NinoUpdateRequestSerializer,
)
from .services import assign_nino_center, create_nino, remove_nino_center, set_nino_active, update_nino


class NinoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Nino.objects.none()
    permission_classes = [IsTutor]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Nino.objects.none()
        queryset = Nino.objects.select_related('id_tutor', 'id_tutor__id_usuario', 'centro').filter(
            id_tutor__id_usuario=self.request.user,
        )
        if self.action == 'list' and self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(activo=True)
        return queryset.order_by('nombre')

    def get_serializer_class(self):
        if self.action == 'create':
            return NinoCreateRequestSerializer
        if self.action in ['partial_update', 'update']:
            return NinoUpdateRequestSerializer
        if self.action == 'assign_center':
            return AssignCenterSerializer
        return NinoReadSerializer

    @extend_schema(
        request=NinoCreateRequestSerializer,
        responses={201: NinoReadSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nino = create_nino(user=request.user, data=serializer.validated_data, request=request)
        return Response(NinoReadSerializer(nino).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=NinoUpdateRequestSerializer,
        responses={200: NinoReadSerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        nino = self.get_object()
        serializer = self.get_serializer(nino, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        nino = update_nino(nino=nino, user=request.user, data=serializer.validated_data, request=request)
        return Response(NinoReadSerializer(nino).data)

    @extend_schema(responses={200: NinoReadSerializer})
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        nino = self.get_object()
        nino = set_nino_active(nino=nino, user=request.user, active=False, request=request)
        return Response(NinoReadSerializer(nino).data)

    @extend_schema(responses={200: NinoReadSerializer})
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        nino = self.get_object()
        nino = set_nino_active(nino=nino, user=request.user, active=True, request=request)
        return Response(NinoReadSerializer(nino).data)

    @extend_schema(
        request=AssignCenterSerializer,
        responses={200: NinoReadSerializer},
    )
    @action(detail=True, methods=['post'], url_path='assign-center')
    def assign_center(self, request, pk=None):
        nino = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nino = assign_nino_center(
            nino=nino,
            centro=serializer.validated_data['centro_id'],
            user=request.user,
            request=request,
        )
        return Response(NinoReadSerializer(nino).data)

    @extend_schema(responses={200: NinoReadSerializer})
    @action(detail=True, methods=['post'], url_path='remove-center')
    def remove_center(self, request, pk=None):
        nino = self.get_object()
        nino = remove_nino_center(nino=nino, user=request.user, request=request)
        return Response(NinoReadSerializer(nino).data)
