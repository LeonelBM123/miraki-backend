from django.test import TestCase
from django.contrib.gis.geos import GEOSGeometry
from rest_framework.test import APIClient
from apps.accounts.models import Rol, Usuario, Tutor

POLYGON_GEOJSON = {
    'type': 'Polygon',
    'coordinates': [[
        [-63.1823, -17.7832],
        [-63.1820, -17.7832],
        [-63.1820, -17.7835],
        [-63.1823, -17.7835],
        [-63.1823, -17.7832],
    ]],
}


def make_tutor_user(correo='tutor@test.com', password='Test1234!'):
    rol, _ = Rol.objects.get_or_create(nombre_rol='Tutor')
    user = Usuario.objects.create_user(correo=correo, password=password, id_rol=rol)
    tutor = Tutor.objects.create(id_usuario=user, nombre='Tutor Test', telefono='70000000')
    return user, tutor


class ZonaSeguraCRUDTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, self.tutor = make_tutor_user()
        self.client.force_authenticate(user=self.user)

    def test_crear_zona(self):
        resp = self.client.post('/api/v1/zones/zonas/', {
            'nombre': 'Casa',
            'poligono': POLYGON_GEOJSON,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['nombre'], 'Casa')
        self.assertEqual(resp.data['activo'], True)

    def test_listar_zonas_solo_propias(self):
        self.client.post('/api/v1/zones/zonas/', {
            'nombre': 'Mi Zona',
            'poligono': POLYGON_GEOJSON,
        }, format='json')

        # Otro tutor no debe ver las zonas del primero
        other_user, _ = make_tutor_user(correo='otro@test.com')
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        resp = other_client.get('/api/v1/zones/zonas/')
        self.assertEqual(len(resp.data['results']), 0)

    def test_editar_nombre_zona(self):
        create_resp = self.client.post('/api/v1/zones/zonas/', {
            'nombre': 'Original',
            'poligono': POLYGON_GEOJSON,
        }, format='json')
        zona_id = create_resp.data['id_zona']
        resp = self.client.patch(f'/api/v1/zones/zonas/{zona_id}/', {
            'nombre': 'Modificado',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['nombre'], 'Modificado')

    def test_desactivar_zona(self):
        create_resp = self.client.post('/api/v1/zones/zonas/', {
            'nombre': 'A Desactivar',
            'poligono': POLYGON_GEOJSON,
        }, format='json')
        zona_id = create_resp.data['id_zona']
        resp = self.client.post(f'/api/v1/zones/zonas/{zona_id}/deactivate/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['activo'], False)

    def test_zona_ajena_da_404(self):
        create_resp = self.client.post('/api/v1/zones/zonas/', {
            'nombre': 'Privada',
            'poligono': POLYGON_GEOJSON,
        }, format='json')
        zona_id = create_resp.data['id_zona']

        other_user, _ = make_tutor_user(correo='intruso@test.com')
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        resp = other_client.get(f'/api/v1/zones/zonas/{zona_id}/')
        self.assertEqual(resp.status_code, 404)
