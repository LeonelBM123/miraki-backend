from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Rol, Tutor
from apps.alerts.models import Alerta, Posicion
from apps.alerts.tasks import evaluar_zonas
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo
from apps.zones.models import NinoZonaSegura, ZonaSegura

Usuario = get_user_model()


class EvaluarZonasTaskTests(TestCase):
    def setUp(self):
        self.rol_tutor, _ = Rol.objects.get_or_create(
            nombre_rol='Tutor',
            defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'},
        )
        self.usuario = Usuario.objects.create_user(
            correo='tutor-zonas@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )
        self.tutor = Tutor.objects.create(id_usuario=self.usuario, nombre='Tutor Zonas', telefono='70000010')
        self.nino = Nino.objects.create(id_tutor=self.tutor, nombre='Sofía')
        self.dispositivo = Dispositivo.objects.create(
            id_nino=self.nino,
            imei='864209876543210',
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
        self.zona = ZonaSegura.objects.create(
            nombre='Zona Central',
            poligono=poligono,
            id_tutor_propietario=self.tutor,
            activo=True,
        )
        NinoZonaSegura.objects.create(id_nino=self.nino, id_zona=self.zona, activa=True)

    def _create_position(self, *, latitud, longitud, minutos_atras=0):
        return Posicion.objects.create(
            id_dispositivo=self.dispositivo,
            latitud=str(latitud),
            longitud=str(longitud),
            ubicacion=Point(longitud, latitud, srid=4326),
            velocidad='12.34',
            fecha_posicion=timezone.now() - timezone.timedelta(minutes=minutos_atras),
        )

    @mock.patch('apps.alerts.tasks.send_push_notification.delay')
    def test_child_outside_zone_creates_alert(self, mock_delay):
        posicion = self._create_position(latitud=-16.550000, longitud=-68.250000)

        result = evaluar_zonas()

        self.assertEqual(result, '1 alerts created')
        alerta = Alerta.objects.get()
        self.assertEqual(alerta.id_nino, self.nino)
        self.assertEqual(alerta.id_zona, self.zona)
        self.assertEqual(alerta.id_posicion, posicion)
        mock_delay.assert_called_once_with(alerta.id_alerta)

    @mock.patch('apps.alerts.tasks.send_push_notification.delay')
    def test_child_inside_zone_no_alert(self, mock_delay):
        self._create_position(latitud=-16.450000, longitud=-68.150000)

        result = evaluar_zonas()

        self.assertEqual(result, '0 alerts created')
        self.assertFalse(Alerta.objects.exists())
        mock_delay.assert_not_called()

    @mock.patch('apps.alerts.tasks.send_push_notification.delay')
    def test_no_duplicate_within_10min(self, mock_delay):
        self._create_position(latitud=-16.550000, longitud=-68.250000)

        first = evaluar_zonas()
        second = evaluar_zonas()

        self.assertEqual(first, '1 alerts created')
        self.assertEqual(second, '0 alerts created')
        self.assertEqual(Alerta.objects.count(), 1)
        mock_delay.assert_called_once()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @mock.patch('apps.alerts.tasks.send_push_notification.delay')
    def test_skipped_if_always_eager(self, mock_delay):
        self._create_position(latitud=-16.550000, longitud=-68.250000)

        result = evaluar_zonas()

        self.assertEqual(result, '1 alerts created')
        self.assertEqual(Alerta.objects.count(), 1)
        mock_delay.assert_not_called()
