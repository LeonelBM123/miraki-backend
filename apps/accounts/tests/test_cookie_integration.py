from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import BitacoraAcceso
from apps.audit.models import Bitacora
from apps.children.models import Nino


class CookieAuthIntegrationTests(APITestCase):
    def test_full_tutor_cookie_flow(self):
        register = self.client.post('/api/v1/auth/register/', {
            'correo': 'flow@example.com',
            'password': 'StrongPass123!',
            'confirmar_password': 'StrongPass123!',
            'tipo_cuenta': 'tutor',
            'nombre': 'Tutor Flow',
            'telefono': '70000009',
        }, format='json')
        self.assertEqual(register.status_code, status.HTTP_201_CREATED)

        login = self.client.post('/api/v1/auth/login/', {
            'correo': 'flow@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, login.cookies)
        self.assertIn(settings.JWT_REFRESH_COOKIE_NAME, login.cookies)

        me = self.client.get('/api/v1/auth/me/')
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data['correo'], 'flow@example.com')

        create = self.client.post('/api/v1/children/ninos/', {'nombre': 'Flow Kid'}, format='json')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        nino_id = create.data['id_nino']

        list_response = self.client.get('/api/v1/children/ninos/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        patch = self.client.patch(f'/api/v1/children/ninos/{nino_id}/', {'nombre': 'Flow Kid Editado'}, format='json')
        self.assertEqual(patch.status_code, status.HTTP_200_OK)

        deactivate = self.client.post(f'/api/v1/children/ninos/{nino_id}/deactivate/')
        self.assertEqual(deactivate.status_code, status.HTTP_200_OK)

        reactivate = self.client.post(f'/api/v1/children/ninos/{nino_id}/reactivate/')
        self.assertEqual(reactivate.status_code, status.HTTP_200_OK)

        refresh = self.client.post('/api/v1/auth/refresh/', {}, format='json')
        self.assertEqual(refresh.status_code, status.HTTP_200_OK)
        self.assertIn(settings.JWT_ACCESS_COOKIE_NAME, refresh.cookies)

        logout = self.client.post('/api/v1/auth/logout/', {}, format='json')
        self.assertEqual(logout.status_code, status.HTTP_200_OK)
        self.client.cookies.clear()
        after_logout = self.client.get('/api/v1/auth/me/')
        self.assertEqual(after_logout.status_code, status.HTTP_401_UNAUTHORIZED)

        self.assertTrue(Nino.objects.filter(id_nino=nino_id, nombre='Flow Kid Editado', activo=True).exists())
        self.assertGreaterEqual(Bitacora.objects.filter(tabla_afectada='nino').count(), 4)
        self.assertEqual(BitacoraAcceso.objects.filter(tipo_evento='login_exitoso').count(), 1)
        self.assertEqual(BitacoraAcceso.objects.filter(tipo_evento='logout').count(), 1)
