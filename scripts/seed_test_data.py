import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'

import django
django.setup()

from django.contrib.gis.geos import Polygon, Point
from django.utils import timezone
from apps.accounts.models import Usuario, Rol, Tutor
from apps.children.models import Nino
from apps.zones.models import ZonaSegura, NinoZonaSegura
from apps.dispositivos.models import Dispositivo
from apps.alerts.models import Posicion

rol_tutor, _ = Rol.objects.get_or_create(nombre_rol='Tutor', defaults={'descripcion': 'Tutor'})

user, created = Usuario.objects.get_or_create(
    correo='test@prueba.com',
    defaults={'password': 'pbkdf2_sha256$...', 'id_rol': rol_tutor}
)
if created:
    user.set_password('Test123!')
    user.save()
    Tutor.objects.create(id_usuario=user, nombre='Tutor Prueba', telefono='70000001')

tutor = Tutor.objects.get(id_usuario=user)

nino, created = Nino.objects.get_or_create(
    id_tutor=tutor, nombre='Ana Prueba', defaults={'activo': True}
)

poligono = Polygon(((-63.25, -17.85), (-63.15, -17.85), (-63.15, -17.75), (-63.25, -17.75), (-63.25, -17.85)), srid=4326)
zona, created = ZonaSegura.objects.get_or_create(
    nombre='Zona Prueba', defaults={'poligono': poligono, 'id_tutor_propietario': tutor, 'activo': True}
)
nz, _ = NinoZonaSegura.objects.get_or_create(id_nino=nino, id_zona=zona, defaults={'activa': True})

dev, created = Dispositivo.objects.get_or_create(
    imei='864000000000001', defaults={'id_nino': nino, 'estado': 'vinculado', 'activo': True}
)

# Posicion FUERA de la zona (Cochabamba)
Posicion.objects.create(
    id_dispositivo=dev, latitud='-17.380000', longitud='-66.150000',
    ubicacion=Point(-66.15, -17.38, srid=4326), velocidad='5.5', fecha_posicion=timezone.now(),
)

# Posicion DENTRO de la zona
Posicion.objects.create(
    id_dispositivo=dev, latitud='-17.800000', longitud='-63.200000',
    ubicacion=Point(-63.20, -17.80, srid=4326), velocidad='2.0', fecha_posicion=timezone.now(),
)

print("=== DATOS DE PRUEBA LISTOS ===")
print("Usuario: test@prueba.com / Test123!")
print(f"Nino: {nino.nombre} (id={nino.id_nino})")
print(f"Zona: {zona.nombre} (id={zona.pk})")
print(f"Dispositivo IMEI: {dev.imei} (id={dev.id_dispositivo})")
print()
print("Para generar una alerta:")
print("  from apps.alerts.tasks import evaluar_zonas")
print("  evaluar_zonas()")
