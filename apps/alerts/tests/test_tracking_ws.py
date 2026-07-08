from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Rol, Usuario
from config.asgi import application


TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class TrackingConsumerTests(TestCase):
    def setUp(self):
        self.rol_tutor = Rol.objects.create(nombre_rol='Tutor', descripcion='Tutor')
        self.usuario = Usuario.objects.create_user(
            correo='tutor@example.com',
            password='Secr3t-pass',
            id_rol=self.rol_tutor,
        )
        self.token = str(AccessToken.for_user(self.usuario))

    def _connect(self, path):
        async def run():
            communicator = WebsocketCommunicator(application, path)
            connected, detail = await communicator.connect()
            if connected:
                await communicator.disconnect()
            return connected, detail

        return async_to_sync(run)()

    def _receive_position_update(self):
        async def run():
            communicator = WebsocketCommunicator(
                application,
                f'/ws/tracking/?token={self.token}',
            )
            connected, detail = await communicator.connect()
            self.assertTrue(connected, detail)

            try:
                payload = {
                    'type': 'posicion_update',
                    'child_id': 7,
                    'nombre': 'Luis',
                    'latitud': '-16.5',
                    'longitud': '-68.15',
                    'velocidad': '12.3',
                    'bateria': 81,
                    'fecha_posicion': '2026-07-07T10:00:00Z',
                }
                await communicator.send_json_to(payload)
                return await communicator.receive_json_from()
            finally:
                await communicator.disconnect()

        return async_to_sync(run)()

    def test_connect_with_valid_token(self):
        connected, detail = self._connect(f'/ws/tracking/?token={self.token}')

        self.assertTrue(connected)
        self.assertIsNone(detail)

    def test_connect_without_token_4401(self):
        connected, close_code = self._connect('/ws/tracking/')

        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    def test_connect_invalid_token_4401(self):
        connected, close_code = self._connect('/ws/tracking/?token=bad-token')

        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    def test_receive_posicion_update_broadcast(self):
        response = self._receive_position_update()

        self.assertEqual(response['type'], 'position')
        self.assertEqual(response['child_id'], 7)
        self.assertEqual(response['nombre'], 'Luis')
        self.assertEqual(response['latitud'], '-16.5')
        self.assertEqual(response['longitud'], '-68.15')
        self.assertEqual(response['velocidad'], '12.3')
        self.assertEqual(response['bateria'], 81)
        self.assertEqual(response['fecha_posicion'], '2026-07-07T10:00:00Z')
