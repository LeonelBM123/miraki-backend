from django.db.models import OuterRef, Subquery
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTutor
from apps.children.models import Nino

from .models import Alerta, DispositivoToken, Posicion
from .serializers import (
    AlertaMarkAttendedSerializer,
    AlertaReadSerializer,
    DispositivoTokenSerializer,
)
from .services import atender_alerta


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

    def get(self, request):
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT v.id_nino, n.nombre, v.latitud, v.longitud, v.velocidad, v.fecha_posicion
                FROM vw_ultima_posicion_nino v
                JOIN nino n ON v.id_nino = n.id_nino
                JOIN tutor t ON n.id_tutor = t.id_tutor
                WHERE t.id_usuario_id = %s
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
                'fecha_posicion': row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ]

        return Response({'results': results})
