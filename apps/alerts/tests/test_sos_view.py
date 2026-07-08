from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Tutor
from apps.alerts.models import Alerta
from apps.children.models import Nino

Usuario = get_user_model()


class SOSViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario_tutor = Usuario.objects.create_user(
            correo='sos-nino@example.com',
            password='Secr3t-pass',
        )
        self.tutor = Tutor.objects.create(
            id_usuario=self.usuario_tutor,
            nombre='Tutor SOS',
            telefono='3001234567',
        )
        self.nino = Nino.objects.create(
            nombre='Ana',
            id_tutor=self.tutor,
            activo=True,
        )

    def build_token(self, scope='kid_device'):
        token = AccessToken()
        token['nino_id'] = self.nino.id_nino
        token['tutor_id'] = self.usuario_tutor.id_usuario
        token['scope'] = scope
        return str(token)

    def test_sos_alert_con_token_valido(self):
        response = self.client.post(
            '/api/v1/alertas/sos/',
            data={},
            format='json',
            HTTP_X_KID_TOKEN=self.build_token(),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['id_nino'], self.nino.id_nino)
        self.assertEqual(response.data['tipo'], Alerta.TipoAlerta.SOS)
        self.assertEqual(Alerta.objects.filter(id_nino=self.nino, tipo=Alerta.TipoAlerta.SOS).count(), 1)

    def test_sos_alert_sin_token(self):
        response = self.client.post('/api/v1/alertas/sos/', data={}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
