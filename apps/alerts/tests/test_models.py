from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Rol, Tutor
from apps.alerts.models import Alerta, DispositivoToken, Posicion
from apps.children.models import Nino
from apps.dispositivos.models import Dispositivo
from apps.zones.models import ZonaSegura

Usuario = get_user_model()


class AlertasModelsTests(TestCase):
    def setUp(self):
        self.rol_tutor, _ = Rol.objects.get_or_create(
            nombre_rol='Tutor',
            defaults={'descripcion': 'Padre o tutor que monitorea a uno o más niños'},
        )
        self.usuario = Usuario.objects.create_user(
            correo='tutor-alertas@example.com',
            password='StrongPass123!',
            id_rol=self.rol_tutor,
        )
        self.tutor = Tutor.objects.create(
            id_usuario=self.usuario,
            nombre='Tutor Alertas',
            telefono='70000010',
        )
        self.nino = Nino.objects.create(id_tutor=self.tutor, nombre='Sofía')
        self.dispositivo = Dispositivo.objects.create(
            id_nino=self.nino,
            imei='864209876543210',
            estado='vinculado',
            activo=True,
        )

        poligono = Polygon((
            (-68.20, -16.50),
            (-68.10, -16.50),
            (-68.10, -16.40),
            (-68.20, -16.40),
            (-68.20, -16.50),
        ))
        poligono.srid = 4326
        self.zona = ZonaSegura.objects.create(
            nombre='Zona Central',
            poligono=poligono,
            id_tutor_propietario=self.tutor,
            activo=True,
        )
        self.posicion = Posicion.objects.create(
            id_dispositivo=self.dispositivo,
            latitud='-16.450000',
            longitud='-68.150000',
            ubicacion=Point(-68.150000, -16.450000, srid=4326),
            velocidad='12.34',
            fecha_posicion=timezone.now(),
        )

    def test_alerta_crear(self):
        alerta = Alerta.objects.create(
            id_nino=self.nino,
            id_zona=self.zona,
            id_posicion=self.posicion,
            tipo=Alerta.TipoAlerta.SALIDA_ZONA,
        )

        self.assertIsNotNone(alerta.id_alerta)
        self.assertEqual(alerta.id_nino, self.nino)
        self.assertEqual(alerta.id_zona, self.zona)
        self.assertEqual(alerta.id_posicion, self.posicion)
        self.assertEqual(str(alerta), f'Alerta {alerta.id_alerta} - Salida de zona - {alerta.fecha_alerta}')

    def test_alerta_tipo_check(self):
        alerta = Alerta(id_nino=self.nino, tipo='invalido')

        with self.assertRaises(ValidationError):
            alerta.full_clean()

    def test_alerta_defaults(self):
        alerta = Alerta.objects.create(id_nino=self.nino, tipo=Alerta.TipoAlerta.SOS)

        self.assertFalse(alerta.atendida)
        self.assertIsNone(alerta.fecha_atencion)
        self.assertIsNone(alerta.atendida_por)

    def test_dispositivo_token_crear(self):
        token = DispositivoToken.objects.create(
            id_usuario=self.usuario,
            id_dispositivo=self.dispositivo,
            token='fcm-token-001',
            plataforma=DispositivoToken.Plataforma.ANDROID,
        )

        self.assertIsNotNone(token.id)
        self.assertEqual(token.id_usuario, self.usuario)
        self.assertEqual(token.id_dispositivo, self.dispositivo)
        self.assertTrue(token.activo)

    def test_dispositivo_token_unique_token(self):
        DispositivoToken.objects.create(
            id_usuario=self.usuario,
            id_dispositivo=self.dispositivo,
            token='fcm-token-unique',
            plataforma=DispositivoToken.Plataforma.WEB,
        )

        with self.assertRaises(IntegrityError):
            DispositivoToken.objects.create(
                id_usuario=self.usuario,
                id_dispositivo=self.dispositivo,
                token='fcm-token-unique',
                plataforma=DispositivoToken.Plataforma.IOS,
            )

    def test_posicion_crear(self):
        posicion = Posicion.objects.create(
            id_dispositivo=self.dispositivo,
            latitud='-16.451000',
            longitud='-68.152000',
            ubicacion=Point(-68.152000, -16.451000, srid=4326),
            velocidad='20.50',
            fecha_posicion=timezone.now(),
        )

        self.assertIsNotNone(posicion.id_posicion)
        self.assertEqual(posicion.id_dispositivo, self.dispositivo)
        self.assertEqual(posicion.ubicacion.srid, 4326)
        self.assertAlmostEqual(float(posicion.latitud), -16.451000)
        self.assertAlmostEqual(float(posicion.longitud), -68.152000)

    def test_posicion_fields(self):
        ubicacion = Posicion._meta.get_field('ubicacion')
        fecha_recepcion = Posicion._meta.get_field('fecha_recepcion')

        self.assertTrue(ubicacion.geography)
        self.assertEqual(ubicacion.srid, 4326)
        self.assertTrue(ubicacion.null)
        self.assertTrue(ubicacion.blank)
        self.assertTrue(fecha_recepcion.auto_now_add)
