from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import RequestFactory, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import BitacoraAcceso, Rol, Tutor
from apps.accounts.services.registration import register_account
from apps.audit.models import Bitacora
from apps.institutions.models import AdminCentro, CentroEducativo

Usuario = get_user_model()


class RegisterAccountTests(APITestCase):
    def test_register_tutor_creates_user_profile_and_audit_without_tokens(self):
        response = self.client.post('/api/v1/auth/register/', {
            'correo': 'tutor@example.com',
            'password': 'StrongPass123!',
            'confirmar_password': 'StrongPass123!',
            'tipo_cuenta': 'tutor',
            'nombre': 'Tutor Uno',
            'telefono': '70000000',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        usuario = Usuario.objects.get(correo='tutor@example.com')
        self.assertEqual(usuario.id_rol.nombre_rol, 'Tutor')
        self.assertTrue(Tutor.objects.filter(id_usuario=usuario, nombre='Tutor Uno').exists())
        self.assertEqual(Bitacora.objects.filter(tabla_afectada='usuario').count(), 1)
        self.assertEqual(Bitacora.objects.filter(tabla_afectada='tutor').count(), 1)

    def test_register_admin_centro_creates_center_admin_and_audit(self):
        response = self.client.post('/api/v1/auth/register/', {
            'correo': 'admincentro@example.com',
            'password': 'StrongPass123!',
            'confirmar_password': 'StrongPass123!',
            'tipo_cuenta': 'admin_centro',
            'nombre': 'Admin Centro',
            'telefono': '70000001',
            'centro': {
                'nombre': 'Centro Uno',
                'direccion': 'Av. Siempre Viva',
            },
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        usuario = Usuario.objects.get(correo='admincentro@example.com')
        self.assertEqual(usuario.id_rol.nombre_rol, 'AdminCentro')
        centro = CentroEducativo.objects.get(nombre='Centro Uno')
        self.assertTrue(AdminCentro.objects.filter(id_usuario=usuario, id_centro=centro).exists())
        self.assertEqual(Bitacora.objects.filter(tabla_afectada='centro_educativo').count(), 1)
        self.assertEqual(Bitacora.objects.filter(tabla_afectada='admin_centro').count(), 1)

    def test_register_rejects_superadmin_and_invalid_data(self):
        response = self.client.post('/api/v1/auth/register/', {
            'correo': 'super@example.com',
            'password': 'StrongPass123!',
            'confirmar_password': 'StrongPass123!',
            'tipo_cuenta': 'SuperAdmin',
            'nombre': 'Super',
            'telefono': '70000002',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Usuario.objects.filter(correo='super@example.com').exists())

    def test_register_rejects_duplicate_email_case_insensitive_and_password_mismatch(self):
        rol = Rol.objects.get(nombre_rol='Tutor')
        Usuario.objects.create_user(correo='dup@example.com', password='StrongPass123!', id_rol=rol)

        duplicate = self.client.post('/api/v1/auth/register/', {
            'correo': 'DUP@example.com',
            'password': 'StrongPass123!',
            'confirmar_password': 'StrongPass123!',
            'tipo_cuenta': 'tutor',
            'nombre': 'Tutor',
            'telefono': '70000003',
        }, format='json')
        mismatch = self.client.post('/api/v1/auth/register/', {
            'correo': 'new@example.com',
            'password': 'StrongPass123!',
            'confirmar_password': 'OtherPass123!',
            'tipo_cuenta': 'tutor',
            'nombre': 'Tutor',
            'telefono': '70000003',
        }, format='json')

        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_admin_centro_requires_center_and_address(self):
        response = self.client.post('/api/v1/auth/register/', {
            'correo': 'admin-no-center@example.com',
            'password': 'StrongPass123!',
            'confirmar_password': 'StrongPass123!',
            'tipo_cuenta': 'admin_centro',
            'nombre': 'Admin',
            'telefono': '70000004',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RegistrationServiceTransactionTests(TestCase):
    def test_register_tutor_rolls_back_when_audit_fails(self):
        request = RequestFactory().post('/api/v1/auth/register/')
        data = {
            'correo': 'rollback@example.com',
            'password': 'StrongPass123!',
            'tipo_cuenta': 'tutor',
            'nombre': 'Rollback',
            'telefono': '70000005',
        }

        with patch('apps.accounts.services.registration.record_action', side_effect=RuntimeError('audit fail')):
            with self.assertRaises(RuntimeError):
                register_account(data=data, request=request)

        self.assertFalse(Usuario.objects.filter(correo='rollback@example.com').exists())
        self.assertFalse(Tutor.objects.filter(nombre='Rollback').exists())


class LoginLogoutTests(APITestCase):
    def setUp(self):
        self.rol = Rol.objects.get(nombre_rol='Tutor')
        self.usuario = Usuario.objects.create_user(
            correo='login@example.com',
            password='StrongPass123!',
            id_rol=self.rol,
        )

    def test_login_success_sets_httponly_cookies_without_exposing_tokens(self):
        response = self.client.post('/api/v1/auth/login/', {
            'correo': 'login@example.com',
            'password': 'StrongPass123!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertEqual(response.data['usuario']['rol'], 'Tutor')
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(settings.JWT_REFRESH_COOKIE_NAME, response.cookies)
        self.assertTrue(response.cookies[settings.JWT_ACCESS_COOKIE_NAME]['httponly'])
        self.assertTrue(response.cookies[settings.JWT_REFRESH_COOKIE_NAME]['httponly'])
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 0)
        self.assertIsNone(self.usuario.bloqueado_hasta)
        self.assertEqual(BitacoraAcceso.objects.filter(tipo_evento='login_exitoso').count(), 1)

    def test_failed_login_counts_attempts_and_blocks_on_fifth_attempt(self):
        for attempt in range(1, 6):
            response = self.client.post('/api/v1/auth/login/', {
                'correo': 'login@example.com',
                'password': 'WrongPass123!',
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.usuario.refresh_from_db()
            self.assertEqual(self.usuario.intentos_fallidos, attempt)

        self.assertIsNotNone(self.usuario.bloqueado_hasta)
        self.assertEqual(BitacoraAcceso.objects.filter(tipo_evento='login_fallido').count(), 5)

    def test_login_rejected_while_blocked_and_success_after_time_clears_lock(self):
        self.usuario.intentos_fallidos = 5
        self.usuario.bloqueado_hasta = timezone.now() + timezone.timedelta(minutes=15)
        self.usuario.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])

        blocked = self.client.post('/api/v1/auth/login/', {
            'correo': 'login@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(blocked.status_code, status.HTTP_401_UNAUTHORIZED)

        self.usuario.bloqueado_hasta = timezone.now() - timezone.timedelta(minutes=1)
        self.usuario.save(update_fields=['bloqueado_hasta'])
        success = self.client.post('/api/v1/auth/login/', {
            'correo': 'login@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(success.status_code, status.HTTP_200_OK)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 0)
        self.assertIsNone(self.usuario.bloqueado_hasta)

    def test_missing_email_login_is_audited_without_user(self):
        response = self.client.post('/api/v1/auth/login/', {
            'correo': 'missing@example.com',
            'password': 'StrongPass123!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        log = BitacoraAcceso.objects.get(correo_intento='missing@example.com')
        self.assertIsNone(log.id_usuario)

    def test_logout_blacklists_refresh_and_audits(self):
        refresh = RefreshToken.for_user(self.usuario)
        self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(refresh.access_token)
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = str(refresh)

        response = self.client.post('/api/v1/auth/logout/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BlacklistedToken.objects.count(), 1)
        self.assertEqual(BitacoraAcceso.objects.filter(tipo_evento='logout', id_usuario=self.usuario).count(), 1)
        self.assertEqual(response.cookies[settings.JWT_ACCESS_COOKIE_NAME].value, '')
        self.assertEqual(response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value, '')

    def test_me_requires_access_cookie_and_returns_public_user(self):
        anonymous = self.client.get('/api/v1/auth/me/')
        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(self.usuario)
        self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(refresh.access_token)
        response = self.client.get('/api/v1/auth/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'id_usuario': self.usuario.id_usuario,
            'correo': 'login@example.com',
            'rol': 'Tutor',
        })

    def test_refresh_uses_refresh_cookie_and_rotates_cookies(self):
        refresh = RefreshToken.for_user(self.usuario)
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = str(refresh)

        response = self.client.post('/api/v1/auth/refresh/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Token renovado correctamente.')
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)
        self.assertIn(settings.JWT_REFRESH_COOKIE_NAME, response.cookies)

    def test_refresh_without_cookie_returns_401(self):
        response = self.client.post('/api/v1/auth/refresh/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cookie_authenticated_mutation_requires_csrf_when_checks_are_enforced(self):
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_response = csrf_client.get('/api/v1/auth/csrf/')
        csrf_token = csrf_response.cookies['csrftoken'].value

        missing_csrf = csrf_client.post('/api/v1/auth/login/', {
            'correo': 'login@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(missing_csrf.status_code, status.HTTP_403_FORBIDDEN)

        login = csrf_client.post('/api/v1/auth/login/', {
            'correo': 'login@example.com',
            'password': 'StrongPass123!',
        }, format='json', HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(login.status_code, status.HTTP_200_OK)

        without_header = csrf_client.post('/api/v1/auth/logout/', {}, format='json')
        self.assertEqual(without_header.status_code, status.HTTP_403_FORBIDDEN)

        logout = csrf_client.post('/api/v1/auth/logout/', {}, format='json', HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(logout.status_code, status.HTTP_200_OK)


class SuperuserTests(TestCase):
    def test_create_superuser_assigns_superadmin_role_and_flags(self):
        usuario = Usuario.objects.create_superuser(correo='root@example.com', password='StrongPass123!')

        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.is_superuser)
        self.assertEqual(usuario.id_rol.nombre_rol, 'SuperAdmin')
