import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.base'
import django; django.setup()

from django.db.models import OuterRef, Subquery
from apps.alerts.models import Posicion
from apps.alerts.tasks import evaluar_zonas
from apps.children.models import Nino

# Check Nino
nino = Nino.objects.get(pk=1)
print(f'Nino: {nino.nombre}, activo={nino.activo}')
print(f'Has dispositivo: {hasattr(nino, "dispositivo")}')
if hasattr(nino, 'dispositivo'):
    dev = nino.dispositivo
    print(f'Dispositivo: {dev.imei} (id={dev.id_dispositivo})')
    print(f'Posiciones count: {dev.posiciones.count()}')
    for p in dev.posiciones.all():
        print(f'  Posicion id={p.id_posicion}: lat={p.latitud}, lng={p.longitud}')

# Check evaluar_zonas queryset
latest = Posicion.objects.filter(id_dispositivo__id_nino=OuterRef('pk')).order_by('-fecha_posicion', '-id_posicion')
qs = Nino.objects.filter(activo=True).annotate(latest_id=Subquery(latest.values('id_posicion')[:1]))
print(f'\nNinos con posiciones: {qs.count()}')
for n in qs.values('id_nino', 'nombre', 'latest_id'):
    print(f'  {n}')

print(f'\nResultado evaluar_zonas: {evaluar_zonas()}')
