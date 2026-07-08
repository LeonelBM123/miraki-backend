from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.authentication import PairingTokenAuthentication
from apps.accounts.models import Tutor
from apps.children.models import Nino

from ..models import CodigoPareo

Usuario = get_user_model()


class PairingCodeCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario_tutor = Usuario.objects.create_user(
            correo='tutor@example.com',
            password='Secr3t-pass',
        )
        self.tutor = Tutor.objects.create(
            id_usuario=self.usuario_tutor,
            nombre='Tutor Prueba',
            telefono='3001234567',
        )
        self.nino = Nino.objects.create(
            nombre='Ana',
            id_tutor=self.tutor,
        )

        self.otro_usuario = Usuario.objects.create_user(
            correo='otro@example.com',
            password='Secr3t-pass',
        )
        self.otro_tutor = Tutor.objects.create(
            id_usuario=self.otro_usuario,
            nombre='Otro Tutor',
            telefono='3007654321',
        )
        self.otro_nino = Nino.objects.create(
            nombre='Luis',
            id_tutor=self.otro_tutor,
        )

    def test_crear_codigo_como_tutor(self):
        self.client.force_authenticate(user=self.usuario_tutor)

        response = self.client.post('/api/v1/pareo/crear/', {'id_nino': self.nino.id_nino}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['codigo']), 6)
        self.assertTrue(response.data['codigo'].isalnum())
        self.assertEqual(response.data['codigo'], response.data['codigo'].upper())
        self.assertEqual(CodigoPareo.objects.count(), 1)
        codigo = CodigoPareo.objects.get()
        self.assertEqual(codigo.id_nino, self.nino)
        self.assertEqual(codigo.id_tutor, self.usuario_tutor)
        self.assertFalse(codigo.usado)

    def test_crear_codigo_sin_auth(self):
        response = self.client.post('/api/v1/pareo/crear/', {'id_nino': self.nino.id_nino}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_crear_codigo_de_otro_hijo_rechazado(self):
        self.client.force_authenticate(user=self.usuario_tutor)

        response = self.client.post('/api/v1/pareo/crear/', {'id_nino': self.otro_nino.id_nino}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CodigoPareo.objects.count(), 0)


class PairingDeviceLinkTests(TestCase):
    def setUp(self):
        # El endpoint de vinculación usa AnonRateThrottle; la caché de throttle es
        # compartida entre tests, así que la limpiamos para no acumular 429.
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.usuario_tutor = Usuario.objects.create_user(
            correo='tutor@example.com',
            password='Secr3t-pass',
        )
        self.tutor = Tutor.objects.create(
            id_usuario=self.usuario_tutor,
            nombre='Tutor Prueba',
            telefono='3001234567',
        )
        self.nino = Nino.objects.create(
            nombre='Ana',
            id_tutor=self.tutor,
        )

    def create_pairing_code(self, codigo='ABC123', used=False, expires_at=None):
        return CodigoPareo.objects.create(
            codigo=codigo,
            id_nino=self.nino,
            id_tutor=self.usuario_tutor,
            expira_en=expires_at or (timezone.now() + timedelta(minutes=30)),
            usado=used,
        )

    def test_vincular_codigo_valido(self):
        codigo = self.create_pairing_code()

        response = self.client.post('/api/v1/pareo/vincular/', {'codigo': codigo.codigo}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['id_nino'], self.nino.id_nino)
        self.assertEqual(response.data['nombre'], 'Ana')
        self.assertEqual(response.data['tutor_nombre'], 'Tutor Prueba')
        access = AccessToken(response.data['token'])
        self.assertEqual(access['nino_id'], self.nino.id_nino)
        self.assertEqual(access['tutor_id'], self.usuario_tutor.id_usuario)
        self.assertEqual(access['scope'], 'kid_device')
        codigo.refresh_from_db()
        self.assertTrue(codigo.usado)

    def test_vincular_codigo_expirado(self):
        codigo = self.create_pairing_code(expires_at=timezone.now() - timedelta(minutes=1))

        response = self.client.post('/api/v1/pareo/vincular/', {'codigo': codigo.codigo}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        codigo.refresh_from_db()
        self.assertFalse(codigo.usado)

    def test_vincular_codigo_usado(self):
        codigo = self.create_pairing_code(used=True)

        response = self.client.post('/api/v1/pareo/vincular/', {'codigo': codigo.codigo}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        codigo.refresh_from_db()
        self.assertTrue(codigo.usado)

    def test_vincular_codigo_desconocido(self):
        response = self.client.post('/api/v1/pareo/vincular/', {'codigo': 'ZZZZ99'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vincular_sin_codigo(self):
        response = self.client.post('/api/v1/pareo/vincular/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PairingTokenAuthenticationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.usuario_tutor = Usuario.objects.create_user(
            correo='tutor@example.com',
            password='Secr3t-pass',
        )
        self.tutor = Tutor.objects.create(
            id_usuario=self.usuario_tutor,
            nombre='Tutor Prueba',
            telefono='3001234567',
        )
        self.nino = Nino.objects.create(
            nombre='Ana',
            id_tutor=self.tutor,
        )

    def build_token(self, scope='kid_device'):
        token = AccessToken()
        token['nino_id'] = self.nino.id_nino
        token['tutor_id'] = self.usuario_tutor.id_usuario
        token['scope'] = scope
        return str(token)

    def test_pairing_token_authentication(self):
        request = self.factory.get('/api/v1/pareo/estado/1/', HTTP_X_KID_TOKEN=self.build_token())

        user, raw_token = PairingTokenAuthentication().authenticate(request)

        self.assertEqual(user, self.nino)
        self.assertEqual(raw_token, request.headers['X-Kid-Token'])

    def test_pairing_token_missing_scope(self):
        request = self.factory.get('/api/v1/pareo/estado/1/', HTTP_X_KID_TOKEN=self.build_token(scope='other'))

        self.assertIsNone(PairingTokenAuthentication().authenticate(request))

    def test_pairing_token_wrong_header(self):
        request = self.factory.get('/api/v1/pareo/estado/1/', HTTP_AUTHORIZATION=f'Bearer {self.build_token()}')

        self.assertIsNone(PairingTokenAuthentication().authenticate(request))
