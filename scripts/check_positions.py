import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
import django; django.setup()
from apps.alerts.models import Posicion

for p in Posicion.objects.all().order_by('id_posicion'):
    print(f'id={p.id_posicion}, fecha_posicion={p.fecha_posicion}, lat={p.latitud}, lng={p.longitud}')
