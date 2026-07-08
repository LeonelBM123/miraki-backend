import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
import django; django.setup()

from django.contrib.gis.geos import Point
from django.utils import timezone
from apps.alerts.models import Posicion
from apps.dispositivos.models import Dispositivo
from apps.alerts.models import Alerta

# Clean up old data
Alerta.objects.all().delete()
Posicion.objects.all().delete()
print(f'Cleaned {Alerta.objects.count()} alerts, {Posicion.objects.count()} positions')

dev = Dispositivo.objects.get(imei='864000000000001')
print(f'Device: {dev.imei} (id={dev.id_dispositivo})')

# Create position OUTSIDE zone (Cochabamba) — MOST RECENT
pos_outside = Posicion.objects.create(
    id_dispositivo=dev,
    latitud='-17.380000',
    longitud='-66.150000',
    ubicacion=Point(-66.15, -17.38, srid=4326),
    velocidad='5.5',
    fecha_posicion=timezone.now(),
)
print(f'OUTSIDE position created: id={pos_outside.id_posicion} at {pos_outside.fecha_posicion}')

# Create position INSIDE zone (Santa Cruz) — 30 MINUTES AGO
pos_inside = Posicion.objects.create(
    id_dispositivo=dev,
    latitud='-17.800000',
    longitud='-63.200000',
    ubicacion=Point(-63.20, -17.80, srid=4326),
    velocidad='2.0',
    fecha_posicion=timezone.now() - timezone.timedelta(minutes=30),
)
print(f'INSIDE position created: id={pos_inside.id_posicion} at {pos_inside.fecha_posicion}')

# Now the latest position (#3) is OUTSIDE the zone
print(f'\nLatest position id should be: {pos_outside.id_posicion} (outside)')

from apps.alerts.tasks import evaluar_zonas
result = evaluar_zonas()
print(f'\nevaluar_zonas result: {result}')

alerts = Alerta.objects.all()
print(f'Alerts created: {alerts.count()}')
for a in alerts:
    from django.urls import reverse
    print(f'  Alerta id={a.id_alerta}: tipo={a.tipo}, atendida={a.atendida}, fecha={a.fecha_alerta}')
