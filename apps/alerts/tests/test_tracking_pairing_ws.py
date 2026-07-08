from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Rol, Tutor, Usuario
from apps.children.models import Nino
from config.asgi import application


TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class TrackingConsumerPairingTokenTests(TransactionTestCase):
    # TransactionTestCase: los consumers async no conviven bien con la única
    # transacción atómica de TestCase (deja la conexión de BD cerrada entre clases).
    def setUp(self):
        self.rol_tutor, _ = Rol.objects.get_or_create(nombre_rol='Tutor', defaults={'descripcion': 'Tutor'})
        self.usuario = Usuario.objects.create_user(
            correo='pairing-tutor@example.com',
            password='Secr3t-pass',
            id_rol=self.rol_tutor,
        )
        self.tutor = Tutor.objects.create(
            id_usuario=self.usuario,
            nombre='Tutor Pairing',
            telefono='3001234567',
        )
        self.nino = Nino.objects.create(nombre='Ana', id_tutor=self.tutor, activo=True)

    def build_pairing_token(self, scope='kid_device'):
        token = AccessToken()
        token['nino_id'] = self.nino.id_nino
        token['tutor_id'] = self.usuario.id_usuario
        token['scope'] = scope
        return str(token)

    def _connect(self, token):
        async def run():
            communicator = WebsocketCommunicator(application, f'/ws/tracking/?token={token}')
            connected, detail = await communicator.connect()
            if connected:
                await communicator.disconnect()
            return connected, detail

        return async_to_sync(run)()

    def test_ws_consumer_accepts_pairing_token(self):
        connected, detail = self._connect(self.build_pairing_token())

        self.assertTrue(connected)
        self.assertIsNone(detail)

    def test_ws_consumer_rejects_invalid_token(self):
        connected, close_code = self._connect('bad-token')

        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)
