from unittest import mock
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Rol, Tutor
from apps.alerts.models import Posicion
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo
from apps.pareo.services import generar_token_pareo

Usuario = get_user_model()


class ReportarPosicionViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.rol_tutor, _ = Rol.objects.get_or_create(
            nombre_rol='Tutor',
            defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'},
        )
        self.usuario = Usuario.objects.create_user(
            correo='tutor-reportar@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )
        self.tutor = Tutor.objects.create(id_usuario=self.usuario, nombre='Tutor Reportar', telefono='70000100')
        self.nino = Nino.objects.create(id_tutor=self.tutor, nombre='Ana')
        self.dispositivo = Dispositivo.objects.create(
            id_nino=self.nino,
            imei='864201111111111',
            estado='vinculado',
            activo=True,
        )
        self.token = generar_token_pareo(self.nino)
        self.payload = {
            'latitud': -16.450001,
            'longitud': -68.150002,
            'velocidad': 5.5,
            'fecha_posicion': timezone.now().isoformat(),
        }

    @mock.patch('apps.alerts.views.get_channel_layer', return_value=None)
    @mock.patch('apps.alerts.views.evaluar_zonas.delay')
    def test_reports_position_with_pairing_token(self, mock_evaluar_zonas, _mock_channel_layer):
        response = self.client.post(
            '/api/v1/posiciones/reportar/',
            self.payload,
            format='json',
            HTTP_X_KID_TOKEN=self.token,
        )

        self.assertEqual(response.status_code, 201)
        posicion = Posicion.objects.get()
        self.assertEqual(posicion.id_dispositivo, self.dispositivo)
        self.assertEqual(float(posicion.latitud), self.payload['latitud'])
        self.assertEqual(float(posicion.longitud), self.payload['longitud'])
        self.assertEqual(posicion.ubicacion, Point(self.payload['longitud'], self.payload['latitud'], srid=4326))
        mock_evaluar_zonas.assert_called_once_with()

    def test_missing_token_returns_unauthorized(self):
        response = self.client.post('/api/v1/posiciones/reportar/', self.payload, format='json')

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Posicion.objects.exists())

    def test_invalid_token_returns_unauthorized(self):
        response = self.client.post(
            '/api/v1/posiciones/reportar/',
            self.payload,
            format='json',
            HTTP_X_KID_TOKEN='invalid-token',
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Posicion.objects.exists())

    @mock.patch('apps.alerts.views.get_channel_layer', return_value=None)
    @mock.patch('apps.alerts.views.evaluar_zonas.delay')
    def test_inactive_device_is_reactivated_and_reports(self, _mock_evaluar_zonas, _mock_channel_layer):
        # El endpoint reactiva el dispositivo del niño (get_or_create) en vez de
        # rechazar: miraki_kid auto-provisiona su dispositivo al reportar.
        self.dispositivo.activo = False
        self.dispositivo.save(update_fields=['activo'])

        response = self.client.post(
            '/api/v1/posiciones/reportar/',
            self.payload,
            format='json',
            HTTP_X_KID_TOKEN=self.token,
        )

        self.assertEqual(response.status_code, 201)
        self.dispositivo.refresh_from_db()
        self.assertTrue(self.dispositivo.activo)
        self.assertEqual(Posicion.objects.count(), 1)
        self.assertEqual(Posicion.objects.get().id_dispositivo, self.dispositivo)

    def test_invalid_coordinates_return_bad_request(self):
        payload = {**self.payload, 'latitud': -100}

        response = self.client.post(
            '/api/v1/posiciones/reportar/',
            payload,
            format='json',
            HTTP_X_KID_TOKEN=self.token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('latitud', response.data)
        self.assertFalse(Posicion.objects.exists())

    def test_future_position_timestamp_returns_bad_request(self):
        payload = {**self.payload, 'fecha_posicion': (timezone.now() + timedelta(minutes=10)).isoformat()}

        response = self.client.post(
            '/api/v1/posiciones/reportar/',
            payload,
            format='json',
            HTTP_X_KID_TOKEN=self.token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('fecha_posicion', response.data)
        self.assertFalse(Posicion.objects.exists())

    def test_stale_position_timestamp_returns_bad_request(self):
        payload = {**self.payload, 'fecha_posicion': (timezone.now() - timedelta(days=2)).isoformat()}

        response = self.client.post(
            '/api/v1/posiciones/reportar/',
            payload,
            format='json',
            HTTP_X_KID_TOKEN=self.token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('fecha_posicion', response.data)
        self.assertFalse(Posicion.objects.exists())
