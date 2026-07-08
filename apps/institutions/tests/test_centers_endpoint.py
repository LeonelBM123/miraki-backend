from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Rol, Tutor
from apps.alerts.models import Posicion
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo
from apps.institutions.models import AdminCentro, CentroEducativo
from apps.zones.models import NinoZonaSegura, ZonaSegura

Usuario = get_user_model()


class CentersEndpointTests(APITestCase):
    def setUp(self):
        rol_tutor = Rol.objects.get(nombre_rol='Tutor')
        rol_admin = Rol.objects.get(nombre_rol='AdminCentro')
        self.tutor_user = Usuario.objects.create_user('tutor-centers@example.com', 'StrongPass123!', id_rol=rol_tutor)
        self.admin_user = Usuario.objects.create_user('admin-centers@example.com', 'StrongPass123!', id_rol=rol_admin)
        self.tutor = Tutor.objects.create(
            id_usuario=self.tutor_user,
            nombre='Tutor Centers',
            telefono='70001001',
        )
        self.centro_a = CentroEducativo.objects.create(nombre='Alpha', direccion='Direccion Alpha')
        self.centro_b = CentroEducativo.objects.create(nombre='Beta', direccion='Direccion Beta')
        self.centro_inactivo = CentroEducativo.objects.create(
            nombre='Inactivo',
            direccion='Direccion Inactiva',
            activo=False,
        )
        self.admin_centro = AdminCentro.objects.create(
            id_usuario=self.admin_user,
            id_centro=self.centro_a,
            nombre='Admin Centers',
            telefono='70001002',
        )

    def test_tutor_can_list_active_centers_with_pagination_and_stable_order(self):
        self.client.force_authenticate(self.tutor_user)

        response = self.client.get('/api/v1/institutions/centers/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(
            [item['id_centro'] for item in response.data['results']],
            [self.centro_a.pk, self.centro_b.pk],
        )
        self.assertEqual(set(response.data['results'][0].keys()), {'id_centro', 'nombre', 'direccion'})
        self.assertEqual(response.data['results'][0]['nombre'], 'Alpha')
        self.assertEqual(response.data['results'][0]['direccion'], 'Direccion Alpha')

    def test_unauthenticated_user_receives_401(self):
        response = self.client.get('/api/v1/institutions/centers/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_centers_endpoint_keeps_global_pagination(self):
        for index in range(21):
            CentroEducativo.objects.create(nombre=f'Centro {index:02d}', direccion=f'Direccion {index:02d}')

        self.client.force_authenticate(self.tutor_user)
        response = self.client.get('/api/v1/institutions/centers/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 23)
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(len(response.data['results']), 20)

    def test_centers_endpoint_does_not_allow_write_methods(self):
        self.client.force_authenticate(self.tutor_user)

        post = self.client.post('/api/v1/institutions/centers/', {'nombre': 'Nuevo'}, format='json')
        patch = self.client.patch('/api/v1/institutions/centers/', {'nombre': 'Editado'}, format='json')
        delete = self.client.delete('/api/v1/institutions/centers/')

        self.assertEqual(post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(patch.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_can_get_own_center(self):
        self.client.force_authenticate(self.admin_user)

        response = self.client.get('/api/v1/institutions/my-center/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id_centro'], self.centro_a.pk)
        self.assertEqual(response.data['nombre'], 'Alpha')

    def test_admin_can_edit_own_center(self):
        self.client.force_authenticate(self.admin_user)

        response = self.client.patch(
            '/api/v1/institutions/my-center/',
            {'nombre': 'Alpha Renombrado', 'direccion': 'Nueva Direccion'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.centro_a.refresh_from_db()
        self.assertEqual(self.centro_a.nombre, 'Alpha Renombrado')
        self.assertEqual(self.centro_a.direccion, 'Nueva Direccion')

    def test_tutor_cannot_access_my_center(self):
        self.client.force_authenticate(self.tutor_user)

        get = self.client.get('/api/v1/institutions/my-center/')
        patch = self.client.patch('/api/v1/institutions/my-center/', {'nombre': 'X'}, format='json')

        self.assertEqual(get.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(patch.status_code, status.HTTP_403_FORBIDDEN)

    def test_tutor_cannot_access_institution_map(self):
        self.client.force_authenticate(self.tutor_user)
        response = self.client.get('/api/v1/institutions/map/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_institution_map_reports_children_and_zones(self):
        # Zona institucional del centro del admin.
        poligono = Polygon((
            (-63.20, -17.80),
            (-63.10, -17.80),
            (-63.10, -17.70),
            (-63.20, -17.70),
            (-63.20, -17.80),
        ))
        poligono.srid = 4326
        zona = ZonaSegura.objects.create(nombre='Perímetro Alpha', poligono=poligono, id_centro=self.centro_a, activo=True)

        nino = Nino.objects.create(id_tutor=self.tutor, nombre='Centro Kid', centro=self.centro_a)
        NinoZonaSegura.objects.create(id_nino=nino, id_zona=zona, activa=True)
        dispositivo = Dispositivo.objects.create(id_nino=nino, imei='860000000000099', estado='vinculado', activo=True)
        Posicion.objects.create(
            id_dispositivo=dispositivo,
            latitud='-17.750000',
            longitud='-63.150000',
            ubicacion=Point(-63.150000, -17.750000, srid=4326),
            fecha_posicion=timezone.now(),
        )

        self.client.force_authenticate(self.admin_user)
        response = self.client.get('/api/v1/institutions/map/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['zonas']), 1)
        self.assertEqual(response.data['zonas'][0]['poligono']['type'], 'Polygon')

        child = next(c for c in response.data['children'] if c['id_nino'] == nino.id_nino)
        self.assertTrue(child['dentro_zona'])
        self.assertEqual(child['latitud'], -17.75)

    def test_existing_children_center_flows_still_work(self):
        nino = Nino.objects.create(id_tutor=self.tutor, nombre='Mateo')
        self.client.force_authenticate(self.tutor_user)

        assign = self.client.post(
            f'/api/v1/children/ninos/{nino.pk}/assign-center/',
            {'centro_id': self.centro_a.pk},
            format='json',
        )
        remove = self.client.post(f'/api/v1/children/ninos/{nino.pk}/remove-center/')

        self.client.force_authenticate(self.admin_user)
        center_children = self.client.get('/api/v1/institutions/children/')

        self.assertEqual(assign.status_code, status.HTTP_200_OK)
        self.assertEqual(remove.status_code, status.HTTP_200_OK)
        self.assertEqual(center_children.status_code, status.HTTP_200_OK)
