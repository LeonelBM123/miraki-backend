from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Tutor
from apps.alerts.models import Alerta, Posicion
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo
from apps.zones.models import NinoZonaSegura, ZonaSegura

Usuario = get_user_model()


class EstadoNinoViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario_tutor = Usuario.objects.create_user(
            correo='estado-nino@example.com',
            password='Secr3t-pass',
        )
        self.tutor = Tutor.objects.create(
            id_usuario=self.usuario_tutor,
            nombre='Tutor Estado',
            telefono='3001234567',
        )
        self.nino = Nino.objects.create(
            nombre='Ana',
            id_tutor=self.tutor,
            activo=True,
        )
        self.dispositivo = Dispositivo.objects.create(
            id_nino=self.nino,
            imei='8642000000000101',
            estado='vinculado',
            activo=True,
        )

        poligono = Polygon(
            (
                (-68.20, -16.50),
                (-68.10, -16.50),
                (-68.10, -16.40),
                (-68.20, -16.40),
                (-68.20, -16.50),
            )
        )
        poligono.srid = 4326
        self.zona = ZonaSegura.objects.create(
            nombre='Zona segura',
            poligono=poligono,
            id_tutor_propietario=self.tutor,
            activo=True,
        )
        NinoZonaSegura.objects.create(id_nino=self.nino, id_zona=self.zona, activa=True)

        self.posicion = Posicion.objects.create(
            id_dispositivo=self.dispositivo,
            latitud='-16.450000',  # Keep as-is; tested field name is latitud in Posicion
            longitud='-68.150000',
            ubicacion=Point(-68.150000, -16.450000, srid=4326),
            velocidad='12.34',
            fecha_posicion=timezone.now() - timedelta(minutes=3),
        )
        Alerta.objects.create(id_nino=self.nino, tipo=Alerta.TipoAlerta.SOS)

    def build_token(self, scope='kid_device'):
        token = AccessToken()
        token['nino_id'] = self.nino.id_nino
        token['tutor_id'] = self.usuario_tutor.id_usuario
        token['scope'] = scope
        return str(token)

    def test_estado_nino_con_token_valido(self):
        response = self.client.get(
            f'/api/v1/pareo/estado/{self.nino.id_nino}/',
            HTTP_X_KID_TOKEN=self.build_token(),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id_nino'], self.nino.id_nino)
        self.assertEqual(response.data['nombre'], 'Ana')
        self.assertEqual(response.data['tutor_nombre'], 'Tutor Estado')
        self.assertTrue(response.data['activo'])
        self.assertEqual(response.data['ultima_posicion']['lat'], -16.45)
        self.assertEqual(response.data['ultima_posicion']['lng'], -68.15)
        self.assertEqual(response.data['ultima_posicion']['fecha'], self.posicion.fecha_posicion.isoformat())
        self.assertEqual(response.data['zona_actual']['nombre'], 'Zona segura')
        self.assertTrue(response.data['zona_actual']['dentro'])
        self.assertEqual(response.data['alertas_recientes'], 1)

    def test_estado_nino_sin_token(self):
        response = self.client.get(f'/api/v1/pareo/estado/{self.nino.id_nino}/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_estado_nino_token_invalido(self):
        response = self.client.get(
            f'/api/v1/pareo/estado/{self.nino.id_nino}/',
            HTTP_X_KID_TOKEN='bad-token',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
