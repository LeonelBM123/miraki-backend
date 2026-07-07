from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import Rol, Usuario, Tutor
from apps.children.models import Nino
from apps.zones.models import NinoZonaSegura

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


def make_tutor_user(correo='tutor2@test.com', password='Test1234!'):
    rol, _ = Rol.objects.get_or_create(nombre_rol='Tutor')
    user = Usuario.objects.create_user(correo=correo, password=password, id_rol=rol)
    tutor = Tutor.objects.create(id_usuario=user, nombre='Tutor Test 2', telefono='70000001')
    return user, tutor


class HorariosYNinosTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user, self.tutor = make_tutor_user()
        self.client.force_authenticate(user=self.user)

        create_resp = self.client.post('/api/v1/zones/zonas/', {
            'nombre': 'Colegio',
            'poligono': POLYGON_GEOJSON,
        }, format='json')
        self.zona_id = create_resp.data['id_zona']

    def test_sync_horarios(self):
        horarios_data = [
            {'dia_semana': 1, 'hora_inicio': '08:00:00', 'hora_fin': '12:00:00'},
            {'dia_semana': 3, 'hora_inicio': '14:00:00', 'hora_fin': '18:00:00'},
        ]
        resp = self.client.put(f'/api/v1/zones/zonas/{self.zona_id}/horarios/', horarios_data, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['horarios']), 2)
        self.assertEqual(resp.data['horarios'][0]['dia_semana'], 1)

    def test_horario_invalido_horas(self):
        horarios_data = [
            {'dia_semana': 1, 'hora_inicio': '15:00:00', 'hora_fin': '10:00:00'},
        ]
        resp = self.client.put(f'/api/v1/zones/zonas/{self.zona_id}/horarios/', horarios_data, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_vincular_y_desactivar_nino(self):
        nino = Nino.objects.create(
            nombre='Lucas',
            id_tutor=self.tutor,
            activo=True,
        )

        # 1. Vincular niño (PB-09)
        resp = self.client.post(f'/api/v1/zones/zonas/{self.zona_id}/vincular_nino/', {'id_nino': nino.pk}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['ninos_asociados']), 1)
        self.assertEqual(resp.data['ninos_asociados'][0]['nombre'], 'Lucas')
        self.assertEqual(resp.data['ninos_asociados'][0]['activa'], True)

        # 2. Desactivar vigilancia temporalmente (PB-10)
        resp2 = self.client.post(f'/api/v1/zones/zonas/{self.zona_id}/desactivar_nino/', {'id_nino': nino.pk}, format='json')
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data['ninos_asociados'][0]['activa'], False)

        # Verificar en base de datos que el registro no se eliminó (cumpliendo PB-10)
        asoc = NinoZonaSegura.objects.get(id_nino=nino, id_zona_id=self.zona_id)
        self.assertEqual(asoc.activa, False)
