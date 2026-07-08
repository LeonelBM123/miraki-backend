from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Rol, Tutor
from apps.alerts.models import Alerta, DispositivoToken, Posicion
from apps.alerts.tasks import evaluar_bateria
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo

Usuario = get_user_model()


@override_settings(BATERIA_UMBRAL_ALERTA=15, BATERIA_DEDUP_HORAS=6)
class EvaluarBateriaTaskTests(TestCase):
    def setUp(self):
        self.rol_tutor, _ = Rol.objects.get_or_create(
            nombre_rol='Tutor',
            defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'},
        )
        self.usuario = Usuario.objects.create_user(
            correo='tutor-bateria@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )
        self.tutor = Tutor.objects.create(id_usuario=self.usuario, nombre='Tutor Batería', telefono='70000020')
        self.nino = Nino.objects.create(id_tutor=self.tutor, nombre='Mateo')
        self.dispositivo = Dispositivo.objects.create(
            id_nino=self.nino,
            imei='864209876543211',
            estado='vinculado',
            activo=True,
        )
        DispositivoToken.objects.create(
            id_usuario=self.usuario,
            token='fcm-test-token-bateria',
            plataforma=DispositivoToken.Plataforma.ANDROID,
            activo=True,
        )

    def _create_position(self, *, bateria):
        return Posicion.objects.create(
            id_dispositivo=self.dispositivo,
            latitud='-16.500000',
            longitud='-68.150000',
            ubicacion=Point(-68.150000, -16.500000, srid=4326),
            velocidad='0.00',
            bateria=bateria,
            fecha_posicion=timezone.now(),
        )

    @mock.patch('apps.alerts.tasks.send_push_notification.delay')
    def test_low_battery_creates_alert_and_dispatches_push(self, mock_delay):
        posicion = self._create_position(bateria=10)

        result = evaluar_bateria(posicion.id_posicion)

        alerta = Alerta.objects.get()
        self.assertEqual(alerta.tipo, Alerta.TipoAlerta.BATERIA_BAJA)
        self.assertEqual(alerta.id_nino, self.nino)
        self.assertEqual(alerta.id_posicion, posicion)
        self.assertIn('created', result)
        mock_delay.assert_called_once_with(alerta.id_alerta)

    @mock.patch('apps.alerts.tasks.send_push_notification.delay')
    def test_battery_at_threshold_creates_alert(self, mock_delay):
        posicion = self._create_position(bateria=15)

        evaluar_bateria(posicion.id_posicion)

        self.assertEqual(Alerta.objects.count(), 1)

    @mock.patch('apps.alerts.tasks.send_push_notification.delay')
    def test_battery_above_threshold_no_alert(self, mock_delay):
        posicion = self._create_position(bateria=80)

        result = evaluar_bateria(posicion.id_posicion)

        self.assertEqual(result, 'battery ok')
        self.assertFalse(Alerta.objects.exists())
        mock_delay.assert_not_called()

    @mock.patch('apps.alerts.tasks.send_push_notification.delay')
    def test_battery_none_no_alert(self, mock_delay):
        posicion = self._create_position(bateria=None)

        result = evaluar_bateria(posicion.id_posicion)

        self.assertEqual(result, 'battery ok')
        self.assertFalse(Alerta.objects.exists())

    @mock.patch('apps.alerts.tasks.send_push_notification.delay')
    def test_dedup_within_window(self, mock_delay):
        first = self._create_position(bateria=10)
        second = self._create_position(bateria=8)

        evaluar_bateria(first.id_posicion)
        result = evaluar_bateria(second.id_posicion)

        self.assertEqual(result, 'battery alert deduped')
        self.assertEqual(Alerta.objects.count(), 1)
        mock_delay.assert_called_once()
