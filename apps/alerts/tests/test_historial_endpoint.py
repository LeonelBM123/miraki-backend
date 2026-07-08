from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Rol, Tutor
from apps.alerts.models import Posicion
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo

Usuario = get_user_model()


class HistorialPosicionesViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.rol_tutor, _ = Rol.objects.get_or_create(
            nombre_rol='Tutor',
            defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'},
        )
        self.usuario = Usuario.objects.create_user('tutor-hist@example.com', 'StrongPass123!', id_rol=self.rol_tutor)
        self.tutor = Tutor.objects.create(id_usuario=self.usuario, nombre='Tutor Hist', telefono='70000200')
        self.nino = Nino.objects.create(id_tutor=self.tutor, nombre='Ruta Kid')
        self.dispositivo = Dispositivo.objects.create(
            id_nino=self.nino, imei='860000000000200', estado='vinculado', activo=True,
        )
        for i in range(3):
            Posicion.objects.create(
                id_dispositivo=self.dispositivo,
                latitud=f'-17.75{i}000',
                longitud='-63.150000',
                ubicacion=Point(-63.15, -17.75, srid=4326),
                velocidad='1.00',
                bateria=90 - i,
                fecha_posicion=timezone.now() - timezone.timedelta(minutes=i),
            )

        self.otro_usuario = Usuario.objects.create_user('otro-hist@example.com', 'StrongPass123!', id_rol=self.rol_tutor)
        self.otro_tutor = Tutor.objects.create(id_usuario=self.otro_usuario, nombre='Otro', telefono='70000201')
        self.otro_nino = Nino.objects.create(id_tutor=self.otro_tutor, nombre='Ajeno')

    def test_returns_history_json_for_own_child(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.get(f'/api/v1/posiciones/historial/?nino={self.nino.id_nino}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)
        self.assertIn('latitud', response.data['results'][0])

    def test_csv_export_attachment(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.get(f'/api/v1/posiciones/historial/?nino={self.nino.id_nino}&formato=csv')

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment; filename="historial_', response['Content-Disposition'])
        body = response.content.decode('utf-8')
        self.assertIn('Fecha,Latitud,Longitud,Velocidad,Bateria', body)

    def test_other_tutor_child_returns_404(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.get(f'/api/v1/posiciones/historial/?nino={self.otro_nino.id_nino}')
        self.assertEqual(response.status_code, 404)

    def test_missing_nino_returns_400(self):
        self.client.force_authenticate(self.usuario)
        response = self.client.get('/api/v1/posiciones/historial/')
        self.assertEqual(response.status_code, 400)
