from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

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
