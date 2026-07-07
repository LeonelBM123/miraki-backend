from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import BitacoraAcceso, Rol
from apps.audit.models import Bitacora

Usuario = get_user_model()


class AuditPermissionTests(APITestCase):
    def setUp(self):
        self.super_role = Rol.objects.get(nombre_rol='SuperAdmin')
        self.tutor_role = Rol.objects.get(nombre_rol='Tutor')
        self.superuser = Usuario.objects.create_user(
            correo='super@example.com',
            password='StrongPass123!',
            id_rol=self.super_role,
            is_staff=True,
            is_superuser=True,
        )
        self.tutor = Usuario.objects.create_user(
            correo='tutor-audit@example.com',
            password='StrongPass123!',
            id_rol=self.tutor_role,
        )
        Bitacora.objects.create(tabla_afectada='nino', id_registro='1', operacion='INSERT', id_usuario=self.tutor)
        BitacoraAcceso.objects.create(correo_intento='x@example.com', tipo_evento='login_fallido')

    def test_only_superadmin_can_read_general_and_access_audit(self):
        self.client.force_authenticate(self.tutor)
        self.assertEqual(self.client.get('/api/v1/audit/bitacora/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.get('/api/v1/accounts/bitacora-accesos/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.client.force_authenticate(self.superuser)
        self.assertEqual(self.client.get('/api/v1/audit/bitacora/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get('/api/v1/accounts/bitacora-accesos/').status_code, status.HTTP_200_OK)

    def test_cookie_auth_preserves_audit_permissions(self):
        tutor_refresh = RefreshToken.for_user(self.tutor)
        self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(tutor_refresh.access_token)
        self.assertEqual(self.client.get('/api/v1/audit/bitacora/').status_code, status.HTTP_403_FORBIDDEN)

        self.client.cookies.clear()
        super_refresh = RefreshToken.for_user(self.superuser)
        self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(super_refresh.access_token)
        self.assertEqual(self.client.get('/api/v1/audit/bitacora/').status_code, status.HTTP_200_OK)
