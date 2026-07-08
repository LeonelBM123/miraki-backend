from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Rol
from apps.alerts.models import DispositivoToken

Usuario = get_user_model()


class DispositivoTokenViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.rol_tutor, _ = Rol.objects.get_or_create(
            nombre_rol='Tutor',
            defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'},
        )
        self.usuario = Usuario.objects.create_user(
            correo='token-user@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )
        self.otro_usuario = Usuario.objects.create_user(
            correo='token-user-2@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )

    def test_create_token(self):
        self.client.force_authenticate(user=self.usuario)

        response = self.client.post(
            '/api/v1/dispositivo-tokens/',
            data={'token': 'fcm-token-001', 'plataforma': 'android'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['token'], 'fcm-token-001')
        self.assertEqual(response.data['id_usuario'], self.usuario.id_usuario)

    def test_upsert_same_token_no_dup(self):
        self.client.force_authenticate(user=self.usuario)

        first = self.client.post(
            '/api/v1/dispositivo-tokens/',
            data={'token': 'fcm-token-dup', 'plataforma': 'ios'},
            format='json',
        )
        second = self.client.post(
            '/api/v1/dispositivo-tokens/',
            data={'token': 'fcm-token-dup', 'plataforma': 'web'},
            format='json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(DispositivoToken.objects.filter(token='fcm-token-dup').count(), 1)
        self.assertEqual(first.data['id'], second.data['id'])

    def test_delete_token(self):
        token = DispositivoToken.objects.create(
            id_usuario=self.usuario,
            token='fcm-token-delete',
            plataforma=DispositivoToken.Plataforma.WEB,
        )
        self.client.force_authenticate(user=self.usuario)

        response = self.client.delete(f'/api/v1/dispositivo-tokens/{token.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(DispositivoToken.objects.filter(pk=token.pk).exists())

    def test_filter_by_user(self):
        DispositivoToken.objects.create(
            id_usuario=self.usuario,
            token='token-user-1',
            plataforma=DispositivoToken.Plataforma.ANDROID,
        )
        DispositivoToken.objects.create(
            id_usuario=self.otro_usuario,
            token='token-user-2',
            plataforma=DispositivoToken.Plataforma.IOS,
        )
        self.client.force_authenticate(user=self.usuario)

        response = self.client.get('/api/v1/dispositivo-tokens/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['token'], 'token-user-1')
