from datetime import timedelta
from unittest import mock
from uuid import UUID

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient, APIRequestFactory

from config.settings import base as base_settings

from .models import BitacoraAcceso, Rol
from .serializers import BitacoraTokenObtainPairSerializer, UsuarioSerializer
from .views import LoginView, RegisterView

Usuario = get_user_model()


class SecuritySettingsTests(SimpleTestCase):
    def test_rest_framework_throttle_and_logging_config(self):
        self.assertEqual(
            base_settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'],
            {'anon': '5/min', 'user': '100/hour', 'auth': '10/min'},
        )
        self.assertIn('rest_framework.throttling.ScopedRateThrottle', base_settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'])
        self.assertEqual(base_settings.LOGGING['loggers']['auth']['handlers'], ['auth_file'])
        self.assertEqual(base_settings.LOGGING['handlers']['auth_file']['class'], 'config.settings.base.EnsuringRotatingFileHandler')

    def test_auth_views_use_auth_throttle_scope(self):
        self.assertEqual(LoginView.throttle_scope, 'auth')
        self.assertEqual(RegisterView.throttle_scope, 'auth')


class BitacoraTokenObtainPairSerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.rol = Rol.objects.create(nombre_rol='Tutor', descripcion='Tutor')
        self.usuario = Usuario.objects.create_user(
            correo='tutor@example.com',
            password='Secr3t-pass',
            id_rol=self.rol,
        )

    def build_serializer(self, correo, password):
        request = self.factory.post('/api/auth/login/', HTTP_USER_AGENT='pytest')
        return BitacoraTokenObtainPairSerializer(
            data={'correo': correo, 'password': password},
            context={'request': request},
        )

    def test_validate_resets_lockout_state_and_logs_success(self):
        self.usuario.intentos_fallidos = 3
        self.usuario.bloqueado_hasta = timezone.now() - timedelta(minutes=1)
        self.usuario.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])

        serializer = self.build_serializer('tutor@example.com', 'Secr3t-pass')
        data = serializer.validate({'correo': 'tutor@example.com', 'password': 'Secr3t-pass'})

        self.assertIn('access', data)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 0)
        self.assertIsNone(self.usuario.bloqueado_hasta)
        self.assertEqual(BitacoraAcceso.objects.filter(tipo_evento='login_exitoso').count(), 1)

    def test_validate_increments_attempts_and_locks_after_five_failures(self):
        for _ in range(5):
            serializer = self.build_serializer('tutor@example.com', 'wrong-password')
            with self.assertRaises(AuthenticationFailed):
                serializer.validate({'correo': 'tutor@example.com', 'password': 'wrong-password'})

        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 5)
        self.assertIsNotNone(self.usuario.bloqueado_hasta)
        self.assertGreater(self.usuario.bloqueado_hasta, timezone.now())
        self.assertEqual(BitacoraAcceso.objects.filter(tipo_evento='login_fallido').count(), 5)

    def test_locked_account_short_circuits_before_authentication(self):
        self.usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=10)
        self.usuario.save(update_fields=['bloqueado_hasta'])

        serializer = self.build_serializer('tutor@example.com', 'Secr3t-pass')

        with mock.patch('rest_framework_simplejwt.serializers.TokenObtainPairSerializer.validate', side_effect=AssertionError('super().validate() should not run')):
            with self.assertRaises(AuthenticationFailed):
                serializer.validate({'correo': 'tutor@example.com', 'password': 'Secr3t-pass'})

        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 0)


class UsuarioSerializerAndPublicIdTests(TestCase):
    def setUp(self):
        self.rol = Rol.objects.create(nombre_rol='Tutor', descripcion='Tutor')
        self.usuario = Usuario.objects.create_user(
            correo='tutor1@example.com',
            password='Secr3t-pass',
            id_rol=self.rol,
        )

    def test_usuario_serializer_exposes_public_id_and_hides_internal_pk(self):
        data = UsuarioSerializer(self.usuario).data

        self.assertNotIn('id_usuario', data)
        self.assertNotIn('intentos_fallidos', data)
        self.assertNotIn('bloqueado_hasta', data)
        self.assertEqual(data['public_id'], str(self.usuario.public_id))

    def test_public_id_is_unique_and_lookup_works(self):
        otro_usuario = Usuario.objects.create_user(
            correo='tutor2@example.com',
            password='Secr3t-pass',
            id_rol=self.rol,
        )

        self.assertIsInstance(self.usuario.public_id, UUID)
        self.assertIsInstance(otro_usuario.public_id, UUID)
        self.assertNotEqual(self.usuario.public_id, otro_usuario.public_id)
        self.assertEqual(Usuario.objects.get_by_public_id(self.usuario.public_id), self.usuario)


class MeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.rol = Rol.objects.create(nombre_rol='Tutor', descripcion='Tutor')
        self.usuario = Usuario.objects.create_user(
            correo='me@example.com',
            password='Secr3t-pass',
            id_rol=self.rol,
        )

    def test_me_returns_authenticated_user(self):
        self.client.force_authenticate(user=self.usuario)

        response = self.client.get('/api/v1/accounts/me/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['correo'], 'me@example.com')
        self.assertEqual(response.data['nombre_rol'], 'Tutor')
