from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Rol, Tutor
from apps.audit.models import Bitacora
from apps.children.models import Nino
from apps.institutions.models import AdminCentro, CentroEducativo
from rest_framework_simplejwt.tokens import RefreshToken

Usuario = get_user_model()


class NinoFlowTests(APITestCase):
    def setUp(self):
        rol_tutor = Rol.objects.get(nombre_rol='Tutor')
        rol_admin = Rol.objects.get(nombre_rol='AdminCentro')
        self.user_a = Usuario.objects.create_user('a@example.com', 'StrongPass123!', id_rol=rol_tutor)
        self.user_b = Usuario.objects.create_user('b@example.com', 'StrongPass123!', id_rol=rol_tutor)
        self.admin = Usuario.objects.create_user('admin@example.com', 'StrongPass123!', id_rol=rol_admin)
        self.admin_b = Usuario.objects.create_user('admin-b@example.com', 'StrongPass123!', id_rol=rol_admin)
        self.tutor_a = Tutor.objects.create(id_usuario=self.user_a, nombre='Tutor A', telefono='70000001')
        self.tutor_b = Tutor.objects.create(id_usuario=self.user_b, nombre='Tutor B', telefono='70000002')
        self.centro_a = CentroEducativo.objects.create(nombre='Centro A', direccion='Calle A')
        self.centro_b = CentroEducativo.objects.create(nombre='Centro B', direccion='Calle B')
        self.admin_centro_a = AdminCentro.objects.create(
            id_usuario=self.admin,
            id_centro=self.centro_a,
            nombre='Admin A',
            telefono='70000003',
        )
        self.admin_centro_b = AdminCentro.objects.create(
            id_usuario=self.admin_b,
            id_centro=self.centro_b,
            nombre='Admin B',
            telefono='70000004',
        )

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

    def test_cookie_authenticated_tutor_can_use_children_endpoints(self):
        refresh = RefreshToken.for_user(self.user_a)
        self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(refresh.access_token)

        response = self.client.post('/api/v1/children/ninos/', {'nombre': 'Cookie Kid'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Nino.objects.get(nombre='Cookie Kid').id_tutor, self.tutor_a)

    def test_tutor_can_assign_change_and_remove_own_nino_center(self):
        nino = Nino.objects.create(id_tutor=self.tutor_a, nombre='Mateo')
        self.client.force_authenticate(self.user_a)

        assign = self.client.post(
            f'/api/v1/children/ninos/{nino.pk}/assign-center/',
            {'centro_id': self.centro_a.pk},
            format='json',
        )
        self.assertEqual(assign.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertEqual(nino.centro, self.centro_a)
        self.assertEqual(assign.data['centro']['id_centro'], self.centro_a.pk)

        first_audit = Bitacora.objects.get(tabla_afectada='nino', operacion='UPDATE')
        self.assertEqual(first_audit.datos_anteriores, {'centro': None})
        self.assertEqual(first_audit.datos_nuevos, {'centro': self.centro_a.pk})

        change = self.client.post(
            f'/api/v1/children/ninos/{nino.pk}/assign-center/',
            {'centro_id': self.centro_b.pk},
            format='json',
        )
        self.assertEqual(change.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertEqual(nino.centro, self.centro_b)

        change_audit = Bitacora.objects.filter(tabla_afectada='nino', operacion='UPDATE').latest('id_bitacora')
        self.assertEqual(change_audit.datos_anteriores, {'centro': self.centro_a.pk})
        self.assertEqual(change_audit.datos_nuevos, {'centro': self.centro_b.pk})

        remove = self.client.post(f'/api/v1/children/ninos/{nino.pk}/remove-center/')
        self.assertEqual(remove.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertIsNone(nino.centro)

        remove_audit = Bitacora.objects.filter(tabla_afectada='nino', operacion='UPDATE').latest('id_bitacora')
        self.assertEqual(remove_audit.datos_anteriores, {'centro': self.centro_b.pk})
        self.assertEqual(remove_audit.datos_nuevos, {'centro': None})

    def test_remove_center_is_idempotent_without_duplicate_audit(self):
        nino = Nino.objects.create(id_tutor=self.tutor_a, nombre='Sin centro')
        self.client.force_authenticate(self.user_a)

        response = self.client.post(f'/api/v1/children/ninos/{nino.pk}/remove-center/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['centro'])
        self.assertFalse(Bitacora.objects.filter(tabla_afectada='nino', operacion='UPDATE').exists())

    def test_admin_centro_children_list_only_shows_own_active_center_children(self):
        visible = Nino.objects.create(id_tutor=self.tutor_a, nombre='Visible', centro=self.centro_a)
        Nino.objects.create(id_tutor=self.tutor_a, nombre='Sin Centro')
        Nino.objects.create(id_tutor=self.tutor_a, nombre='Otro Centro', centro=self.centro_b)
        Nino.objects.create(id_tutor=self.tutor_b, nombre='Inactivo', centro=self.centro_a, activo=False)

        self.client.force_authenticate(self.admin)
        response = self.client.get(f'/api/v1/institutions/children/?centro_id={self.centro_b.pk}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual([item['id_nino'] for item in response.data['results']], [visible.pk])

    def test_admin_centro_b_does_not_see_center_a_children(self):
        Nino.objects.create(id_tutor=self.tutor_a, nombre='Centro A', centro=self.centro_a)
        own = Nino.objects.create(id_tutor=self.tutor_b, nombre='Centro B', centro=self.centro_b)

        self.client.force_authenticate(self.admin_b)
        response = self.client.get('/api/v1/institutions/children/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id_nino'] for item in response.data['results']], [own.pk])

    def test_tutor_cannot_assign_or_remove_other_tutor_nino_center(self):
        other = Nino.objects.create(id_tutor=self.tutor_b, nombre='Ajeno', centro=self.centro_a)
        self.client.force_authenticate(self.user_a)

        assign = self.client.post(
            f'/api/v1/children/ninos/{other.pk}/assign-center/',
            {'centro_id': self.centro_b.pk},
            format='json',
        )
        remove = self.client.post(f'/api/v1/children/ninos/{other.pk}/remove-center/')

        self.assertEqual(assign.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(remove.status_code, status.HTTP_404_NOT_FOUND)
        other.refresh_from_db()
        self.assertEqual(other.centro, self.centro_a)

    def test_admin_centro_cannot_assign_or_remove_center(self):
        nino = Nino.objects.create(id_tutor=self.tutor_a, nombre='Mateo', centro=self.centro_a)
        self.client.force_authenticate(self.admin)

        assign = self.client.post(
            f'/api/v1/children/ninos/{nino.pk}/assign-center/',
            {'centro_id': self.centro_b.pk},
            format='json',
        )
        remove = self.client.post(f'/api/v1/children/ninos/{nino.pk}/remove-center/')

        self.assertEqual(assign.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(remove.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_user_receives_401_on_center_endpoints(self):
        nino = Nino.objects.create(id_tutor=self.tutor_a, nombre='Mateo')

        assign = self.client.post(
            f'/api/v1/children/ninos/{nino.pk}/assign-center/',
            {'centro_id': self.centro_a.pk},
            format='json',
        )
        remove = self.client.post(f'/api/v1/children/ninos/{nino.pk}/remove-center/')
        listing = self.client.get('/api/v1/institutions/children/')

        self.assertEqual(assign.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(remove.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(listing.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_assign_center_with_missing_center_is_controlled_error(self):
        nino = Nino.objects.create(id_tutor=self.tutor_a, nombre='Mateo')
        self.client.force_authenticate(self.user_a)

        response = self.client.post(
            f'/api/v1/children/ninos/{nino.pk}/assign-center/',
            {'centro_id': 999999},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('centro_id', response.data)

    def test_admin_centro_children_list_keeps_drf_pagination(self):
        for index in range(21):
            Nino.objects.create(id_tutor=self.tutor_a, nombre=f'Nino {index:02d}', centro=self.centro_a)

        self.client.force_authenticate(self.admin)
        response = self.client.get('/api/v1/institutions/children/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 21)
        self.assertIsNone(response.data['previous'])
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(len(response.data['results']), 20)

    def test_existing_nino_with_null_center_still_supports_current_operations(self):
        nino = Nino.objects.create(id_tutor=self.tutor_a, nombre='Actual')
        self.client.force_authenticate(self.user_a)

        list_response = self.client.get('/api/v1/children/ninos/')
        patch = self.client.patch(f'/api/v1/children/ninos/{nino.pk}/', {'nombre': 'Actualizado'}, format='json')
        deactivate = self.client.post(f'/api/v1/children/ninos/{nino.pk}/deactivate/')
        reactivate = self.client.post(f'/api/v1/children/ninos/{nino.pk}/reactivate/')

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['results'][0]['centro'], None)
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.assertEqual(deactivate.status_code, status.HTTP_200_OK)
        self.assertEqual(reactivate.status_code, status.HTTP_200_OK)
        nino.refresh_from_db()
        self.assertEqual(nino.nombre, 'Actualizado')
        self.assertIsNone(nino.centro)
