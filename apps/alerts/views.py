import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.gis.geos import Point
from django.db.models import OuterRef, Subquery
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.authentication import PairingTokenAuthentication
from apps.accounts.permissions import IsTutor
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo

from .models import Alerta, DispositivoToken, Posicion
from .serializers import (
    AlertaMarkAttendedSerializer,
    AlertaReadSerializer,
    DispositivoTokenSerializer,
    PosicionReportadaSerializer,
    ReportarPosicionSerializer,
)
from .tasks import evaluar_bateria, evaluar_zonas
from .services import atender_alerta

logger = logging.getLogger(__name__)


class AlertaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Alerta.objects.none()
    permission_classes = [permissions.IsAuthenticated, IsTutor]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Alerta.objects.none()

        queryset = (
            Alerta.objects.select_related('id_nino', 'id_nino__id_tutor', 'id_zona', 'id_posicion')
            .filter(id_nino__id_tutor__id_usuario=self.request.user)
        )

        nino_id = self.request.query_params.get('nino_id')
        if nino_id:
            queryset = queryset.filter(id_nino_id=nino_id)

        atendida = self.request.query_params.get('atendida')
        if atendida is not None:
            queryset = queryset.filter(atendida=atendida.lower() in {'true', '1', 'yes'})

        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        desde = self.request.query_params.get('desde')
        if desde:
            queryset = queryset.filter(fecha_alerta__date__gte=desde)

        hasta = self.request.query_params.get('hasta')
        if hasta:
            queryset = queryset.filter(fecha_alerta__date__lte=hasta)

        return queryset.order_by('-fecha_alerta')

    def get_serializer_class(self):
        if self.action == 'atender':
            return AlertaMarkAttendedSerializer
        return AlertaReadSerializer

    @action(detail=True, methods=['post'])
    def atender(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alerta = self.get_object()
        alerta = atender_alerta(alerta=alerta, user=request.user, request=request)
        return Response(AlertaReadSerializer(alerta).data)

    @action(detail=False, methods=['get'], url_path='reporte')
    def reporte(self, request):
        """CU-37: reporte CSV de alertas del tutor, respetando los mismos filtros."""
        import csv

        from django.http import HttpResponse
        from django.utils import timezone as tz

        queryset = self.get_queryset()

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f'reporte_alertas_{tz.now().strftime("%Y%m%d_%H%M")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Fecha', 'Nino', 'Tipo', 'Zona', 'Estado', 'Latitud', 'Longitud'])
        tipos = dict(Alerta.TipoAlerta.choices)
        for alerta in queryset:
            writer.writerow([
                tz.localtime(alerta.fecha_alerta).strftime('%Y-%m-%d %H:%M'),
                alerta.id_nino.nombre,
                tipos.get(alerta.tipo, alerta.tipo),
                alerta.id_zona.nombre if alerta.id_zona else '',
                'Atendida' if alerta.atendida else 'Pendiente',
                alerta.id_posicion.latitud if alerta.id_posicion else '',
                alerta.id_posicion.longitud if alerta.id_posicion else '',
            ])
        return response


class DispositivoTokenViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = DispositivoToken.objects.none()
    serializer_class = DispositivoTokenSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DispositivoToken.objects.none()
        return DispositivoToken.objects.filter(id_usuario=self.request.user).order_by('id')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        token = DispositivoToken.objects.filter(token=data['token']).first()
        created = token is None
        if created:
            token = DispositivoToken.objects.create(
                id_usuario=request.user,
                id_dispositivo=data.get('id_dispositivo'),
                token=data['token'],
                plataforma=data['plataforma'],
                activo=True,
                creado_por=request.user,
                modificado_por=request.user,
            )
        else:
            token.id_usuario = request.user
            token.id_dispositivo = data.get('id_dispositivo')
            token.token = data['token']
            token.plataforma = data['plataforma']
            token.activo = True
            token.modificado_por = request.user
            token.save(
                update_fields=['id_usuario', 'id_dispositivo', 'token', 'plataforma', 'activo', 'modificado_por']
            )

        return Response(self.get_serializer(token).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class UltimaPosicionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # El mapa del tutor consulta esta vista cada 30 s (~120/hora); con el
    # throttle 'user' de 100/hour se agotaba y el mapa caía a "Reconectando".
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'tracking'

    def get(self, request):
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT v.id_nino, n.nombre, v.latitud, v.longitud, v.velocidad, v.bateria, v.fecha_posicion
                FROM vw_ultima_posicion_nino v
                JOIN nino n ON v.id_nino = n.id_nino
                JOIN tutor t ON n.id_tutor = t.id_tutor
                WHERE t.id_usuario = %s
                """,
                [request.user.id_usuario],
            )
            rows = cursor.fetchall()

        results = [
            {
                'id_nino': row[0],
                'nombre': row[1],
                'latitud': float(row[2]) if row[2] is not None else None,
                'longitud': float(row[3]) if row[3] is not None else None,
                'velocidad': float(row[4]) if row[4] is not None else None,
                'bateria': row[5],
                'fecha_posicion': row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ]

        return Response({'results': results})


class ReportarPosicionView(APIView):
    authentication_classes = [PairingTokenAuthentication]
    permission_classes = [permissions.AllowAny]
    # El dispositivo del niño reporta seguido; usa un bucket propio y generoso
    # ('kid_device') en vez del throttle 'user' global (100/hour), que se
    # agotaba y devolvía 429 al niño impidiéndole mandar su ubicación.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'kid_device'

    def post(self, request):
        if not isinstance(request.user, Nino):
            raise AuthenticationFailed('Token de pareo requerido.')

        serializer = ReportarPosicionSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning('Posicion report 400: errors=%s data=%s', serializer.errors, request.data)
            serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        dispositivo, _ = Dispositivo.objects.get_or_create(
            id_nino=request.user,
            defaults={
                'imei': f'APP-{request.user.id_nino}',
                'modelo': 'Miraki Kid App',
                'estado': 'vinculado',
                'activo': True,
            },
        )
        if not dispositivo.activo:
            dispositivo.activo = True
            dispositivo.save(update_fields=['activo'])

        posicion = Posicion.objects.create(
            id_dispositivo=dispositivo,
            latitud=data['latitud'],
            longitud=data['longitud'],
            ubicacion=Point(float(data['longitud']), float(data['latitud']), srid=4326),
            velocidad=data.get('velocidad'),
            bateria=data.get('bateria'),
            fecha_posicion=data['fecha_posicion'],
        )

        try:
            evaluar_zonas.delay()
        except Exception as exc:
            logger.warning('Zone evaluation dispatch failed after child position report: %s', exc)
        if posicion.bateria is not None:
            try:
                evaluar_bateria.delay(posicion.id_posicion)
            except Exception as exc:
                logger.warning('Battery evaluation dispatch failed after child position report: %s', exc)
        self._notify_tracking_groups(request.user, posicion)

        return Response(PosicionReportadaSerializer(posicion).data, status=status.HTTP_201_CREATED)

    def _notify_tracking_groups(self, nino, posicion):
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        payload = {
            'type': 'posicion.update',
            'child_id': nino.id_nino,
            'nombre': nino.nombre,
            'latitud': float(posicion.latitud),
            'longitud': float(posicion.longitud),
            'velocidad': float(posicion.velocidad) if posicion.velocidad is not None else None,
            'bateria': posicion.bateria,
            'fecha_posicion': posicion.fecha_posicion.isoformat(),
        }
        group_names = {f'tracking-{nino.id_tutor.id_usuario_id}', f'tracking-{nino.id_nino}'}
        for group_name in group_names:
            try:
                async_to_sync(channel_layer.group_send)(group_name, payload)
            except Exception as exc:
                logger.warning('Tracking websocket dispatch failed for group %s: %s', group_name, exc)


class SOSView(APIView):
    authentication_classes = [PairingTokenAuthentication]
    permission_classes = [permissions.AllowAny]
    # Un SOS es una emergencia: nunca debe limitarse por rate-limit.
    throttle_classes = []

    def post(self, request):
        if not isinstance(request.user, Nino):
            raise AuthenticationFailed('Token de pareo requerido.')

        alerta = Alerta.objects.create(id_nino=request.user, tipo=Alerta.TipoAlerta.SOS)
        return Response(AlertaReadSerializer(alerta).data, status=status.HTTP_201_CREATED)


class HistorialPosicionesView(APIView):
    """CU-38: historial de posiciones (recorrido) de un niño del tutor por rango de
    fechas. Devuelve JSON para consulta o CSV (?formato=csv) para exportar."""

    permission_classes = [permissions.IsAuthenticated]
    MAX_JSON = 1000

    def get(self, request):
        nino_id = request.query_params.get('nino')
        if not nino_id:
            return Response({'detail': 'El parámetro nino es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            nino = Nino.objects.get(pk=nino_id, id_tutor__id_usuario=request.user)
        except (Nino.DoesNotExist, ValueError):
            return Response({'detail': 'El niño no existe o no pertenece a tu cuenta.'}, status=status.HTTP_404_NOT_FOUND)

        queryset = Posicion.objects.filter(id_dispositivo__id_nino=nino)
        desde = request.query_params.get('desde')
        if desde:
            queryset = queryset.filter(fecha_posicion__date__gte=desde)
        hasta = request.query_params.get('hasta')
        if hasta:
            queryset = queryset.filter(fecha_posicion__date__lte=hasta)
        queryset = queryset.order_by('fecha_posicion', 'id_posicion')

        if request.query_params.get('formato') == 'csv':
            return self._csv(nino, queryset)

        posiciones = list(queryset[: self.MAX_JSON])
        results = [
            {
                'id_posicion': p.id_posicion,
                'latitud': float(p.latitud),
                'longitud': float(p.longitud),
                'velocidad': float(p.velocidad) if p.velocidad is not None else None,
                'bateria': p.bateria,
                'fecha_posicion': p.fecha_posicion.isoformat(),
            }
            for p in posiciones
        ]
        return Response({
            'nino': {'id_nino': nino.id_nino, 'nombre': nino.nombre},
            'count': queryset.count(),
            'truncated': queryset.count() > self.MAX_JSON,
            'results': results,
        })

    def _csv(self, nino, queryset):
        import csv

        from django.http import HttpResponse
        from django.utils import timezone as tz

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f'historial_{nino.id_nino}_{tz.now().strftime("%Y%m%d_%H%M")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(['Fecha', 'Latitud', 'Longitud', 'Velocidad', 'Bateria'])
        for p in queryset.iterator():
            writer.writerow([
                tz.localtime(p.fecha_posicion).strftime('%Y-%m-%d %H:%M:%S'),
                p.latitud,
                p.longitud,
                p.velocidad if p.velocidad is not None else '',
                p.bateria if p.bateria is not None else '',
            ])
        return response
