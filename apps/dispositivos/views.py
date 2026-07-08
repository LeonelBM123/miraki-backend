from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from apps.accounts.permissions import IsTutor

from .models import Dispositivo
from .serializers import DispositivoReadSerializer, LinkDeviceSerializer
from .services import get_device_status, link_device


class DispositivoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Dispositivo.objects.none()
    permission_classes = [IsTutor]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Dispositivo.objects.none()
        return (
            Dispositivo.objects.select_related('id_nino', 'id_nino__id_tutor', 'id_nino__id_tutor__id_usuario')
            .filter(id_nino__id_tutor__id_usuario=self.request.user)
            .order_by('imei')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return LinkDeviceSerializer
        return DispositivoReadSerializer

    def _serialize_with_status(self, device):
        payload = DispositivoReadSerializer(device).data
        payload.update(get_device_status(device))
        return payload

    @extend_schema(request=LinkDeviceSerializer, responses={201: DispositivoReadSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = link_device(
            imei=serializer.validated_data['imei'],
            id_nino=serializer.validated_data['id_nino'],
            user=request.user,
            request=request,
        )
        return Response(self._serialize_with_status(device), status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: DispositivoReadSerializer})
    def retrieve(self, request, *args, **kwargs):
        device = self.get_object()
        return Response(self._serialize_with_status(device))

    @extend_schema(responses={200: DispositivoReadSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        payload = [self._serialize_with_status(device) for device in queryset]
        return Response(payload)
