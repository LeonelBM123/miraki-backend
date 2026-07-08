from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from apps.accounts.authentication import PairingTokenAuthentication
from apps.alerts.models import Alerta, Posicion
from apps.children.models import Nino
from apps.zones.models import ZonaSegura

from .models import CodigoPareo
from .serializers import CrearCodigoSerializer, EstadoNinoSerializer, VincularDispositivoSerializer
from .services import generar_codigo, vincular_dispositivo


class CrearCodigoView(CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CrearCodigoSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        nino = serializer.validated_data['nino']
        CodigoPareo.objects.filter(id_nino=nino, usado=False).update(usado=True)

        codigo = generar_codigo()
        while CodigoPareo.objects.filter(codigo=codigo).exists():
            codigo = generar_codigo()

        expira_en = timezone.now() + timedelta(minutes=30)
        CodigoPareo.objects.create(
            codigo=codigo,
            id_nino=nino,
            id_tutor=request.user,
            expira_en=expira_en,
        )

        return Response({'codigo': codigo, 'expira_en': expira_en}, status=status.HTTP_201_CREATED)


class VincularDispositivoView(CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VincularDispositivoSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resultado = vincular_dispositivo(serializer.validated_data['codigo'])
        return Response(resultado, status=status.HTTP_201_CREATED)


class EstadoNinoView(APIView):
    authentication_classes = [PairingTokenAuthentication]
    permission_classes = [permissions.AllowAny]
    # La app del niño consulta el estado cada 30 s (~120/hora); con el throttle
    # 'user' global de 100/hour se agotaba el bucket compartido y luego el
    # reporte de ubicación recibía 429. Usa el bucket dedicado del dispositivo.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'kid_device'

    def get(self, request, nino_id):
        if not isinstance(request.user, Nino):
            raise AuthenticationFailed('Token de pareo requerido.')

        nino = get_object_or_404(Nino.objects.select_related('id_tutor__id_usuario'), pk=nino_id)
        if nino.id_nino != request.user.id_nino:
            raise AuthenticationFailed('El token de pareo no coincide con el niño solicitado.')

        ultima_posicion = (
            Posicion.objects.filter(id_dispositivo__id_nino=nino).order_by('-fecha_posicion').first()
        )
        if ultima_posicion and ultima_posicion.ubicacion is not None:
            zona_actual = ZonaSegura.objects.filter(
                activo=True,
                poligono__covers=ultima_posicion.ubicacion,
                ninos_asociados__id_nino=nino,
                ninos_asociados__activa=True,
            ).select_related('id_tutor_propietario', 'id_centro').first()
        else:
            zona_actual = None

        payload = {
            'id_nino': nino.id_nino,
            'nombre': nino.nombre,
            'tutor_nombre': nino.id_tutor.nombre,
            'activo': nino.activo,
            'ultima_posicion': (
                {
                    'lat': float(ultima_posicion.latitud),
                    'lng': float(ultima_posicion.longitud),
                    'fecha': ultima_posicion.fecha_posicion.isoformat(),
                }
                if ultima_posicion
                else None
            ),
            'zona_actual': {
                'nombre': zona_actual.nombre if zona_actual else 'Sin zona segura',
                'dentro': zona_actual is not None,
            },
            'alertas_recientes': Alerta.objects.filter(
                id_nino=nino,
                fecha_alerta__gte=timezone.now() - timedelta(days=1),
            ).count(),
        }

        return Response(EstadoNinoSerializer(payload).data)
