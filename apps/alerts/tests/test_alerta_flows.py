from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from django.urls import resolve
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Rol, Tutor
from apps.alerts.models import Alerta, Posicion
from apps.alerts.serializers import (
    AlertaMarkAttendedSerializer,
    AlertaReadSerializer,
    DispositivoTokenSerializer,
)
from apps.alerts.services import atender_alerta
from apps.alerts.views import AlertaViewSet, DispositivoTokenViewSet
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo
from apps.zones.models import ZonaSegura

Usuario = get_user_model()


class AlertaFlowsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.rol_tutor, _ = Rol.objects.get_or_create(
            nombre_rol='Tutor',
            defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'},
        )
        self.rol_admin, _ = Rol.objects.get_or_create(
            nombre_rol='AdminCentro',
            defaults={'descripcion': 'Administrador de un centro educativo'},
        )

        self.usuario = Usuario.objects.create_user(
            correo='tutor-alertas@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )
        self.tutor = Tutor.objects.create(
            id_usuario=self.usuario,
            nombre='Tutor Alertas',
            telefono='70000010',
        )

        self.otro_usuario = Usuario.objects.create_user(
            correo='otro-tutor@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )
        self.otro_tutor = Tutor.objects.create(
            id_usuario=self.otro_usuario,
            nombre='Otro Tutor',
            telefono='70000011',
        )

        self.admin_centro = Usuario.objects.create_user(
            correo='admin-centro@example.com',
            password='StrongPass123!',
            id_rol=self.rol_admin,
        )

        self.alerta = self._build_alert(self.tutor, 'principal', Alerta.TipoAlerta.SALIDA_ZONA)
        self.alerta_otro = self._build_alert(self.otro_tutor, 'secundaria', Alerta.TipoAlerta.SOS)

    def _build_alert(self, tutor, suffix, tipo):
        nino = Nino.objects.create(id_tutor=tutor, nombre=f'Niño {suffix}')
        dispositivo = Dispositivo.objects.create(
            id_nino=nino,
            imei=f'864200000000{len(suffix):02d}{nino.id_nino % 100:02d}',
            estado='vinculado',
            activo=True,
        )
        poligono = Polygon(
            (
                (-68.20, -16.50),
                (-68.10, -16.50),
                (-68.10, -16.40),
                (-68.20, -16.40),
                (-68.20, -16.50),
            )
        )
        poligono.srid = 4326
        zona = ZonaSegura.objects.create(
            nombre=f'Zona {suffix}',
            poligono=poligono,
            id_tutor_propietario=tutor,
            activo=True,
        )
        posicion = Posicion.objects.create(
            id_dispositivo=dispositivo,
            latitud='-16.450000',
            longitud='-68.150000',
            ubicacion=Point(-68.150000, -16.450000, srid=4326),
            velocidad='12.34',
            fecha_posicion=timezone.now(),
        )
        return Alerta.objects.create(
            id_nino=nino,
            id_zona=zona,
            id_posicion=posicion,
            tipo=tipo,
        )

    def test_atender_alerta_flips_state(self):
        alerta = atender_alerta(alerta=self.alerta, user=self.usuario)

        alerta.refresh_from_db()

        self.assertTrue(alerta.atendida)
        self.assertIsNotNone(alerta.fecha_atencion)
        self.assertEqual(alerta.atendida_por, self.usuario)

    def test_atender_alerta_idempotent(self):
        atender_alerta(alerta=self.alerta, user=self.usuario)
        alerta = atender_alerta(alerta=self.alerta, user=self.usuario)

        self.assertTrue(alerta.atendida)
        self.assertEqual(alerta.atendida_por, self.usuario)

    def test_alerta_read_serializer_fields(self):
        data = AlertaReadSerializer(self.alerta).data

        self.assertEqual(data['id_alerta'], self.alerta.id_alerta)
        self.assertEqual(data['id_nino'], self.alerta.id_nino_id)
        self.assertEqual(data['nombre_nino'], self.alerta.id_nino.nombre)
        self.assertEqual(data['id_zona'], self.alerta.id_zona_id)
        self.assertEqual(data['nombre_zona'], self.alerta.id_zona.nombre)
        self.assertEqual(data['id_posicion'], self.alerta.id_posicion_id)
        self.assertEqual(data['latitud'], str(self.alerta.id_posicion.latitud))
        self.assertEqual(data['longitud'], str(self.alerta.id_posicion.longitud))
        self.assertEqual(data['tipo'], self.alerta.tipo)
        self.assertFalse(data['atendida'])

    def test_alerta_mark_attended_serializer(self):
        serializer = AlertaMarkAttendedSerializer(data={})

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_dispositivo_token_serializer_validate(self):
        valido = DispositivoTokenSerializer(data={'token': 'push-token-001', 'plataforma': 'android'})
        invalido = DispositivoTokenSerializer(data={'token': 'push-token-002', 'plataforma': 'windows'})

        self.assertTrue(valido.is_valid(), valido.errors)
        self.assertFalse(invalido.is_valid())
        self.assertIn('plataforma', invalido.errors)

    def test_list_alertas_own_children(self):
        self.client.force_authenticate(user=self.usuario)

        response = self.client.get('/api/v1/alertas/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id_alerta'], self.alerta.id_alerta)

    def test_retrieve_alerta(self):
        self.client.force_authenticate(user=self.usuario)

        response = self.client.get(f'/api/v1/alertas/{self.alerta.id_alerta}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id_alerta'], self.alerta.id_alerta)
        self.assertEqual(response.data['nombre_nino'], self.alerta.id_nino.nombre)

    def test_atender_action_200(self):
        self.client.force_authenticate(user=self.usuario)

        response = self.client.post(f'/api/v1/alertas/{self.alerta.id_alerta}/atender/', data={})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['atendida'])
        self.assertEqual(response.data['atendida_por'], self.usuario.id_usuario)

    def test_cross_tutor_404(self):
        self.client.force_authenticate(user=self.usuario)

        retrieve_response = self.client.get(f'/api/v1/alertas/{self.alerta_otro.id_alerta}/')
        atender_response = self.client.post(f'/api/v1/alertas/{self.alerta_otro.id_alerta}/atender/', data={})

        self.assertEqual(retrieve_response.status_code, 404)
        self.assertEqual(atender_response.status_code, 404)

    def test_list_pagination(self):
        for index in range(21):
            self._build_alert(self.tutor, f'page-{index}', Alerta.TipoAlerta.SALIDA_ZONA)

        self.client.force_authenticate(user=self.usuario)

        response = self.client.get('/api/v1/alertas/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 22)
        self.assertEqual(len(response.data['results']), 20)

    def test_list_filter_by_tipo(self):
        self._build_alert(self.tutor, 'sos', Alerta.TipoAlerta.SOS)

        self.client.force_authenticate(user=self.usuario)

        response = self.client.get('/api/v1/alertas/?tipo=sos')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['tipo'], Alerta.TipoAlerta.SOS)

    def test_list_filter_by_atendida(self):
        atender_alerta(alerta=self.alerta, user=self.usuario)

        self.client.force_authenticate(user=self.usuario)

        response = self.client.get('/api/v1/alertas/?atendida=true')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertTrue(response.data['results'][0]['atendida'])

    def test_non_tutor_gets_403(self):
        self.client.force_authenticate(user=self.admin_centro)

        response = self.client.get('/api/v1/alertas/')

        self.assertEqual(response.status_code, 403)

    def test_urls_resolve(self):
        alerta_match = resolve('/api/v1/alertas/')
        token_match = resolve('/api/v1/dispositivo-tokens/')

        self.assertIs(alerta_match.func.cls, AlertaViewSet)
        self.assertIs(token_match.func.cls, DispositivoTokenViewSet)

    def test_list_filter_by_date_range(self):
        vieja = self._build_alert(self.tutor, 'vieja', Alerta.TipoAlerta.SALIDA_ZONA)
        Alerta.objects.filter(pk=vieja.id_alerta).update(
            fecha_alerta=timezone.now() - timezone.timedelta(days=10),
        )

        self.client.force_authenticate(user=self.usuario)
        hoy = timezone.localtime().date().isoformat()
        response = self.client.get(f'/api/v1/alertas/?desde={hoy}')

        self.assertEqual(response.status_code, 200)
        ids = {row['id_alerta'] for row in response.data['results']}
        self.assertIn(self.alerta.id_alerta, ids)
        self.assertNotIn(vieja.id_alerta, ids)

    def test_reporte_csv_attachment_only_own_alerts(self):
        self.client.force_authenticate(user=self.usuario)

        response = self.client.get('/api/v1/alertas/reporte/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment; filename="reporte_alertas_', response['Content-Disposition'])
        body = response.content.decode('utf-8')
        self.assertIn('Fecha,Nino,Tipo,Zona,Estado', body)
        self.assertIn(self.alerta.id_nino.nombre, body)
        self.assertNotIn(self.alerta_otro.id_nino.nombre, body)
