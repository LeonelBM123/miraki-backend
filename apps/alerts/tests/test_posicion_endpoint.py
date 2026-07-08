from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Rol, Tutor
from apps.alerts.models import Posicion
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo

Usuario = get_user_model()


class UltimaPosicionViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.rol_tutor, _ = Rol.objects.get_or_create(
            nombre_rol='Tutor',
            defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'},
        )

        self.usuario = Usuario.objects.create_user(
            correo='tutor-posiciones@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )
        self.tutor = Tutor.objects.create(id_usuario=self.usuario, nombre='Tutor Posiciones', telefono='70000010')

        self.otro_usuario = Usuario.objects.create_user(
            correo='otro-posiciones@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )
        self.otro_tutor = Tutor.objects.create(
            id_usuario=self.otro_usuario,
            nombre='Otro Tutor',
            telefono='70000011',
        )

    def _create_child_with_positions(self, tutor, nombre, posiciones):
        nino = Nino.objects.create(id_tutor=tutor, nombre=nombre)
        dispositivo = Dispositivo.objects.create(
            id_nino=nino,
            imei=f'864200000000{nino.id_nino:02d}',
            estado='vinculado',
            activo=True,
        )
        for data in posiciones:
            fecha_posicion = data['fecha_posicion']
            if isinstance(fecha_posicion, str):
                fecha_posicion = datetime.fromisoformat(fecha_posicion.replace('Z', '+00:00'))
            Posicion.objects.create(
                id_dispositivo=dispositivo,
                latitud=str(data['latitud']),
                longitud=str(data['longitud']),
                ubicacion=Point(data['longitud'], data['latitud'], srid=4326),
                velocidad=data.get('velocidad'),
                fecha_posicion=fecha_posicion,
            )
        return nino

    def test_ultima_posicion_returns_latest(self):
        self._create_child_with_positions(
            self.tutor,
            'Sofía',
            [
                {'latitud': -16.460000, 'longitud': -68.160000, 'fecha_posicion': '2026-07-07T10:00:00Z'},
                {'latitud': -16.450000, 'longitud': -68.150000, 'fecha_posicion': '2026-07-07T10:10:00Z'},
            ],
        )

        self.client.force_authenticate(user=self.usuario)
        response = self.client.get('/api/v1/posiciones/ultima/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['nombre'], 'Sofía')
        self.assertEqual(response.data['results'][0]['latitud'], -16.45)
        self.assertEqual(response.data['results'][0]['longitud'], -68.15)

    def test_ultima_posicion_filtered_by_tutor(self):
        self._create_child_with_positions(
            self.tutor,
            'Sofía',
            [{'latitud': -16.450000, 'longitud': -68.150000, 'fecha_posicion': '2026-07-07T10:10:00Z'}],
        )
        self._create_child_with_positions(
            self.otro_tutor,
            'Mateo',
            [{'latitud': -16.400000, 'longitud': -68.100000, 'fecha_posicion': '2026-07-07T10:10:00Z'}],
        )

        self.client.force_authenticate(user=self.usuario)
        response = self.client.get('/api/v1/posiciones/ultima/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['nombre'], 'Sofía')

    def test_ultima_posicion_empty(self):
        self.client.force_authenticate(user=self.otro_usuario)

        response = self.client.get('/api/v1/posiciones/ultima/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'], [])
