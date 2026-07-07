from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Rol, Tutor
from apps.audit.models import Bitacora
from apps.children.models import Nino

Usuario = get_user_model()


class NinoFlowTests(APITestCase):
    def setUp(self):
        rol_tutor = Rol.objects.get(nombre_rol='Tutor')
        rol_admin = Rol.objects.get(nombre_rol='AdminCentro')
        self.user_a = Usuario.objects.create_user('a@example.com', 'StrongPass123!', id_rol=rol_tutor)
        self.user_b = Usuario.objects.create_user('b@example.com', 'StrongPass123!', id_rol=rol_tutor)
        self.admin = Usuario.objects.create_user('admin@example.com', 'StrongPass123!', id_rol=rol_admin)
        self.tutor_a = Tutor.objects.create(id_usuario=self.user_a, nombre='Tutor A', telefono='70000001')
        self.tutor_b = Tutor.objects.create(id_usuario=self.user_b, nombre='Tutor B', telefono='70000002')

    def test_tutor_creates_lists_updates_deactivates_and_reactivates_nino(self):
        self.client.force_authenticate(self.user_a)
        create = self.client.post('/api/v1/children/ninos/', {
            'nombre': 'Mateo',
            'fecha_nacimiento': '2018-05-20',
            'foto_url': '',
        }, format='json')

        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        nino = Nino.objects.get(nombre='Mateo')
        self.assertEqual(nino.id_tutor, self.tutor_a)
        self.assertTrue(nino.activo)
        self.assertEqual(Bitacora.objects.filter(tabla_afectada='nino', operacion='INSERT').count(), 1)

        list_response = self.client.get('/api/v1/children/ninos/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        results = list_response.data['results'] if isinstance(list_response.data, dict) else list_response.data
        self.assertEqual(len(results), 1)

        patch = self.client.patch(f'/api/v1/children/ninos/{nino.pk}/', {'nombre': 'Mateo Editado'}, format='json')
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertEqual(nino.nombre, 'Mateo Editado')

        deactivate = self.client.post(f'/api/v1/children/ninos/{nino.pk}/deactivate/')
        self.assertEqual(deactivate.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertFalse(nino.activo)

        default_list = self.client.get('/api/v1/children/ninos/')
        default_results = default_list.data['results'] if isinstance(default_list.data, dict) else default_list.data
        self.assertEqual(len(default_results), 0)

        reactivate = self.client.post(f'/api/v1/children/ninos/{nino.pk}/reactivate/')
        self.assertEqual(reactivate.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertTrue(nino.activo)
        self.assertGreaterEqual(Bitacora.objects.filter(tabla_afectada='nino', operacion='UPDATE').count(), 3)

    def test_admin_centro_cannot_create_nino(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/v1/children/ninos/', {'nombre': 'Nope'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_future_birthdate_is_rejected_and_tutor_injection_is_ignored(self):
        self.client.force_authenticate(self.user_a)
        future = timezone.localdate() + timezone.timedelta(days=1)
        invalid = self.client.post('/api/v1/children/ninos/', {
            'nombre': 'Futuro',
            'fecha_nacimiento': future.isoformat(),
        }, format='json')
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        injected = self.client.post('/api/v1/children/ninos/', {
            'nombre': 'Seguro',
            'id_tutor': self.tutor_b.pk,
        }, format='json')
        self.assertEqual(injected.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Nino.objects.get(nombre='Seguro').id_tutor, self.tutor_a)

    def test_tutor_cannot_infer_or_modify_other_tutor_nino(self):
        own = Nino.objects.create(id_tutor=self.tutor_a, nombre='Propio')
        other = Nino.objects.create(id_tutor=self.tutor_b, nombre='Ajeno')

        self.client.force_authenticate(self.user_a)
        list_response = self.client.get('/api/v1/children/ninos/')
        results = list_response.data['results'] if isinstance(list_response.data, dict) else list_response.data
        self.assertEqual([item['id_nino'] for item in results], [own.pk])

        self.assertEqual(self.client.get(f'/api/v1/children/ninos/{other.pk}/').status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.patch(f'/api/v1/children/ninos/{other.pk}/', {'nombre': 'Hack'}, format='json').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(f'/api/v1/children/ninos/{other.pk}/deactivate/').status_code,
            status.HTTP_404_NOT_FOUND,
        )
