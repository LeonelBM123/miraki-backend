from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Rol, Tutor
from apps.audit.models import Bitacora
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo

Usuario = get_user_model()


class DispositivoFlowTests(APITestCase):
    def setUp(self):
        rol_tutor = Rol.objects.get(nombre_rol='Tutor')
        self.user = Usuario.objects.create_user('tutor-device@example.com', 'StrongPass123!', id_rol=rol_tutor)
        self.tutor = Tutor.objects.create(id_usuario=self.user, nombre='Tutor Dispositivo', telefono='70000003')
        self.nino = Nino.objects.create(id_tutor=self.tutor, nombre='Valentina')

    def test_tutor_links_lists_and_retrieves_device(self):
        self.client.force_authenticate(self.user)

        create = self.client.post('/api/v1/dispositivos/', {'imei': '123456789012345', 'id_nino': self.nino.pk}, format='json')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create.data['imei'], '123456789012345')
        self.assertEqual(create.data['estado_general'], 'Vinculado')

        device = Dispositivo.objects.get(imei='123456789012345')
        self.assertEqual(device.id_nino, self.nino)
        self.assertEqual(Bitacora.objects.filter(tabla_afectada='dispositivo', operacion='INSERT').count(), 1)

        list_response = self.client.get('/api/v1/dispositivos/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        retrieve = self.client.get(f'/api/v1/dispositivos/{device.pk}/')
        self.assertEqual(retrieve.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieve.data['id_nino'], self.nino.pk)

    def test_cannot_link_twice_to_same_child(self):
        self.client.force_authenticate(self.user)
        Dispositivo.objects.create(imei='111111111111111', id_nino=self.nino, estado='vinculado', activo=True)

        response = self.client.post('/api/v1/dispositivos/', {'imei': '222222222222222', 'id_nino': self.nino.pk}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('dispositivo vinculado', str(response.data).lower())
